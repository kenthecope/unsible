# 24.01.2024 - update to python3
# kcope@juniper.net

from populate_lsp import populate_lsp_info
from jnpr.junos.exception import *
import time
import logging
import random
from terminal_colors import bcolors
from terminal_colors import colorize
from terminal_colors import pad_ansi_width
from bandwidth import Bandwidth
import sys
import os
import re

class LSPDisplay(object):
    """
    show a screen
    """
    def __init__(self):
        self.logger = logging.getLogger()

        # some flags to control curses layout
        self.auto_layout = False

        self.status = "Initializing..."   # The last status from a thread job
        self.errors = "None"   # The last error from a thread job

        self.header = []  # this is a list of items to be placed in the header
        self.header_text = ""  # actual text of the header
        self.col_width = {}  # this is a dictionary of colums to how wide they should be
                             # the keys are the items in self.header and the values are
                             # integers based on the length of text in the  

        self.title_text = 'LSP Information'
        self.show_time()

        # collumn display definitions
        # dictionary of colum number, to a list of the lsp attribute to display name, and the column width
        self.col_header = { 0: ['name', 'Name', 30],
                            1: ['ccsd','CCSD', 6],
                            2: ['vpn','L3VPN', 20],
                            3: ['lookup_source_ip','From', 12],
                            4: ['source_address','From Address', 15],
                            5: ['lookup_destination_ip','To', 12],
                            6: ['destination_address','To Address', 15],
                            7: ['path_bandwidth','Bandwidth', 12],
                            8: ['lsp_state','State', 7],
                          }

        """
        data for each collumn, it shold look like:
        self.col_data = [ { 0: ['some text to display', 'COLOR'],
                            1: ['2nd col text', 'COLOR'],
                           ....
        """
        self.col_data = [] # data for each collumn



        self.lsps = {}   # this is a dictionary of device to lsp_map
        self.ingress_lsps_count = 0

        # inventory object from an unsible inventory - used for ip resolution
        self.inventory = None

        # hide cursor
        self.show_cursor = False

        # offset if we are not showing all of the LSPs
        self.lsp_display_offset = 0
        # lines of overhead we have, lines not displayihg lsps
        self.overhead_lines = 12
        # counter for lsps on display
        self.display_lsp_count = 0

        # filters
        self.filter_only_down = False   # only display LSPs that are down
        self.sort_by = 'name'  # sort displayed LSPs by one of the col_header[i][0] values
        self.sort_reverse = False # toggle for reversing sort torder
        self.regex = '' # a regex filter for matching LSP info

    def lsp_display_offset_decrement(self):
        if self.lsp_display_offset >= 1:
            self.lsp_display_offset -= 1

    def lsp_display_offset_increment(self):
        if self.lsp_display_offset + self.display_lsp_count < self.ingress_lsps_count:
            self.lsp_display_offset += 1


    def terminal_size(self):
        import fcntl, termios, struct
        th, tw, hp, wp = struct.unpack('HHHH', fcntl.ioctl(0, termios.TIOCGWINSZ,
                                       struct.pack('HHHH', 0, 0, 0, 0)))
        return tw, th

    @property
    def term_width(self):
        tw, th = self.terminal_size()
        return tw

    @property
    def term_height(self):
        tw, th = self.terminal_size()
        return th


    def update_display_lsps(self):
        # this method displays the lsps on the collumn pads
        self.col_data = []
        sorted_lsps = []
        lsps = []
        f_lsps = []

        # parse the lspmaps for lsps
        for ip, lsp_map in self.lsps.items():
            if lsp_map:
                for lsp in lsp_map.ingress_lsps:
                    lsps.append(lsp)

        # count the ingress lsps
        self.ingress_lsps_count = len(lsps)

        # filter the lsps baed on a regex
        attributes = []
        for i in self.col_header:
            attributes.append(self.col_header[i][0])
        if self.regex:
            for lsp in lsps:
                for attribute in attributes:
                    if attribute in dir(lsp):
                        attr = str(getattr(lsp, attribute))
                        if re.search(self.regex, attr):
                            if lsp not in f_lsps:
                                f_lsps.append(lsp)
                        elif re.search(self.regex, str(self.inventory.resolver(attr))):
                            if lsp not in f_lsps:
                                f_lsps.append(lsp)
                    elif attribute in dir(self):
                        # search on the from, to, ccsd and vpn
                        attr = str(getattr(self, attribute))
                        if re.search(self.regex, attr):
                            if lsp not in f_lsps:
                                f_lsps.append(lsp)
        else:
            f_lsps = lsps

        # sort the ingress lsps based on the sort by criteria
        # if sorting by bandwidth, parse out the active path BW to the
        # bandwidth field of the lsp before sorting
        if self.sort_by == 'bandwidth':
            for lsp in f_lsps:
                # look for active path
                for path in lsp.paths:
                    if path.path_active:
                        # if it has a bandwidth statement, set that to the LSP
                        if path.bandwidth:
                            lsp.bandwidth = path.bandwidth
                        else:
                            lsp.bandwidth = Bandwidth(0)
                    else:
                        lsp.bandwidth = Bandwidth(-1)


        sorted_lsps = sorted(f_lsps, key=lambda x: getattr(x, self.sort_by),
                             reverse=self.sort_reverse)

        # get a display line for the sorted lsps
        self.filter_lsp_count = 0
        for lsp in sorted_lsps:
            myline = self.process_lsp(lsp)
            if myline:
                self.filter_lsp_count += 1
            self.col_data.append(myline)

        #self.logger.debug('COL_PAD_DATA {}'.format(self.col_pad_data))

    def ccsd(self, lsp):
        # this is a method to process dat for a column
        # this should return a set with the ccsd and color it should be
        try:
            ccsd = lsp.name.split(':')[1]
        except:
            ccsd = None
        return ( ccsd , 'YELLOW')

    def path_bandwidth(self, lsp):
        """
        This method returns the bandwidth of the active path
        """
        for path in lsp.paths:
            if path.path_active:
                if path.bandwidth:
                    return ( str(path.bandwidth), 'YELLOW')
                else:
                    return ( '0', 'YELLOW')
        return ('', 'WHITE')

    def vpn(self, lsp):
        # this is a method to process dat for a column
        # this should return a set with the vpn and color it should be
        if ':' in lsp.name:
            try:
                vpn = lsp.name.split(':')[0]
            except:
                vpn = None
        else:
            vpn = None
        return ( vpn , 'YELLOW')

    def lookup_source_ip(self, lsp):
        # see if we can resolve the ip with the unsible inventory
        if self.inventory:
            ip = self.inventory.resolver(lsp.source_address)
            #self.logger.info("LOOKUP {}".format(ip))
        else:
            ip = None
        return ( ip, 'YELLOW')

    def lookup_destination_ip(self, lsp):
        # see if we can resolve the ip with the unsible inventory
        if self.inventory:
            ip = self.inventory.resolver(lsp.destination_address)
        else:
            ip = None
        return ( ip, 'YELLOW')


    def process_lsp(self, lsp):
        # process an lsp into a display line
        #self.logger.debug('PROCESS LSP {}'.format(str(lsp.name)))
        if self.filter_only_down and lsp.lsp_state != 'Dn':
            return  []
        parsed_output = []
        attributes = []
        for index in range(0, len(self.col_header)):
            attributes.append(self.col_header[index][0])
        for attribute in attributes:
            color = 'WHITE'
            if attribute == 'lsp_state':
                if getattr(lsp, attribute) == 'Dn':
                    color = 'RED'
                else:
                    color = 'GREEN'
            try:
                parsed_output.append(( getattr(lsp, attribute), color))
            except AttributeError:
                # we have a custom attribute, try to process it as a self function
                # feed it the lsp to work on
                # any method here should return a set in the form ('output text', curses color)
                parsed_output.append(getattr(self, attribute)(lsp))
            except Exception as e:
                self.logger.debug('ERROR {}'.format(str(e)))

        #print "PARSED_OUTPUT:", parsed_output
        return parsed_output

    @property
    def current_time(self):
        # return a string of the time
        return time.ctime(time.time())

    def show_time(self):
        # update the time in the title pad
        return self.current_time

    def __str__(self):
        self.update_display_lsps()

        # max width of display
        max_width = 0
        for i in range(0, len(self.col_header)):
            max_width += self.col_header[i][-1]

        # check that teminal width is at least 40 characters
        if self.term_width <= 40:
            o = '\033c' # clear the screen
            o += '\n'* (self.term_height / 2)
            o += "TERMINAL NEEDS TO BE \nAT LEAST 40 CHARACTERS WIDE\n"
            return colorize(o, 'RED')

        def terminal_width_filter(col):
            # return a true false if the collumn should be displayed
            # based on the width of the terminal
            col_3_and_5 = self.col_header[3][-1] + self.col_header[5][-1]
            col_3_and_5_and_7 = col_3_and_5 + self.col_header[7][-1]
            col_3572 = col_3_and_5_and_7 + self.col_header[2][-1]
            col_35721 = col_3572 + self.col_header[1][-1]
            col_3572146 = col_35721 + self.col_header[4][-1] + col_35721 + self.col_header[6][-1]

            if self.term_width >= max_width:
                return True
            # dont display from or to names
            elif self.term_width >= max_width - col_3_and_5:
                if col in [ 3, 5 ]:
                    return False
                else:
                    return True
            elif self.term_width > max_width - col_3_and_5_and_7:
                if col in [ 3, 5, 7 ]:
                    return False
                else:
                    return True
            elif self.term_width > max_width - col_3572 :
                if col in [ 3, 5, 7, 2 ]:
                    return False
                else:
                    return True
            elif self.term_width > max_width - col_35721 :
                if col in [ 3, 5, 7, 2, 1 ]:
                    return False
                else:
                    return True
            elif self.term_width > max_width - col_3572146 :
                if col in [ 3, 5, 7, 2, 1, 4, 6 ]:
                    return False
                else:
                    return True
            else:
                return True

        o = '\033c' # clear the screen
        #o = ''

        o += '{:<40}{:>{width}}\n\n'.format(colorize(self.title_text, 'BOLD'), self.current_time,
                                           width=self.term_width - 40)
        o += '  {} {}\n'.format(colorize('Status:    ', 'BOLD'), self.status)
        o += '  {} {}\n'.format(colorize('Last Error:', 'BOLD'), self.errors)

        o += '  Total LSPs {}   Displayed/Matched filter: {}/{} LSPs\n\n'.format(self.ingress_lsps_count,
                                                                                 self.display_lsp_count,
                                                                                 self.filter_lsp_count )
        #o += '  Term W {} Term H {}\n'.format(self.term_width, self.term_height)
        # process the header and ready a display line
        l = ''
        for i in range(0, len(self.col_header)):
            width = self.col_header[i][-1]
            if terminal_width_filter(i):
               l += '{:<{width}}'.format(self.col_header[i][1], width=width)
        o += colorize(l, 'UNDERLINE')
        o += '\n'
        if self.lsp_display_offset > 0:
            o += ' ^ ^ ^ ^ ^ ^ '
        o += '\n'

        # make sure lsp data is up to date
        self.update_display_lsps()

        # place this before the stats, to get a good lsp_display_count
        display_lsp_count = 0
        # display lsps (with an offset if needed) to fill up the display
        for data  in self.col_data:
            l = ''
            if data:
                display_lsp_count += 1
                for i in range(0, len(self.col_header)):
                    width = self.col_header[i][-1]
                    if data[i][0]:
                        text = colorize(data[i][0], data[i][1])
                    else:
                        text = ''
                    if terminal_width_filter(i):
                        if i in [ 7, 8]:
                            # right justify collums
                            pad_width = pad_ansi_width(text)
                            width += pad_width
                            l += '{:>{width}}'.format(text, width=width)
                        else:
                            # left justify
                            l += '{:<{width}}'.format(text, width=width)
                l += '\n'
                if display_lsp_count > self.lsp_display_offset:
                    o += l
                if display_lsp_count > self.term_height - self.overhead_lines + self.lsp_display_offset:
                    break
        self.display_lsp_count = display_lsp_count - self.lsp_display_offset

        # new lines to fill up the rest of the screen (remaining lines)
        nl_pads = 0
        for i in range(0, self.term_height - self.overhead_lines - display_lsp_count + self.lsp_display_offset):
            o += '\n'
            nl_pads += 1

        # the what to to line
        length =  0
        # display the continuation down string (if needed)
        if self.overhead_lines + self.display_lsp_count + nl_pads > self.term_height:
            if self.lsp_display_offset + self.display_lsp_count == self.filter_lsp_count:
                continue_string = ''
            else:
                continue_string = '::::::::::::'
        else:
            continue_string = ''
        o += colorize(continue_string, 'UNDERLINE')
        length -= len(continue_string)
        for i in range(0, len(self.col_header)):
            if terminal_width_filter(i):
                width = self.col_header[i][-1]
                length +=  width
        o += colorize("{}\n".format(' '*length), 'UNDERLINE')

        # options
        # a few widht sizes
        width_large = 120
        width_med = 100
        width_small = 80
        o += "[Q]uit"
        o += " "*3
        if self.filter_only_down:
            o += colorize("[D]", 'REVERSE')
            if self.term_width > width_large:
                o += "own LSPs"
        else:
            if self.term_width > width_large:
                o += "[D]own LSPs"
            else:
                o += "[D]"
        o += " "*3
        # display sorting options
        if self.term_width > width_large:
            o += "Sort by:"
        elif self.term_width > width_med:
            o += "Sort:"

        # by name
        if self.sort_by == 'name':
            o += colorize("[N]", 'REVERSE')
        else:
            o += "[N]"
        if self.term_width > width_med:
            o += "ame "

        # by bw
        if self.sort_by == 'bandwidth':
            o += colorize("[B]", 'REVERSE')
        else:
            o += "[B]"
        if self.term_width > width_med:
            o += "andwidth "

        # source addresss
        if self.sort_by == 'source_address':
            o += colorize("[S]", 'REVERSE')
        else:
            o += "[S]"
        if self.term_width > width_large:
            o += "ource IP  "
        elif self.term_width > width_med:
            o += "rc IP "

        # destination address
        if self.sort_by == 'destination_address':
            o += colorize("[T]", 'REVERSE')
        else:
            o += "[T]"
        if self.term_width > width_large:
            o += "o IP  "
        elif self.term_width > width_med:
            o += "o  "
        o += " "*3

        # sort in reverse
        if self.sort_reverse:
            o += colorize("[R]", 'REVERSE')
        else:
            o += "[R]"
        if self.term_width > width_large:
            o += "evese sort"
        elif self.term_width > width_med:
            o += "evese"
        o += " "*3

        # sort in reverse
        if self.regex:
            o += colorize("[F]", 'REVERSE')
        else:
            o += "[F]"
        if self.term_width > width_med:
            o += "ilter: {}".format(self.regex)
        else:
            o += ": {}".format(self.regex)

        if not self.show_cursor:
            o += '\033[?25l'
        else:
            o += '\033[?25h'
        #o += '\n'

        return o
