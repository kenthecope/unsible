#!/usr/bin/env python
"""
Report on LSP statistics

kcope@juniper.net

version:
    - 08.11.2017 - various bug fixes
    - 23.10.2017 - First functional version
    - 20.09.2017 - Initial version

TODO:
"""

from jnpr.junos import Device
from netaddr import IPAddress, valid_ipv4, valid_ipv6
import os
import getpass
import sys
import logging
import argparse
import re
import datetime
import pprint
import socket
import Queue
from lib.Device import JunosDevice
from lib.mpls_tables import MPLSLSPTable
from lib.Unsible import Inventory
from lib.populate_lsp import populate_lsp_info
from lib.Status import Status
from jnpr.junos.exception import *
import time
import signal
import select
import tty
import termios

import threading
from threading import Thread
from lib.LSPfetcher import LSPfetcher
#from lib.GetKey import GetKey

from lib.terminal_colors import bcolors
from lib.terminal_colors import colorize

try:
    import termios
except:
    print "This does not work on Windows."
    sys.exit(0)


# see if we should quit
TIME_TO_DIE = False

# see if we have the curses library or not
import imp
try:
    import curses
    from curses import wrapper
    from lib.CursesDisplay import LSPDisplayScreenCurses
    HAVE_CURSES = True
except ImportError:
    HAVE_CURSES = False
    from lib.Display import LSPDisplay

def ts_print(mystring):
    # thread safe print
    # write a string to sys.stdout and then flush
    sys.stdout.write(str(mystring))
    sys.stdout.write('\n')
    #sys.stdout.flush()

def end_program(tcset=None):
    if tcset:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, tcset)
    # show the cursor
    sys.stdout.write("\033[?25h\n")
    sys.stdout.flush()
    sys.exit(0)

def ctl_c_handler(signal, frame):
    global TIME_TO_DIE
    TIME_TO_DIE = True
    end_program()


