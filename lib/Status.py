"""
This is a status object
Copyright 2023 Juniper Networks, Inc. All rights reserved.
Licensed under the Juniper Networks Script Software License (the "License").
You may not use this script file except in compliance with the License, which
is located at
http://www.juniper.net/support/legal/scriptlicense/
Unless required by applicable law or otherwise agreed to in writing by the
parties, software distributed under the License is distributed on an "AS IS"
BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
"""

import curses
from curses import wrapper
import datetime
import time


class Status(object):
    def __init__(self, name = None, stdscr=None):
        self.name = name
        self.stdscr = stdscr # curses display object
        self.column_headers = [] # headers for all of the collumns
        self.columns = [] # this should contain a list of columns, a column shuld be a line
                          # of data we which to output

    def display(self):
        if not self.stdscr:
            # no curses display to write to
            return False
        quit = False
        h_old = -1
        w_old = -1
        i = 0
        self.stdscr.nodelay(True)
        down = False
        warning = curses.A_NORMAL
        curses.curs_set(0)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_WHITE)
        self.stdscr.refresh()
        while not quit:
            h,w = self.stdscr.getmaxyx()
            if h != h_old or w != w_old:
                self.stdscr.clear()
                h_old = h
                w_old = w
            self.stdscr.box()
            self.stdscr.hline(3,1, curses.ACS_HLINE, w-2)
            self.stdscr.addstr(1,1,'LSP Information', curses.A_BOLD)
            tim = time.time()
            t = time.localtime(tim)
            mytime = time.ctime(tim)
            self.stdscr.addstr(1,1,'LSP Information', curses.A_BOLD)
            self.stdscr.addstr(1,w-len(mytime)-1,'{}'.format(mytime), curses.A_BOLD)
            self.stdscr.addstr(5,1,'HEIGHT: {}'.format(h))
            self.stdscr.addstr(6,1,'WIDTH : {}'.format(w))
            self.stdscr.addstr(8,1,'i : {} '.format(i))
            self.stdscr.addstr(9,1,'Status: {} '.format(down), warning)
            self.stdscr.addstr(10,1,'BOLD', curses.A_BOLD)
            self.stdscr.addstr(11,1,'BLINK', curses.A_BLINK)
            self.stdscr.addstr(12,1,'REVERSE', curses.A_REVERSE)
            self.stdscr.addstr(13,1,'STANDOUT', curses.A_STANDOUT)
            self.stdscr.addstr(14,1,'UNDERLINE', curses.A_UNDERLINE)
            self.stdscr.addstr(15,1,'RED', curses.color_pair(1))
            curses.napms(1000)
            i += 1
            c = self.stdscr.getch()
            if c == ord('q'):
                self.stdscr.addstr(5,1, "QUIT")
                quit = True
            elif c == ord('d'):
                if down:
                    down = False
                    warning = curses.A_NORMAL
                else:
                    down = True
                    warning = curses.A_BLINK
            self.stdscr.refresh()

    def __str__(self):
        return "WTF!!!\n"

    def clear_data(self):
        self.columns = []

