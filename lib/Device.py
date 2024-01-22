# 22.01.2024 - updated for python3 
# 
# kcope@juniper.net
#
from jnpr.junos import Device
from jnpr.junos.exception import *
from jnpr.junos.utils.scp import SCP
from jnpr.junos.utils.config import Config
from jnpr.junos.utils.fs import FS
from netaddr import IPAddress, IPNetwork, valid_ipv4, valid_ipv6, iter_iprange
import logging
import time
import sys
from terminal_colors import colorize
from lxml import etree

class JunosDevice(object):
    """
    This is a router/switch Junos device that will be queried
    """


    def __init__(self, ip, user="juniper", userPassword="juniper123"):
        """
        Device should be an  IP address object
        """

        self.__version__ = "Revision: 24.01.2024"
        self.__author__ = "KLC"

        self.deviceUser = user
        self.devicePassword = userPassword
        self.ip = ip
        self.hostname = None
        self.timeout = 180
        self.device = Device(str(self.ip), user=self.deviceUser, password=self.devicePassword, timeout=self.timeout)
        self.logger = logging.getLogger()
        self.lsp_map = None # a lsp map of the device

        # bind a config object from the device
        self.cu = Config(self.device)
        # set the commit timeout
        self.cu.timeout = self.timeout
        # put the cu in exclusive mode if possible
        if 'mode' in dir(self.cu):
            self.cu.mode='exclusive'
        # bind to a FileSystem object
        self.fs = FS(self.device)
        self.yes_to_questions = False  # answer all interactive questions as yes (skip)
        self.commit_timer = 0 # commit timer in minutes
        self.print_output = True # print the output to stdout

        self.failed = False  # set to True if the last command (method) returned a failure
        self.error = None  # any exceptions 
        self.error_mesg = None  # error messages

        self.cli_output = None  # output from a cli command
        self.chassis_xml = None  # output from a get-chassis-inventory rpc
        self.chassis_text = None  # output from a get-chassis-inventory rpc in text format


    def __str__(self):
        output = "======================================================\n"
        output += "User:" + self.deviceUser + "\n"
        output += "Password:" + self.devicePassword + "\n"
        output += "DUT IP:" + str(self.ip) + "\n"
        output += "DUT Hostname:" + str(self.hostname) + "\n"
        output += "======================================================\n"
        return output

    def ts_print(self, mystring):
        # thread safe version of print 
        sys.stdout.write(mystring)
        sys.stdout.write("\n")
        #sys.stdout.flush()

    @property
    def comment(self):
        # return a comment for a commit message
        comment = "PyEZ FrontEnd" + self.__version__ + " " + self.__author__
        return comment

    def close(self):
        """
        Call and process exceptions for device.close()
        """
        try:
            self.device.close()
            return True
        except Exception as e:
            mesg = "Could not close connection to {}".format(self.ip)
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            self.logger.error(mesg)
            self.failed = True
            self.error = e
            return False

    def lock(self):
        """
        Lock the config
        """
        try:
            result = self.cu.lock()
            if result and self.print_output:
               self.ts_print(colorize("Configuration locked.", 'cyan'))
            return result
        except LockError as e:
            mesg = "Could not lock configuration: {}".format(e)
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            self.failed = True
            self.error = e
            self.logger.error(mesg)
        except Exception as e:
            mesg =  "ERROR Locking Configuration : {}".format(e)
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            self.failed = True
            self.error = e
            self.logger.error(mesg)

    def unlock(self):
        """
        unLock the config
        """
        try:
            result = self.cu.unlock()
            if result and self.print_output:
               self.ts_print(colorize("Configuration unlocked.", 'cyan'))
            return result
        except UnlockError as e:
            mesg = "Could not unlock configuration: {}".format(e)
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            self.failed = True
            self.error = e
            self.logger.error(mesg)
        except Exception as e:
            mesg =  "ERROR Unlocking Configuration : {}".format(e)
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            self.failed = True
            self.error = e
            self.logger.error(mesg)

    def commit(self):
        """
        Do a commit on a box (to confirm a commit confirm)
        """
        if self.print_output:
            self.ts_print(colorize("Performing a commit on {}:".format(self.ip), 'bold'))
        if not self.connected:
            try:
                self.open()
            except Exception as e:
                return e
        if not self.lock():
            return
        try:
            results = self.cu.commit(comment=self.comment, timeout=self.timeout)
        except CommitError as e:
            if self.print_output:
               self.ts_print(colorize("Commit error!", 'red'))
        if results:
            if self.print_output:
               self.ts_print(colorize("Commit successful!.", 'green'))

        if not self.unlock():
            return False
        else:
            return True

    def interactive_diff(self):
        """
        Perform an interactive diff
        """
        try:
            diff = self.cu.diff()
        except Exception as e:
            self.failed = True
            self.error = e
            if self.print_output:
                self.ts_print(colorize( 'Error showing the config difference' , 'red'))
            return None

        if not diff:
            if self.print_output:
                mesg = "There are no differences to the configuration."
                self.ts_print(colorize(mesg, 'blue'))
            return None
        else:
            if self.print_output:
                self.ts_print(colorize('Results of a show configuration | compare rollback 0 ', 'bold'))
                self.ts_print(colorize( ('%'*20 + 'CONFIGURATION DIFFERENCES' + '%'*20) , 'bold'))
                self.ts_print(diff)
                self.ts_print(colorize( ('%'*20 + 'CONFIGURATION DIFFERENCES' + '%'*20) , 'bold'))
        return diff


    def configure_interactive(self, config_template):
        """
        Interacatively config the device with confirmation
        """
        if self.print_output:
            self.ts_print(colorize("The following configuration will be loaded:", 'bold'))
            self.ts_print(colorize("-"*80, 'bold'))
            self.ts_print(config_template)
            self.ts_print(colorize("-"*80, 'bold'))

        if not self.connected:
            try:
                self.open()
            except Exception as e:
                self.failed = True
                self.error = e
                return e

        if not self.lock():
            return False

        try:
            results = self.cu.load(config_template)
        except RuntimeError as e:
            if self.print_output:
                mesg = "The configuration file had problems and could not be loaded: {}".format(e)
                self.ts_print(colorize(mesg, 'red'))
                results = []
        except ConfigLoadError as e:
            if self.print_output:
                mesg = "The configuration file not be loaded: {}".format(e)
                self.ts_print(colorize(mesg, 'red'))
                results = []
        for result in results:
            if result.tag == 'ok':
                if self.print_output:
                    mesg = "Configuration successfully loaded."
                    self.ts_print(colorize(mesg, 'green'))
        # show a diff
        if len(results):
            diff = self.interactive_diff()
        if diff:
            self.commit_with_questions()
        if self.unlock():
            return True
        else:
            return False

    def commit_with_questions(self):
        """
        Commit with confirmation and chance to rollback
        """
        if not self.yes_to_questions:
            self.ts_print("\n")
            mesg = "Commit on {} (yes to commit,".format(self.ip)
            mesg += "integer to commmit confirmed)\n"
            mesg = colorize (mesg, 'bold')
            mesg += colorize( "Proceed?", 'attention' )
            # ring a bell
            sys.stdout.write('\a')
            #sys.stdout.flush()

            # get input from the terminal
            commit = input(mesg)
            if commit.lower() in ['y', 'yes', 'affirmative', 'yep']:
                confirmed_timer = 0
            elif commit.isdigit():
                try:
                    confirmed_timer = int(commit)
                except:
                    confirmed_timer = -1
            else:
                self.ts_print(colorize('Aborting commit on {}'.format(self.ip), 'cyan'))
                confirmed_timer = -1
        else:
            confirmed_timer = self.commit_timer

        if confirmed_timer >= 0:
            try:
                if self.print_output:
                    if confirmed_timer == 0:
                        mesg = colorize("Commiting.", 'cyan')
                    else:
                        mesg = "Commiting with confirmation timer of "
                        mesg += "{} minutes.".format(confirmed_timer)
                        self.ts_print(colorize(mesg, 'cyan'))
                        mesg = "Remember to perform another commit or these changes "
                        mesg += "will rollback."
                        self.ts_print(colorize(mesg, 'cyan'))
                results = self.cu.commit(comment=self.comment, confirm=confirmed_timer, timeout=self.timeout)
            except CommitError as e:
                self.failed = True
                self.error = e
                if self.print_output:
                    mesg = "Error committing: {}".format(e)
                    self.ts_print(colorize (mesg, 'red'))
            # results should be a boolean
            if results:
                if self.print_output:
                    self.ts_print(colorize ('Commit successful.', 'green'))



    @property
    def connected(self):
        """
        Return connected status
        """
        return self.device.connected

    def open(self):
        """
        Call and process exceptions for device.open()
        """
        try:
            #self.device.open(gather_facts=False, auto_probe = 1)
            self.device.open(gather_facts=False)
        except ProbeError as e:
            mesg = "Probe failed on {}.".format(self.ip)
            self.logger.error(mesg)
            self.failed = True
            self.error = e
            self.error_mesg = mesg
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            raise
        except ConnectAuthError as e:
            mesg = "Connecttion failed to {} as user {}".format(self.ip, self.deviceUser)
            mesg += " . Bad login credentials."
            self.logger.error(mesg)
            self.failed = True
            self.error = e
            self.error_mesg = mesg
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            raise
        except ConnectRefusedError as e:
            mesg = "Connection refused to {}.".format(self.ip)
            mesg += " NETCONF not enabled or blocked."
            self.logger.error(mesg)
            self.failed = True
            self.error = e
            self.error_mesg = mesg
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            raise
        except ConnectTimeoutError as e:
            mesg = "Connection to {} timed out.".format(self.ip)
            self.logger.error(mesg)
            self.failed = True
            self.error = e
            self.error_mesg = mesg
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            raise
        except ConnectError as e:
            mesg = "Connection  problem to {}:".format(self.ip)
            self.logger.error(mesg)
            self.failed = True
            self.error = e
            self.error_mesg = mesg
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            raise
        except Exception as e:
            mesg = "ERROR: {}".format(e)
            self.logger.error(mesg)
            return e

        if not self.lock():
            return False

        try:
            results = self.cu.load(config_template)
        except RuntimeError as e:
            if self.print_output:
                mesg = "The configuration file had problems and could not be loaded: {}".format(e)
                self.ts_print(colorize(mesg, 'red'))
                results = []
        except ConfigLoadError as e:
            if self.print_output:
                mesg = "The configuration file not be loaded: {}".format(e)
                self.ts_print(colorize(mesg, 'red'))
                results = []
        for result in results:
            if result.tag == 'ok':
                if self.print_output:
                    mesg = "Configuration successfully loaded."
                    self.ts_print(colorize(mesg, 'green'))
        # show a diff
        if len(results):
            diff = self.interactive_diff()
        if diff:
            self.commit_with_questions()

        if self.unlock():
            return True
        else:
            return False

    def commit_with_questions(self):
        """
        Commit with confirmation and chance to rollback
        """
        if not self.yes_to_questions:
            print ("\n")
            mesg = "Commit on {} (yes to commit,".format(self.ip)
            mesg += "integer to commmit confirmed)\n"
            mesg = colorize (mesg, 'bold')
            mesg += colorize( "Proceed?", 'attention' )
            commit = input(mesg)
            if commit.lower() in ['y', 'yes', 'affirmative', 'yep']:
                confirmed_timer = 0
            elif commit.isdigit():
                try:
                    confirmed_timer = int(commit)
                except:
                    confirmed_timer = -1
            else:
                self.ts_print(colorize('Aborting commit on {}'.format(self.ip), 'cyan'))
                confirmed_timer = -1
        else:
            confirmed_timer = self.commit_timer

        if confirmed_timer >= 0:
            try:
                if self.print_output:
                    if confirmed_timer == 0:
                        mesg = colorize("Commiting.", 'cyan')
                    else:
                        mesg = "Commiting with confirmation timer of "
                        mesg += "{} minutes.".format(confirmed_timer)
                        self.ts_print(colorize(mesg, 'cyan'))
                        mesg = "Remember to perform another commit or these changes"
                        mesg += "will rollback."
                        self.ts_print(colorize(mesg, 'cyan'))
                results = self.cu.commit(comment=self.comment, confirm=confirmed_timer, timeout=self.timeout)
            except CommitError as e:
                self.failed = True
                self.error = e
                if self.print_output:
                    mesg = "Error committing: {}".format(e)
                    self.ts_print(colorize (mesg, 'red'))
            except RpcTimeoutError as err:
                self.failed = True
                self.error = err
                if self.print_output:
                    mesg = "Timeout while committing: {}".format(err)
                    self.ts_print(colorize (mesg, 'red'))
            except Exception as err:
                self.failed = True
                self.error = err
                if self.print_output:
                    mesg = "Error: {}".format(err)
                    self.ts_print(colorize (mesg, 'red'))
            # results should be a boolean
            if results:
                if self.print_output:
                    self.ts_print(colorize ('Commit successful.', 'green'))


    @property
    def connected(self):
        """
        Return connected status
        """
        return self.device.connected

    def open(self):
        """
        Call and process exceptions for device.open()
        """
        try:
            #self.device.open(gather_facts=False, auto_probe = 1)
            self.device.open(gather_facts=False)
        except ProbeError as e:
            mesg = "Probe failed on {}.".format(self.ip)
            self.logger.error(mesg)
            self.failed = True
            self.error = e
            self.error_mesg = mesg
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            raise
        except ConnectAuthError as e:
            mesg = "Connecttion failed to {} as user {}".format(self.ip, self.deviceUser)
            mesg += " . Bad login credentials."
            self.logger.error(mesg)
            self.failed = True
            self.error = e
            self.error_mesg = mesg
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            raise
        except ConnectRefusedError as e:
            mesg = "Connection refused to {}.".format(self.ip)
            mesg += " NETCONF not enabled or blocked."
            self.logger.error(mesg)
            self.failed = True
            self.error = e
            self.error_mesg = mesg
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            raise
        except ConnectTimeoutError as e:
            mesg = "Connection to {} timed out.".format(self.ip)
            self.logger.error(mesg)
            self.failed = True
            self.error = e
            self.error_mesg = mesg
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            raise
        except ConnectError as e:
            mesg = "Connection  problem to {}:".format(self.ip)
            self.logger.error(mesg)
            self.failed = True
            self.error = e
            self.error_mesg = mesg
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            raise
        except Exception as e:
            mesg = "ERROR: {}".format(e)
            self.logger.error(mesg)
            self.failed = True
            self.error = e
            self.error_mesg = mesg
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))
            raise

    def cli(self, command):
        """
        Execute a cli command on a device
        """
        if self.print_output:
            self.ts_print("\n")
            self.ts_print(colorize("-"*80, 'bold'))
            self.ts_print(colorize('Executing cli command "{}" on {}'.format(command, self.ip), 'bold'))
            self.ts_print(colorize("-"*80, 'bold'))
        try:
            self.cli_output = self.device.cli(command, warning=False)
            if self.print_output:
                self.ts_print(self.cli_output)
                self.ts_print(colorize("-"*80, 'bold'))
        except:
            self.failed = True
            self.error = e
            self.cli_output = None
        return self.cli_output

    def scp_get(self, source_file, destination_file):
        with SCP(self.device, progress=True) as scp:
            scp.get( source_file, destination_file)

    def scp_put(self, source_file, destination_file=None):
        if not destination_file:
            # need to figure out users home directory
            fs = FS(self.device)
            home_dir=fs.pwd()
            destination_file = home_dir

        mesg = "Secure copy (scp) {} to {} on {}".format(source_file, destination_file, self.ip)
        if self.print_output:
            self.ts_print(colorize (mesg, 'blue'))
        with SCP(self.device, progress=True) as scp:
            try:
                scp.put( source_file, destination_file)
            except Exception as e:
                self.failed = True
                self.error = e
        mesg = "Success copying {} to {} on {}".format(source_file, destination_file, self.ip)
        if self.print_output:
            self.ts_print(colorize (mesg, 'green'))

    def system_storage_cleanup(self, confirm=True):
        # do a system storage cleanup, return dict of files that were removed
        if self.print_output:
            if self.hostname:
                self.ts_print(colorize('Cleaning filesystem storage on {} ({})'.format(self.hostname,
                                                                               self.ip), 'bold'))
            else:
                self.ts_print(colorize('Cleaning filesystem storage on {}'.format(self.ip), 'bold'))
        if not self.connected:
            try:
                self.open()
            except Exception as e:
                return e
        if not confirm:
            filelist = self.fs.storage_cleanup_check()
            if len(filelist) == 0:
                self.ts_print(colorize('No files identified for delettion.', 'cyan'))
                return True
            mesg = "{:52} {:14}   {:>10}".format('Filename', 'Date', 'Size(bytes)')
            self.ts_print("\n")
            self.ts_print(colorize (mesg, 'underline'))
            for myfile in filelist:
                ts_date = filelist[myfile]['ts_date']
                size = filelist[myfile]['size']
                mesg = "{:50} {:>14}   {:>10}".format(myfile, ts_date, size)
                self.ts_print(mesg)
            self.ts_print("\n")
            mesg = "Delete these files on on {} (y,".format(self.ip)
            mesg += "/n)\n"
            mesg = colorize (mesg, 'bold')
            mesg += colorize( "Proceed?", 'attention' )
            # ring a bell
            sys.stdout.write('\a')
            #sys.stdout.flush()

            # get input from the terminal
            commit = input(mesg)
            if not commit.lower() in ['y', 'yes', 'affirmative', 'yep']:
                self.ts_print(colorize('Aborting file deletion on {}'.format(self.ip), 'cyan'))
                return False

        try:
            filelist = self.fs.storage_cleanup()
            self.ts_print(colorize('Filesystem cleaned up on  {}'.format(self.ip), 'green'))
        except Exception as e:
            mesg = "Problem deleting files on {}.".format(self.ip)
            self.logger.error(mesg)
            self.failed = True
            self.error = e
            self.error_mesg = mesg
            if self.print_output:
                self.ts_print(colorize( mesg, 'red'))

        return True

    def rollback(self, rollback_num=1):
        """
        Interacatively rollback the config
        """
        if self.print_output:
            self.ts_print(colorize('Performing a "rollback {}"'.format(rollback_num), 'bold'))

        if not self.connected:
            try:
                self.open()
            except Exception as e:
                return e

        if not self.lock():
            return False

        if self.print_output:
            self.ts_print(colorize('Rolling back configuration', 'cyan'))
        try:
            results = self.cu.rollback(rollback_num)
        except ValueError as e:
            self.failed = True
            self.error = e
            if self.print_output:
                self.ts_print(colorize('Aborting rolback: {}'.format(e), 'red'))
                self.unlock()
                return

        # show a diff
        diff = self.interactive_diff()
        if diff:
            self.commit_with_questions()

        if self.unlock():
            return True
        else:
            return False



    def inventory(self, xml=False):
        """
        Return an XML formatted inventory from the device
        """
        if self.print_output:
            self.ts_print("\n")
            self.ts_print(colorize("-"*80, 'bold'))
            if self.hostname:
                self.ts_print(colorize('Fetching inventory from {} ({})'.format(self.hostname, self.ip),
                               'bold'))
            else:
                self.ts_print(colorize('Fetching inventory from {}'.format(self.ip), 'bold'))
            self.ts_print(colorize("-"*80, 'bold'))
        if not self.connected:
            try:
                self.open()
            except Exception as e:
                return e
        if self.print_output:
            self.ts_print(colorize('Fetching chassis inventory', 'cyan'))
        try:
            if xml:
                self.chassis_xml = self.device.rpc.get_chassis_inventory({'format':'xml'})
            else:
                text = etree.tostring(self.device.rpc.get_chassis_inventory({'format':'text'}),
                                      pretty_print=True)
                self.chassis_text = ""
                for line in text.split('\n'):
                    if line not in ['<output>', '</output>']:
                        self.chassis_text += line + '\n'
        except Exception as e:
            if self.print_output:
                self.ts_print(colorize('Could not retrieve chassis inventory', 'red'))
            self.failed = True
            self.error = e
            return
        # return the text, or a text version of the etree object
        if self.print_output:
            if xml:
                self.ts_print(etree.tostring(self.chassis_xml, pretty_print=True))
            else:
                self.ts_print(self.chassis_text)
        if xml:
            return etree.tostring(self.chassis_xml, pretty_print=True)
        else:
            return self.chassis_text