def main():
    # Setup logging
    logger = logging.getLogger()
    #handler = logging.StreamHandler()
    file_handler = logging.FileHandler('/tmp/LSPstatus.log')
    #formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    #handler.setFormatter(formatter)
    #logger.addHandler(handler)
    logger.addHandler(file_handler)
    #logger.setLevel(logging.DEBUG)
    logger.setLevel(logging.ERROR)

    logger.debug('----------------------------------BEGIN __main__')


    # Command line arguments
    parser = argparse.ArgumentParser(description='LSP Status')
    parser.add_argument('-d', '--host', type=str, help='Hostname or IP address of device to check.')
    parser.add_argument('-l', '--limit', type=str, help='Limit hosts to a subset of matching hosts')
    parser.add_argument('-i', '--inventory-file', type=str, help='Ansible inventory directory.')
    parser.add_argument('-u', '--username', type=str, help='name of user to connect to hubs with')
    parser.add_argument('-p', '--password', help='prompt for password', action="store_true")
    parser.add_argument('--interval', type=int, help='Interval to repeat in seconds.')
    parser.add_argument('--list-hosts', action='store_true', default=False,
                        help="Output matching hosts, but don't excecute anything.")
    parser.add_argument('--list-vars', action='store_true', default=False,
                        help="Output matching hosts and any variables they may inherit.")
    parser.add_argument('--csv', help='Generate a CSV file of the LSPs')
    parser.add_argument('--output-file', type=str, help='Name of file for CSV output')
    parser.add_argument('--insecurepassword', type=str,
                        help='password for user account, WARNING: insecure, for testing only!')
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # a list of devices (IP addresses) to check
    check_ips = []

    # If no username was entered, use the users login value
    if args.username:
        username = args.username
    else:
        username = getpass.getuser()

    if args.password:
        password = getpass.getpass(stream=sys.stderr)
    else:
        # This is for using ssh keys
        password = ""


    # Ansible inventory directory
    ansible_dir = 'ansible/inventory'  # default location
    if args.inventory_file:
        if os.path.isdir(args.inventory_file):
            ansible_dir = args.inventory_file
            ts_print("Ansible Inventory dir is {}".format(ansible_dir))
        else:
            ts_print("ERROR: {} is not a valid directory.".format(args.inventory_file))
            sys.exit()

    # get a list of IPs to check
    if args.limit or args.list_vars:
        inventory = Inventory(directory=ansible_dir)
        inventory.load()
        # load up any variable files
        inventory.load_group_vars()
        inventory.load_host_vars()
        # build a local resolution table from the inventory
        inventory.build_resolver()
        for ip in inventory.lookup(args.limit):
            if valid_ipv4(ip) or valid_ipv6(ip):
                check_ips.append(IPAddress(ip))
            else:
                logger.info('Trying to resolve {}'.format(ip))
                try:
                    resolv = socket.gethostbyname(ip.strip())
                    check_ips.append(IPAddress(resolv))
                except:
                    logger.warning('Could not resolve {} to IP address.'.format(ip))
                    print ('Could not resolve {} to IP address.'.format(ip))
        if args.list_vars:
            ts_print("Listing host variables:")
            pp = pprint.PrettyPrinter(indent=4)
            pp.pprint(inventory.host_vars)
            return

    # check cli args
    if args.host:
        if valid_ipv4(args.host) or valid_ipv6(args.host):
            check_ips.append(IPAddress(args.host))
        else:
            logger.info('Trying to resolve {}'.format(args.host))
            try:
               ip = socket.gethostbyname(args.host.strip())
               check_ips.append(IPAddress(ip))
               inventory = Inventory(directory=ansible_dir)
            except:
               logger.warning('Could not resolve {} to IP address.'.format(args.host))
               ts_print ('Could not resolve {} to IP address.'.format(args.host))

    if args.list_hosts:
        # print hosts, then exit
        for ip in check_ips:
            ts_print(ip)
        return

    if args.list_vars:
        pp = pprint.PrettyPrinter(indent=4)
        ts_print ("missing")

    # a list of devices to check
    devices = []
    for host in check_ips:
        dev = JunosDevice(host, user=username, userPassword=password )
        dev.print_output = False
        devices.append(dev)

    if args.csv:
        for device in devices:
            if not device.device.connected:
                device.open()
            if not device.lsp_map:
                device.lsp_map = populate_lsp_info(device.device)
            ts_print(device.lsp_map.csv())

    if args.interval:
        # display loop without curses
        # wrapper to restore screen after display_interval function is finished
        # start an LSPfetcher

        # register a ctrl-c handler
        signal.signal(signal.SIGINT, ctl_c_handler)

        # get a lock, will be used to control print output
        lock = threading.Lock()

        lsps = LSPfetcher(devices, sleep_interval=int(args.interval),
                          num_threads=2, lock=lock)
        status_q, lsp_q, error_q = lsps.start()

        mystatus = {}
        myerrors = {}
        myerrors = {}

        # queue to store key presses
        key_q = Queue.Queue()

        def display_lsps():

            logger.debug('DEVICES {}'.format(str(devices)))
            screen = LSPDisplay()
            # attach the unsible inventory
            screen.inventory = inventory

            global TIME_TO_DIE

            def isKey():
                return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

            tty.setcbreak(sys.stdin.fileno())

            # hide the cursor
            def hide_cursor():
                lock.acquire()
                sys.stdout.write("\033[?25l")
                sys.stdout.flush()
                lock.release()

            while not TIME_TO_DIE:
                if isKey():
                    lock.acquire()
                    mykey = sys.stdin.read(1)
                    # if we have an escape character, read in two more bytes
                    if mykey == '\x1b':
                        mykey += sys.stdin.read(2)
                        logger.info('MY KEY {}'.format('ESCAPE'))
                        logger.info('MY KEY LEN {}'.format(len(mykey)))
                        outstring = "".join(hex(ord(n)) for n in mykey)
                        logger.info('MY KEY HEX {}'.format(outstring))
                    lock.release()
                    key_q.put(mykey)
                if key_q.qsize() > 0:
                    mykey = key_q.get()
                    if mykey.upper() == 'Q':
                        screen.time_to_die = True
                        lock.acquire()
                        sys.stdout.write("Quitting...")
                        sys.stdout.flush()
                        lock.release()
                        TIME_TO_DIE = True
                        #get_key.time_to_die = True
                        break
                    if mykey.upper() == 'D':
                        # toggle only display lsps that are down
                        if screen.filter_only_down:
                            screen.filter_only_down = False
                        else:
                            screen.filter_only_down = True
                    if mykey.upper() == 'N':
                        # toggle sort by name
                        screen.sort_by = 'name'
                    if mykey.upper() == 'S':
                        # toggle sort by from/source address
                        screen.sort_by = 'source_address'
                    if mykey.upper() == 'T':
                        # toggle sort by to address
                        screen.sort_by = 'destination_address'
                    if mykey.upper() == 'B':
                        # toggle sort by bandwidth
                        screen.sort_by = 'bandwidth'
                        screen.status = "sort by bandwidth"
                    if mykey.upper() == 'R':
                        # toggle sort order
                        if screen.sort_reverse:
                            screen.sort_reverse = False
                        else:
                            screen.sort_reverse = True
                    if mykey.upper() == 'F':
                        screen.status = mykey
                        lock.acquire()
                        # show cursor
                        # turn on echo
                        fd = sys.stdin.fileno()
                        old = termios.tcgetattr(fd)
                        new = old[:]
                        new[3] |= termios.ECHO
                        termios.tcsetattr(fd, termios.TCSADRAIN, new)
                        regex = raw_input('\033[?25hEnter new filter:')
                        termios.tcsetattr(fd, termios.TCSADRAIN, old)
                        #regex = 'BONK'
                        #hide_cursor()
                        lock.release()
                        screen.status = regex
                        screen.regex = regex
                    if mykey == '\x1b[A':
                        screen.lsp_display_offset_decrement()
                    if mykey == '\x1b[B':
                        screen.lsp_display_offset_increment()
                    # for debugging
                    #if len(mykey) == 1:
                    #    screen.status = mykey
                if status_q.qsize() > 0:
                    #logger.info("STATUS_Q")
                    my_status = status_q.get()
                    my_ip = my_status.keys()[0].ip
                    my_status = my_status.values()[0]
                    screen.status = '{} {}'.format(my_ip, my_status)
                if error_q.qsize() > 0:
                    #logger.info("ERROR_Q")
                    my_error = error_q.get()
                    my_ip = my_error.keys()[0].ip
                    my_error = my_error.values()[0]
                    screen.errors = '{} {}'.format(my_ip, my_error)
                if lsp_q.qsize() > 0:
                    #logger.info("LSP_Q")
                    my_lsp = lsp_q.get()
                    my_ip = my_lsp.keys()[0]
                    my_lsp = my_lsp.values()[0]
                    screen.lsps[my_ip] = my_lsp
                # ouput the screen
                lock.acquire()
                ts_print(screen)
                lock.release()
                # wait a quarter of a second
                time.sleep(.25)

            # try to exit cleanly
            end_program(old_settings)

        # save terminal settings
        old_settings = termios.tcgetattr(sys.stdin)

        t = threading.Thread(name = "Display", target=display_lsps )
        t.setDaemon(True)
        t.start()

        while not TIME_TO_DIE:
            time.sleep(1)

        lsps.time_to_die = True
        end_program(old_settings)

    # close devices
    for device in devices:
        #print "DEVICE:", device.device.facts
        if device.device.connected:
            logger.debug('CLOSING CONNECTION TO {}'.format(device.ip))
            device.close()
        else:
            logger.debug('{} NOT CONNECTED'.format(device.ip))

    logger.debug('----------------------------------END __main__')


if __name__ == '__main__':
    # get terminal characteristics
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    main()
    # restore terminal settings before exiting
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
