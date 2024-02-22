"""
A class to store some terminal colors
Copyright 2023 Juniper Networks, Inc. All rights reserved.
Licensed under the Juniper Networks Script Software License (the "License").
You may not use this script file except in compliance with the License, which
is located at
http://www.juniper.net/support/legal/scriptlicense/
Unless required by applicable law or otherwise agreed to in writing by the
parties, software distributed under the License is distributed on an "AS IS"
BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
"""
import time

class bcolors:
    RED   = "\033[1;31m"
    BLUE  = "\033[1;34m"
    CYAN  = "\033[1;36m"
    GREEN = "\033[0;32m"
    RESET = "\033[0;0m"
    BOLD    = "\033[;1m"
    REVERSE = "\033[;7m"
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ATTENTION = '\033[38;5;196;48;5;21m'

def colorize( text, color ):
    """
    Print out the text using the specified color
    If the color does not exist in bcolors, then
    ignore the color
    """
    if color.upper() not in dir(bcolors):
       return text
    mycolor = getattr( bcolors, color.upper())
    mesg = mycolor + text + bcolors.ENDC
    return mesg

def pad_ansi_width(text):
   """
   determines if the string tarts with any of the bcolors class
   definitions, and if so, returns and adjusted width of the
   text that includes the pad
   """
   print ('\n'*30)
   print ("TEXT", text)
   for attribute in dir(bcolors):
       if attribute[:2] != '__':
           my_attr = getattr(bcolors, attribute)
           len_attribute = len(my_attr)
           if text[:len_attribute] == my_attr:
               return len_attribute
   return 0
