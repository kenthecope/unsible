# 22.01.2024 - update for python3
# kcope@juniper.net

import queue
import threading
from threading import Thread
import time
import sys
import logging
import signal
import random
from jnpr.junos.exception import *
from populate_lsp import populate_lsp_info
from LSP import LSPMap


class LSPfetcher(object):

    def __init__(self, boxes=[], sleep_interval=300, num_threads=1, lock=None ):
        self.sleep_interval = sleep_interval # time to wait between queries
        self.boxes = boxes                   # a list of devices to query
        self.num_threads = num_threads       # number of query threads to start

        # thread lock
        self.lock = lock
        # flag to see if it is time to quit
        self.time_to_die = False

        # logging
        self.logger = logging.getLogger()
        self.logger.info("LSPfecther init")

        # catch ctl-c
        #signal.signal(signal.SIGINT, self.sigint_handler)

        # queues for communicataion between threads
        # devices that need xml stats fetched
        self.query_jobs = queue.Queue()
        # devices (and results) of last queiry
        self.results_jobs = queue.Queue()
        # devices that are in a waiting state between queries
        self.sleeper_jobs = queue.Queue()

        # a queue to drop results off in for the caller to use
        self.output_queue = queue.Queue()

        # a queue to display status messages from
        self.status_queue = queue.Queue()

        # a queue to display error messages from
        self.error_queue = queue.Queue()


    def sigint_handler(self, signum, frame):
        #print "Exiting gracefully...."
        self.time_to_die = True


    def sleeper(self, box):
        # sleep for the interval between queiries, then place the name of the device
        # back in the query_jobs queue for the next round
        name = threading.currentThread().getName()
        self.logger.debug('STARTED SLEEPER THREAD for {}: {} '.format(box.ip, name))
        self.status_queue.put({box: 'Waiting {} seconds until next query'.format(self.sleep_interval)})
        time.sleep(self.sleep_interval)
        """
        for i in range (0, self.sleep_interval):
            time.sleep(1)
            self.logger.debug('ZZZZZ - THREAD for {}: {} '.format(box.ip, name))
            self.status_queue.put( { box: 'sleeping...' })
        """
        self.query_jobs.put(box)


    def spinoff_sleeper(self):
        # create a new sleeper thread to sleep for the sleeping interval
        # in_q is the list of tasks that need to go into a wait state, out_q is the query queue
        name = threading.currentThread().getName()
        while not self.time_to_die:
            while self.sleeper_jobs.not_empty:
                box = self.sleeper_jobs.get()
                t = threading.Thread(name = "Sleeper" , target=self.sleeper, args=(box, ))
                t.setDaemon(True)
                t.start()
                self.sleeper_jobs.task_done()


    def process_results(self):
        # this processes the results of a query, then quues up the name of the box
        # in the sleeper_jobs queue to wait until the next polling interval
        name = threading.currentThread().getName()
        #sleep_time = random.randint(1,1)
        while not self.time_to_die:
            while self.results_jobs.not_empty:
                box, lsp_map = self.results_jobs.get()
                #time.sleep(sleep_time)
                self.sleeper_jobs.put(box)
                self.results_jobs.task_done()
                # place the lsp_map into the output queue
                # as a dictionary
                if isinstance(lsp_map, LSPMap):
                    self.output_queue.put({ box.ip: lsp_map})
                else:
                    self.output_queue.put({ box.ip: None})


    def query(self):
        # this spins off a thread that examines the self.query_jobs quue
        # it pulls an lsp_map from the box in the queue, and stores the results
        # in the results_jobs as a set ( box, lsp_map )
        name = threading.currentThread().getName()
        #sleep_time = int(name[-1]) + 1 + random.randint(1,5)
        while not self.time_to_die:
            while self.query_jobs.not_empty and not self.time_to_die:
                box = self.query_jobs.get()
                # open a connection to the device
                #self.error_queue.put({ box: 'test error' })
                if not box.connected:
                    try:
                        box.open()
                    except Exception as e:
                        lsp_map = None
                        self.error_queue.put({ box: e })
                # get an lsp map
                try:
                    if box.connected:
                        self.status_queue.put({ box: 'LSPs query' })
                        lsp_map = populate_lsp_info(box.device)
                        self.status_queue.put({ box: 'LSPs query successful' })
                    else:
                        lsp_map = None
                        self.error_queue.put({ box: 'Not connected' })
                except Exception as e:
                    lsp_map = None
                    self.error_queue.put({ box: e })
                self.query_jobs.task_done()
                # put the device and it's lsp_map in the results queue
                self.results_jobs.put((box, lsp_map))
        # shutting down
        self.status_queue.put({ box: 'Closing NETCONF connection' })



    def add_query_job(self, job):
        # Adds a job to the jobs queue
        #print 'Adding job {}'.format(job.ip)
        self.query_jobs.put(job)


    def start(self):
        #print "Starting..."
        """
        boxes = [ 'BOX_A', 'BOX_B', 'BOX_C', 'BOX_D', 'BOX_E', 'BOX_F', 'BOX_G',
                  'BOX_H', 'BOX_I', 'BOX_J', 'BOX_K', 'BOX_L', 'BOX_M', 'BOX_N',
                  'BOX_O', 'BOX_P', 'BOX_Q', 'BOX_S', 'BOX_T', 'BOX_U', 'BOX_V',
                  'BOX_X', 'BOX_Y', 'BOX_Z', 'BOX_a', 'BOX_b', 'BOX_c', 'BOX_d',
                  'BOX_e', 'BOX_f', 'BOX_g', 'BOX_h', 'BOX_i', 'BOX_j', 'BOX_k',
                  'BOX_l', 'BOX_m', 'BOX_n', 'BOX_o', 'BOX_p', 'BOX_q', 'BOX_s',
                  'BOX_t', 'BOX_u', 'BOX_v', 'BOX_w', 'BOX_x', 'BOX_y', 'BOX_z',
                  'BOX_0', 'BOX_1', 'BOX_2', 'BOX_3', 'BOX_4', 'BOX_5', 'BOX_6',
                  'BOX_7', 'BOX_8', 'BOX_9', 'BOX_!', 'BOX_@', 'BOX_#', 'BOX_$',
                ]
        """

        # a results processor thread
        t = threading.Thread(name = "Results Processor" , target=self.process_results, args=())
        t.setDaemon(True)
        t.start()
        self.logger.debug('STARTED RESULT PROCESSOR THREAD: {} '.format(str(t)))

        # a sleeper job spinoff thread
        t = threading.Thread(name = "SleeperSpinnoffer" , target=self.spinoff_sleeper, args=())
        t.setDaemon(True)
        t.start()
        self.logger.debug('STARTED SLEEPER SPINNER OFFER THREAD: {} '.format(str(t)))

        # query job threads
        for i in range(0, self.num_threads):
            #t = threading.Thread(name = "Querier-"+str(i), target=self.query, args=(self.query_jobs,self.results_jobs))
            t = threading.Thread(name = "Querier-"+str(i), target=self.query, args=())
            # this one queiries routers, so we want the process to shutdown nicely
            t.setDaemon(True)
            t.start()
            self.logger.debug('STARTED QUERIER THREAD: {} '.format(str(t)))

        # add initital jobs
        for box in self.boxes:
            self.add_query_job(box)

        # pass the status and output queues back to the starting app
        return self.status_queue, self.output_queue, self.error_queue

