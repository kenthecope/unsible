"""
24.01.2024 - update to python3
10.12.2017 - add host and group variables to inventory

kcope@juniper.net

"""

import os
import yaml
from netaddr import IPAddress
import logging

class Inventory(object):
    """
    Read in ansible inventories without ansible modules
    """
    def __init__(self, directory=None, devicelist='hosts'):
        """
        directory is the location of the ansible inventory dir
        """
        self.logger = logging.getLogger()
        self.directory = directory
        self.devicelist = devicelist
        self.default_key = None # this is the first key found in the hosts file
        self.inventory = {}
        self.inventory_derefrenced = False # flag to indicate if we derefed inventory fully
        self.inventory_files = {}
        # for variable processing
        self.vars = {}
        self.group_vars = {}
        self.host_vars = {}
        # these should be YAML files
        self.group_vars_files = {}
        self.host_vars_files = {}
        # this is a builtin resolver to resolve IP addresses to hostnames
        self.resolve_ip_to_hostname = {}
        self.resolve_hostname_to_ip = {}


    def build_resolver(self):
        # parse the inventory and build resolver tables
        for key in self.inventory:
            if isinstance(self.inventory[key], list):
                if self.inventory[key]:
                    self.add_to_resolver(key, self.inventory[key][0])
        # parse the host vars
        for key in self.host_vars:
            if isinstance(self.host_vars[key], dict):
                for h_key, h_value in self.host_vars[key].items():
                    self.add_to_resolver(key, h_value)


    def add_to_resolver(self, hostname, ip):
        # adds the ip and hostname to the resolver dictionaries
        # add to the ip_to_hostname dict
        if isinstance(ip, bool):
            return False
        elif isinstance(ip, int):
            return False
        elif isinstance(ip, str):
            if '/'  in ip:
                parsed_ip = ip.split('/')[0]
            else:
                parsed_ip = ip
        else:
            parsed_ip = ip

        try:
            myip = IPAddress(parsed_ip)
        except:
            return False
        self.resolve_ip_to_hostname[myip] = hostname
        # add to the hostname to ip, this is a dictionary of lists
        if hostname not in self.resolve_hostname_to_ip:
            self.resolve_hostname_to_ip[hostname] = []
        if ip not in self.resolve_hostname_to_ip[hostname]:
            self.resolve_hostname_to_ip[hostname].append(myip)

    def resolver(self, box):
        # resolve the box to a hostname if it an IP address, or
        # retrun a list of IPs if it is a hostname
        try:
            ip = IPAddress(box)
        except:
            ip = None
        if ip:
            if ip in self.resolve_ip_to_hostname:
                return self.resolve_ip_to_hostname[ip]
            else:
                return None
        else:
            if box in self.resolve_hostname_to_ip:
                return self.resolve_hostname_to_ip[box]
            else:
                return []


    def load_vars(self, vars_path):
        # load variables from a directory
        mydict = {}
        my_vars_path = os.path.join(self.directory, '..', vars_path)
        if os.path.isdir(my_vars_path):
            # load files for parsing into dictionary
            for myfile in os.listdir(my_vars_path):
                # only open .yml files
                if os.path.isfile(os.path.join(my_vars_path, myfile)):
                    try:
                        with open(os.path.join(my_vars_path, myfile), 'r') as ymlfile:
                            myvar = myfile.split('.yml')[0]
                            mydict[myvar] = yaml.load(ymlfile)
                    except:
                        # not a valid yaml file
                        pass
        return mydict


    def load_group_vars(self):
        self.group_vars = self.load_vars('group_vars')

    def load_host_vars(self):
        self.host_vars = self.load_vars('host_vars')

    @property
    def parents(self):
        """
        This returns an inventory list that only shows
        parents
        """
        parents = {}
        for key, value in self.inventory.items():
            if ':' in key:
                if key.split(':')[-1] == 'children':
                    new_key = key.split(':')[0]
                    parents[new_key] = value
        return parents

    def has_children(self, key):
        # checks a key to see if it ends in :children
        if key.split(':')[-1] == 'children':
            return True
        else:
            return False

    def parent_key(self, key):
        # returns the parent of a key that has children
        # or the key itself if there are no kids
        if key.split(':')[-1] == 'children':
            return key.split(':')[0]
        else:
            return key


    def lookup(self, lookup_val):
        """
        This method returns a fully dereferenced
        list from the inventory
        """
        dref_list = []  # fully dereferenced list
        children_list = []  # a list of children waiting to be drefed
        sub_children_list = []  # a list of children waiting to be drefed


        def dref_file_check(lookup_val):
            # check lookup value to see if there is a entry in the main inventory
            found_key = False   # did we find the lookup value?
            for key in self.inventory:
                if self.parent_key(key) == lookup_val:
                    found_key = True
            # if we didn't find they key in self.inventory, look for it in the files
            if not found_key:
                if lookup_val in self.inventory_files:
                    for key, value in self.inventory_files[lookup_val].items():
                        # add to main inventory
                        self.inventory[key] = value

        # first pass
        # see if the key is already drefed
        if lookup_val in self.inventory:
            for val in self.inventory[lookup_val]:
                dref_list.append(val)
        elif lookup_val in self.parents:
            for child in self.parents[lookup_val]:
                children_list.append(child)
        else:
            # not in inventory at all
            dref_list = []

        children_list_new = []
        # loop until completely drefed
        while children_list:
            for child in children_list:
                if child in self.parents:
                    for kid in self.parents[child]:
                        if kid not in children_list:
                            children_list_new.append(kid)
                        elif child in self.inventory:
                            dref_list.append(self.inventory[child][0])
                            # remove from list
                        else:
                            pass
                elif child in self.inventory:
                    dref_list.append(self.inventory[child][0])
                else:
                    pass
            # clean up and reset lists
            del(children_list)
            children_list = list(children_list_new)
            children_list_new = []

        return dref_list


    def load(self):
        """
        Loads the main inventory and sub inventories from individual files
        Also finds the default (first) key in the hosts file
        """
        # check for directory
        def inv_dict(raw_lines):
            """
            Return a dictionary suitable for
            adding to an inventory
            """
            myinventory = {}
            for line in raw_lines:
                if line[0] == '[' and line.strip()[-1] == ']':
                    key = line.strip()[1:-1]
                    myinventory[key] = []
                    # see if this is the first key
                    if not self.default_key:
                        # conditioins for using it as the default key
                        if key.split(':')[-1] == 'children':
                            # has to be a child
                            self.default_key = key.split(':')[0]
                        elif ':' not in key:
                            # or a standalone variable
                            self.default_key = key
                elif line[0] in ['#', '\n']:
                    # comment 
                    pass
                elif len(line.strip()) > 0:
                    myinventory[key].append(line.strip())
            return myinventory

        if not self.directory:
            print ("ERROR: ansible inventory directory not set")
            return False
        else:
            if not os.path.isdir(self.directory):
                mesg = "ERROR: ansible inventory directory "
                mesg += "{} does not exist!".format(self.directory)
                print (mesg)
                return False


        def parse_inv_file(filename):
            """
            Parse an inventory file into the self.inventory_files dict
            """
            file_path = (os.path.join(self.directory, filename))
            if os.path.isfile(file_path):
                # load file for parsing into dictionary
                file_data = open(file_path, 'r')
                raw_lines = []
                for line in file_data.readlines():
                    raw_lines.append(line)
                file_data.close()
            # create a dictionary for the file contents
            file_dict = {}
            for key, value in inv_dict(raw_lines).items():
                file_dict[key] = value
                self.inventory[key] = value
            # add the dictionary to self.inventory_files 
            # using the filename as a key
            self.inventory_files[filename] = file_dict

        # load each file in the directory into the self.inventory_files
        # variable.  the filename will be used as the key, and the 
        # file contents will be the value (per file)

        for myfile in os.listdir(self.directory):
            if os.path.isfile(os.path.join(self.directory, myfile)):
                # add file contents to self.inventory_files
                parse_inv_file(myfile)


