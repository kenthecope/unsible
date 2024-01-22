#!/usr/bin/env python
"""
Do thinks in an ansible like fasion

kcope@juniper.net

version:
    - 22.01.2024 - convert to python3
    - 18.10.2017 - unsible
    - 20.09.2017 - Initial version

TODO:
"""

# std modules
import os
import inspect
import getpass
import sys
import logging
import argparse
import re
import datetime
import pprint
import socket
import time
import getpass

# installed modules
from jnpr.junos import Device
from jnpr.junos.exception import *
from netaddr import IPAddress, valid_ipv4, valid_ipv6
from lxml import etree

# add lib to the sys path for local modules
filename = inspect.getframeinfo(inspect.currentframe()).filename
path = os.path.dirname(os.path.abspath(filename))
lib_path = os.path.join(path, 'lib')
sys.path.insert(0, lib_path)


from Device import JunosDevice
from Unsible import Inventory
from terminal_colors import colorize

__version__ = '22.01.2024.01'

def main():
    # Setup logging
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    file_handler = logging.FileHandler('/dev/null')
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.setLevel(logging.ERROR)

    print (colorize("Unsible FE ver {} - A Junos PyEZ cli frontend".format(__version__), 'bold'))

    # Command line arguments
    parser = argparse.ArgumentParser(description='Unsible')
    parser.add_argument('-d', '--host', type=str, help='Hostname or IP address of device to check.')
    parser.add_argument('--hostlist', type=str, help='Filename with hostnames or IP addresses to check.')
    parser.add_argument('-l', '--limit', type=str, help='Limit hosts to a subset of matching hosts')
    parser.add_argument('-i', '--inventory-file', type=str, help='Ansible inventory directory.')
    parser.add_argument('-u', '--username', type=str, help='name of user to connect to hubs with')
    parser.add_argument('-p', '--password', help='prompt for password', action="store_true")
    parser.add_argument('--list-hosts', action='store_true', default=False,
                        help="Output matching hosts, but don't excecute anything.")
    parser.add_argument('--list-vars', action='store_true', default=False,
                        help="Output matching hosts and any variables they may inherit.")
    parser.add_argument('--output-file', type=str, help='Write all output to a file that starts with the prefix')
    parser.add_argument('--output-dir', type=str, help='Write all output files into this directory (must exist)')
    parser.add_argument('--separate', action='store_true', help='Write output to separate file per device')

    subparsers = parser.add_subparsers(help='commands')
    # subcommands
    # a cli command
    cli_parser = subparsers.add_parser('cli', help='Run a cli command')
    cli_parser.add_argument('command', action='store', help='A Junos CLI command')

    config_parser = subparsers.add_parser('configure', help='Configure a device interactively')
    config_parser.add_argument('configure', action='store', help='Configuration file')
    config_parser.add_argument('-s', '--set', action='store_true', help='Configuruation file is in set format')
    config_parser.add_argument('-y', '--yes', action='store_true',
                               help='Run automatically without prompting for confirmation of commits')
    config_parser.add_argument('-c', '--confirmed', type=int,
                               help='Do a commit confirmed with a rollback timer in minutes')

    commit_parser = subparsers.add_parser('commit', help='Perform a commit on a device')
    commit_parser.add_argument('commit', action='store_true', help='Do a commit')

    rollback_parser = subparsers.add_parser('rollback', help='Perform a rollback 1 and a commit on a device')
    rollback_parser.add_argument('rollback', action='store_true', help='Do a rollback and a commit. Default is 1.')
    rollback_parser.add_argument('-r', type=int, help='Specify rollback number. Default is 1.')

    copyto_parser = subparsers.add_parser('copyto', help='Copy a file to a device using scp')
    copyto_parser.add_argument('copyto', action='store_true', help='Copy a file to a device using scp')
    copyto_parser.add_argument('source_file', type=str, help='File to copy to devices (with optional path)')
    copyto_parser.add_argument('-d', '--destination', type=str, help='Filename or directory to copy source file to on device')

    copyto_parser = subparsers.add_parser('inventory', help='Do a "show chassis hardware" on the device')
    copyto_parser.add_argument('inventory', action='store_true', help='Get a hardware inventory')
    copyto_parser.add_argument('--xml', action='store_true', help='Fetch the inventory in XML format')

    storage_parser = subparsers.add_parser('storage', help='cleanup system storage on device')
    storage_parser.add_argument('storage', action='store_true', help='et a hardware inventory')
    storage_parser.add_argument('-y', '--yes', action='store_true',
                               help='Delete all files without prompting.')


    args = parser.parse_args()

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



    # a list of devices (IP addresses) to check
    check_ips = {}

    # Ansible inventory directory
    ansible_dir = 'ansible/inventory'  # default location
    if args.inventory_file:
        if os.path.isdir(args.inventory_file):
            ansible_dir = args.inventory_file
            print ("Ansible Inventory dir is {}".format(ansible_dir))
        else:
            print ("ERROR: {} is not a valid directory.".format(args.inventory_file))
            sys.exit()

    # function to load up an unsible inventory
    def unsible_init(directory=ansible_dir):
        inventory = Inventory(directory=ansible_dir)
        inventory.load()
        # load up any variable files
        inventory.load_group_vars()
        inventory.load_host_vars()
        # build a local resolution table from the inventory
        inventory.build_resolver()
        return inventory

    # get a list of IPs to check
    if args.limit or args.list_vars:
        inventory = unsible_init()
        for ip in inventory.lookup(args.limit):
            if valid_ipv4(ip) or valid_ipv6(ip):
                #check_ips.append(IPAddress(ip))
                check_ips[IPAddress(ip)] = None
            else:
                logger.info('Trying to resolve {}'.format(ip))
                try:
                    resolv = socket.gethostbyname(ip.strip())
                    #check_ips.append(IPAddress(resolv))
                    check_ips[IPAddress(resolv)] = ip
                except:
                    logger.warning('Could not resolve {} to IP address.'.format(ip))
                    print ('Could not resolve {} to IP address.'.format(ip))

    # check cli args
    hostlist = []

    def connection_attempt(device):
        # report a connection attempt is in progress
        if device.hostname:
            mesg = "Connecting to {} ({})...".format(device.hostname, device.ip)
        else:
            mesg = "Connecting to {} ...".format(device.ip)
        print ('_'*50)
        print (colorize(mesg, 'bold'))


    def check_host(host):
        # try to resolve a host and check if IP addresses are valid
        # returns an IPAdress object, or none
        if valid_ipv4(host) or valid_ipv6(host):
            return IPAddress(host)
        else:
            logger.info('Trying to resolve {}'.format(host))
            try:
               ip = socket.gethostbyname(host.strip())
               return IPAddress(ip)
            except:
               logger.warning('Could not resolve {} to IP address.'.format(host.strip()))
               print ('Could not resolve {} to IP address.'.format(host.strip()))
        return None

    if args.host:
        if check_host(args.host):
            # print ("ARGS.HOST:", args.host)
            # print ("CHECK_HOST(args.host)", check_host(args.host), type(check_host(args.host)))
            #check_ips.append(check_host(args.host))
            check_ips[check_host(args.host)] = args.host

    if args.hostlist:
        # try to open lostlist file
        if os.path.isfile(args.hostlist):
            try:
                f = open(args.hostlist, 'r')
            except:
                logger.error('Could not open file {}.'.format(args.hostlist))
                print ('Could not open file {}'.format(args.hostlist))
        else:
            logger.error('Could not find file {}.'.format(args.hostlist))
            print ('Could not find file {}'.format(args.hostlist))
            return
        for host in f:
            if check_host(host):
                #check_ips.append(check_host(host))
                check_ips[check_host(host)] = host
        try:
            f.close()
        except:
            logger.error('Could not close file {}.'.format(args.hostlist))
            print ('Could not find file {}'.format(args.hostlist))


    if args.list_hosts:
        # print hosts, then exit
        for ip in check_ips:
            print (ip)
        return

    # a list of devices to operate on
    devices = []
    for ip, host in check_ips.items():
        dev = JunosDevice(ip, user=username, userPassword=password  )
        dev.hostname = host
        devices.append(dev)

    # try to run the command
    if 'inventory' not in dir():
        inventory = unsible_init()

    #print output
    if 'configure' in args:
        # read config file
        if os.path.isfile(args.configure):
            try:
                f = open(args.configure, 'r')
            except:
                print (colorize ("Cound't open file {}".format(args.configure), 'red'))
                return
            config_template = f.read()
            f.close()
        else:
            print (colorize ("File {} not found.".format(args.configure), 'red'))
            return
        for device in devices:
            connection_attempt(device)
            # see if we want to skip interacivity
            if args.yes:
                device.yes_to_questions = True
            # set a default for the commit timer
            if args.confirmed:
                device.commit_timer = args.confirmed
            print ("\n")
            name = inventory.resolver(device.ip)
            print (colorize(" "*80, 'reverse'))
            if name:
                title = 'Configuring {} ({})'.format(name, device.ip)
            else:
                title = 'Configuring {}'.format(device.ip)
            # center the title in a 80 col display
            padding = int(80 - len(title) / 2)
            title_h = " "*padding +  title
            while len(title_h) < 81:
                 title_h += ' '
            print (colorize(title_h, 'reverse'))
            print (colorize(" "*80, 'reverse'))

            result = device.configure_interactive(config_template)



    def write_to_file(data, prefix=None, ip=None, device=None,
                      header=None, postfix='txt', delete=False,
                     xml=False):
        # if xml is set, then all non-tagged ouput is wrapped in an XML comment
        output_dir = '/tmp'
        mydate = str(datetime.date.today().isoformat())
        if not prefix:
            prefix = 'unsible'
        if args.output_dir:
            if not os.path.isdir(args.output_dir):
                print (colorize ('Could not find directory {}'.format(args.output_dir), 'red'))
                return
            else:
                output_dir = args.output_dir
        if args.separate:
            if postfix:
                pf = '.{}'.format(postfix)
            else:
                pf = ''
            if ip:
                output_filename = "{}_{}_{}{}".format(prefix, ip, mydate, pf)
            elif device:
                if device.hostname:
                    output_filename = "{}_{}_{}{}".format(prefix, device.hostname, mydate, pf)
                else:
                    output_filename = "{}_{}_{}{}".format(prefix, device.ip, mydate, pf)
            else:
                print (colorize ('Need IP or hostname for separate files', 'red'))
                sys.exit(0)
        else:
            if postfix:
                output_filename = "{}_{}.{}".format(prefix, mydate, postfix)
            else:
                output_filename = "{}_{}".format(prefix, mydate)

        # header
        separater = ("#"*80 + "\n"*2)
        if device:
            if device.hostname:
                info = "# {} ({}) ".format(device.hostname, device.ip)
            else:
                info = "# {} ".format(device.ip)
            if header:
                info += header + '\n'
        else:
            info = "# "
            if header:
                info += header
            info += '\n'

        # check for output file
        if args.separate:
            # open the file and write to it
            output_file = open(os.path.join( output_dir, output_filename ), 'w')
        else:
            if delete:
                #clobber the file if the delte flag is set
                mode = 'w'
            else:
                # open the file for appending
                mode = 'a'
            output_file = open(os.path.join( output_dir, output_filename ), mode)
        if xml:
            separater = '<!-- {} -->'.format(separater.strip())
            info = '<!-- {} -->'.format(info.strip())
        output_file.write(separater)
        output_file.write(info)
        if data:
            output_file.write(data)
        output_file.close()


    if 'command' in args:
        # reqfuse to do any request commands
        if args.command.strip()[:7] == 'request':
            print (colorize('Cowardly refusing to do any request commands: "{}"!'.format(args.command), 'red'))
            sys.exit(0)

        # write to file if requested
        if not args.output_file:
            command_prefix = 'CLI_' + args.command.replace(" ", "_")
        else:
            command_prefix = args.output_file
        header = "CLI Command: {}".format(args.command)
        # delete any file that we are going to append to firs
        write_to_file(None, prefix=command_prefix, header=header, delete=True )
        for device in devices:
            connection_attempt(device)
            try:
                if not device.device.connected:
                    device.open()
                output = device.cli(args.command)
                device.close()
                if device.failed:
                    write_to_file("Failed.\n", prefix=command_prefix,
                                  device=device, header=header )
                elif device.cli_output:
                    write_to_file(device.cli_output, prefix=command_prefix,
                                  device=device, header=header )
                elif device.cli_output:
                    write_to_file('No results.\n', prefix=command_prefix,
                                  device=device, header=header )
            except:
                print (colorize('Could not run "{}" on {}'.format(args.command, device.ip), 'red'))

    if 'commit' in args:
        for device in devices:
            connection_attempt(device)
            #print (colorize("Performing a commit on {}:".format(device.ip), 'blue'))
            try:
                if not device.device.connected:
                    device.open()
                output = device.commit()
                device.close()
            except Exception as e:
                print (colorize("Commit on {} failed: {}".format(device.ip, e), 'red'))

    if 'rollback' in args:
        for device in devices:
            connection_attempt(device)
            try:
                if not device.device.connected:
                    device.open()
                if args.r:
                    rollback_num = args.r
                else:
                    rollback_num = 1
                output = device.rollback(rollback_num)
                device.close()
            except:
                print ("Couldn't connect to device.")

    if 'copyto' in args:
        for device in devices:
            connection_attempt(device)
            try:
                if not device.device.connected:
                    device.open()
                if args.destination:
                    destination_file = args.destination
                    output = device.scp_put(args.source_file, destination_file)
                else:
                    output = device.scp_put(args.source_file)
            except Exception as e:
                print ("Couldn't connect to device.", e)

    if 'inventory' in args:
        if not args.output_file:
            command_prefix = 'INVENTORY_'
        else:
            command_prefix = args.output_file
        header = "Chassis Inventory"
        # delete any file that we are going to append to first
        if not args.separate:
            write_to_file(None, prefix=command_prefix, header=header,
                          delete=True, xml=args.xml )
        for device in devices:
            connection_attempt(device)
            try:
                if not device.device.connected:
                    device.open()
                if args.xml:
                    xml = True
                else:
                    xml = False
                output = device.inventory(xml=xml)
            except Exception as e:
                print ("Couldn't connect to device.", e)
            if device.failed:
                write_to_file("Failed.\n", prefix=command_prefix,
                              device=device, header=header )
            elif device.chassis_text:
                write_to_file(device.chassis_text, prefix=command_prefix,
                              device=device, header=header )
            elif len(device.chassis_xml):
                output = etree.tostring(device.chassis_xml)
                write_to_file(output, prefix=command_prefix, device=device,
                              header=header, postfix='xml',
                              xml=xml
                             )
    # storage cleanup
    if 'storage' in args:
        for device in devices:
            connection_attempt(device)
            try:
                if not device.device.connected:
                    device.open()
                output = device.system_storage_cleanup(confirm=args.yes)
            except Exception as e:
                print ("Couldn't connect to device.", e)


    # close devices
    for device in devices:
        #print "DEVICE:", device.device.facts
        if device.device.connected:
            device.close()
        else:
            #print (colorize("Couldn't close device {}".format(device.ip), 'red'))
            pass

    # list failures
    failed_ips = []
    # see if there were any failures
    failures = False
    for device in devices:
        if device.failed:
            failures = True

    # if there were any failures, then report and record them
    if failures:
        print (colorize( "="*80, 'bold'))
        print (colorize( "\n\nFAILURES:\n", 'bold'))
        for device in devices:
            if device.failed:
                if device.error:
                    print (colorize( "FAILURE REASON: {} {}".format(device.ip, device.error), 'red'))
                else:
                    print (colorize ("FAILURE: {}".format(device.ip), 'red'))
                failed_ips.append(device.ip)
        # write the falures to a file
        if len(failed_ips):
            print (colorize( "Recording failures:", 'bold'))
            mydate = str(datetime.date.today().isoformat())
            myfile = "failures_" + mydate + '.ips'
            mydir = '/tmp/'
            fail_file = open(os.path.join( mydir, myfile ), 'w')
            for ip in failed_ips:
                fail_file.write(str(ip) + '\n')
            fail_file.close()
            print (colorize( "Wrote {} failures to {}".format(len(failed_ips), os.path.join( mydir, myfile )), 'bold'))


    logger.debug('----------------------------------END __main__')


if __name__ == '__main__':
    main()
