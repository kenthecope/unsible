from netaddr import IPAddress
from datetime import date
from datetime import datetime
from bandwidth import Bandwidth
from Status import Status

"""
NEED TO ADD:
    - p2mp

NEED TO PROCESS RSVP SESSION:
"""

class AdminGroup(object):
    """
    This represents a single or list of admin groups
    """
    def __init__(self, exclude=False, include_all=False,
                 include_any=False, extended=False):
        self.exclude = exclude
        self.include_all = include_all
        self.include_any = include_any
        self.extended = extended
        self.groups = []

    def add(self, group):
        if isinstance(group, str):
            self.groups.append(group.strip())
        elif isinstance(group, list):
            for mygroup in group:
                self.groups.append(mygroup.strip())


    def __str__(self):
        output = ""
        if self.exclude and not self.include_all and not self.include_any:
            output += "Exclude "
        elif not self.exclude and self.include_all and not self.include_any:
            output += "Include All "
        elif not self.exclude and not self.include_all and self.include_any:
            output += "Include Any "
        else:
            # nonsense values
            return output
        if self.extended:
            output += "Extended "
        if len(self.groups) == 1:
            output += "Admin Group: "
        elif len(self.groups) > 1:
            output += "Admin Groups: "
        else:
            return ""
        for group in self.groups:
            output += '{}, '.format(group)
        # chop off last comma
        return output[:-2]



class LSPMap(object):
    """
    This is a mapping of all LSPs on a device
    """
    def __init__(self):
        self.lsps = [] # list all  LSPs
        self.mystatus = Status(name='LSPs')
        #self.status.column_headers.append('Name')
        #self.status.column_headers.append('To')
        #self.status.column_headers.append('From')
        #self.status.column_headers.append('State')

    def add(self, lsp):
        self.lsps.append(lsp)

    def __str__(self):
        # print all ingress LSPs
        output = ""
        if self.ingress_lsps:
            output = "INGRESS LSPS:\n"
            for lsp in self.lsps:
                if lsp.ingress:
                    output += str(lsp)
        return output


    @property
    def ingress_lsps(self):
        # return a list of all ingress lsps 
        lsps = []
        for lsp in self.lsps:
            if lsp.ingress:
                lsps.append(lsp)
        return lsps

    def status_header(self):
        """
        Return a Status Header
        """
        output = "LSP Status   {}\n".format(datetime.now())
        output += "="*80 + '\n'
        output += "{:33}".format("Name")
        output += "{:16}".format("To")
        output += "{:16}".format("From")
        output += "{:6}".format("State")
        output += '\n' + "_"*80 + '\n'
        return output

    def status_data(self, only_down=False):
        """
        Return a Status of each LSP
        """
        output = ""
        line = ""
        for lsp in self.ingress_lsps:
            line += "{:33}".format(lsp.name)
            line += "{:16}".format(lsp.destination_address)
            line += "{:16}".format(lsp.source_address)
            line += "{:7}".format(lsp.lsp_state)
            line += '\n'
            if only_down:
                if lsp.lsp_state == 'Dn':
                    output += line
                else:
                    line = ""
        output += line
        # chop off last '\n'
        return output.strip()

    """
    def status_data(self, only_down=False):
        # clear status
        #self.status.clear_data()
        for lsp in self.ingress_lsps:
            output = [ lsp.name, lsp.destination_address,
                      lsp.source_address, lsp.lsp_state ]
            if only_down:
                if lsp.lsp_state == 'Dn':
                    self.status
    """

    def status(self):
        # Display LSP status
        # check for a curses display
        print "STATUS"


    def csv(self):
        """
        Dump everything into a CSV output style
        """
        output = self.csv_header()
        output += self.csv_data()
        return output

    def csv_data(self):
        """
        Returns a line of csv data per lsp
        ouput is a string
        """
        csv = ""
        for lsp in self.ingress_lsps:
            #print "LSP:", lsp.name, lsp.__dict__
            for key,val in lsp.__dict__.iteritems():
                if key == 'paths':
                    for path in lsp.paths:
                        if path:
                            if path.path_active:
                                csv += '{} '.format(path.name)
                            else:
                                csv += ' '
                        else:
                            csv += ' '
                    csv += ', '
                else:
                    if isinstance(val, int):
                        if val != -1:
                            csv += '{}, '.format(val)
                        else:
                            csv += ', '
                    elif val:
                        csv += '{}, '.format(val)
                    else:
                        csv += ', '
            csv += '\n'
        return csv

    def csv_header(self):
        """
        Build a header for a CSV file from all of the
        contirbuting objects
        """
        header = ''
        for lsp in self.ingress_lsps:
            header = ""
            for key in lsp.__dict__.keys():
                header += '{}, '.format(key)
        return header


class LabelSwitchedPath(object):
    """
    This is a class to store information, query and display LSPs
    """
    def __init__(self, name=None, session_type=None, 
                 lsp_state=None, destination_address=None,
                 source_address=None, route_count=-1,
                 active_path=None,
                 lsp_type=None, egress_label_operation=None,
                 load_balance=None, 
                 encoding_type=None, switching_type=None,
                 gpid=None, mpls_lsp_upstream_label=-1,
                 bandwidth=None,
                 is_fastreroute=False,
                 is_nodeprotection=False,
                 is_linkprotection=False,
                 metric=-1,
                 revert_timer = -1,
                ):
        self.name = name
        self.session_type = session_type # Ingress/Egress/Transit
        self.lsp_state = lsp_state # Up/Dn
        self.source_address=source_address # IPAdress 
        self.destination_address = destination_address # IPaddress
        self.route_count = route_count # integer
        self.lsp_description = None # string
        self.active_path = active_path
        self.active_path_primary = False
        self.active_path_secondary = False
        self.lsp_type = lsp_type
        self.egress_label_operation = egress_label_operation
        self.load_balance = load_balance
        self.encoding_type = encoding_type
        self.switching_type = switching_type
        self.gpid = gpid
        self.mpls_lsp_upstream_label = mpls_lsp_upstream_label
        self.paths = [] # a list of all of the paths
        self.bandwidth = bandwidth
        self.is_fastreroute = is_fastreroute 
        # autobw 
        self.minimum_bandwidth = None
        self.maximum_bandwidth = None
        self.dynamic_minimum_bandwidth = None
        self.adjust_timer = None
        self.adjust_threshold = None
        self.adjust_threshold_activate_bandwidth = None
        self.maximum_average_bandwidth = None
        self.time_to_adjust = None
        self.autobw_minimum_bandwidth_adjust_interval = None
        self.autobw_minimum_bandwidth_adjust_threshold_percent = None
        self.overflow_limit = None
        self.overflow_sample_count = None
        self.underflow_limit = None
        self.underflow_sample_count = None
        self.underflow_max_avg_bandwidth = None
        self.monitor_lsp_bandwidth = False
        self.metric = metric
        self.is_linkprotection = is_linkprotection
        self.is_nodeprotection = is_nodeprotection
        self.revert_timer = revert_timer

    @property
    def php(self):
        # return boolean if penultimate hop popping is taking place
        if self.egress_label_operation == 'Penultimate hop popping':
            return True
        else:
            return False

    @property
    def lsp_up(self):
        if self.lsp_state == 'Up':
            return True
        else:
            return False

    @property
    def lsp_down(self):
        if self.lsp_state == 'Dn':
            return True
        else:
            return False


    def add_path(self, path):
        # add a path object to the LSP
        self.paths.append(path)

    def add_description(self, desc ):
        # add a description to the LSP, checks for no desctiption
        if desc == 'lsp-description':
            self.lsp_description = None # string
        else:
            self.lsp_description = str(desc)

    def add_active_path(self, path ):
        # this parses the active path to determine if the
        # if the active path is on the primary or seconcry
        # path, and if it is on a named path
        if path == '(none)':
            self.active_path_primary = False
            self.active_path_secondary = False
            self.active_path = None
        elif path == '(primary)':
            self.active_path_primary = True
            self.active_path_secondary = False
            self.active_path = None
        elif path[-10:] == ' (primary)':
            self.active_path_primary = True
            self.active_path_secondary = False
            self.active_path = path[0:-9]
        elif path[-12:] == ' (secondary)':
            self.active_path_primary = False
            self.active_path_secondary = True
            self.active_path = path[0:-11]

    def add_autobw(self, minbw=None, maxbw=None, dynminbw=None, 
                   adjust_timer = None, 
                   adjust_threshold = None,
                   atabw = None,
                   maximum_average_bandwidth = None,
                   time_to_adjust = None,
                   min_int = None,
                   min_percent = None,
                   of_limit = None,
                   of_count = None,
                   uf_limit = None,
                   uf_count = None,
                   uf_avebw = None,
                   monitor = False,
                  ):
        # parse and propery add all autobandwidht related parameters
        # to self
        if minbw:
            self.minimum_bandwidth = Bandwidth(minbw)
        if maxbw:
            self.maximum_bandwidth = Bandwidth(maxbw)
        if dynminbw:
            self.dynamic_minimum_bandwidth = Bandwidth(dynminbw)
        if adjust_timer:
            self.adjust_timer = int(adjust_timer)
        if adjust_threshold:
            self.adjust_threshold = int(adjust_threshold)
        if atabw:
            self.adjust_threshold_activate_bandwidth = Bandwidth(atabw)
        if maximum_average_bandwidth:
            self.maximum_average_bandwidth = Bandwidth(maximum_average_bandwidth)
        if time_to_adjust:
            self.time_to_adjust = int(time_to_adjust)
        if min_int:
            self.autobw_minimum_bandwidth_adjust_interval = int(min_int)
        if min_percent:
            self.autobw_minimum_bandwidth_adjust_threshold_percent = int(min_percent)
        if of_limit:
            self.overflow_limit = int(of_limit)
        if of_count:
            self.overflow_sample_count = int(of_count)
        if uf_limit:
            self.underflow_limit = int(uf_limit)
        if uf_count:
            self.underflow_sample_count = int(uf_count)
        if uf_avebw:
            self.underflow_max_avg_bandwidth = Bandwidth(uf_avebw)


    def __str__(self):
        output = "\nLSP Information\n=====================\n"
        if self.name:
            output += "Name: {}\n".format(self.name)
        else:
            output += "Name: None\n"
        if self.session_type:
            output += "Session Type: {}\n".format(self.session_type)
        else:
            output += "Session Type: N/A\n"
        output += "Fast Reroute Desired: {}\n".format(self.is_fastreroute)
        output += "Link Protection Requested: {}\n".format(self.is_linkprotection)
        output += "Node/Link Protection Requested: {}\n".format(self.is_nodeprotection)
        if self.metric > -1:
            output += 'Metirc: {}\n'.format(self.metric)
        else:
            output += 'Metirc: from IGP\n'
        if self.lsp_state:
            output += "State: {}\n".format(self.lsp_state)
        if self.source_address:
            output += "Source Address: {}\n".format(self.source_address)
        if self.destination_address:
            output += "Destination Address: {}\n".format(self.destination_address)
        if self.route_count >= 0:
            output += "Route Count: {}\n".format(self.route_count)
        if self.lsp_description:
            output += "Description: {}\n".format(self.lsp_description)
        if self.active_path_primary:
            output += "On Primary Path\n"
        if self.active_path_secondary:
            output += "On Secondary Path\n"
        if self.active_path:
            output += "Active Path: {}\n".format(self.active_path)
        if self.revert_timer > -1:
            output += "Revert Timer: {}\n".format(self.revert_timer)
        if self.lsp_type:
            output += "LSP Type: {}\n".format(self.lsp_type)
        if self.egress_label_operation:
            output += "Egress Label Op: {}\n".format(self.egress_label_operation)
        if self.load_balance:
            output += "Load Balance: {}\n".format(self.load_balance)
        if self.encoding_type:
            output += "Encoding Type: {}\n".format(self.encoding_type)
        if self.switching_type:
            output += "Switching Type: {}\n".format(self.switching_type)
        if self.gpid:
            output += "GPID: {}\n".format(self.gpid)
        if self.mpls_lsp_upstream_label >= 0:
            output += "Upstream Label: {}\n".format(self.mpls_lsp_upstream_label)
        if self.minimum_bandwidth:
            output += "    Auto-BW Min Bandwidth: {}\n".format(self.minimum_bandwidth)
        if self.maximum_bandwidth:
            output += "    Auto-BW Max Bandwidth: {}\n".format(self.maximum_bandwidth)
        if self.adjust_timer:
            output += "    Auto-BW Adjustment Timer: {} seconds\n".format(self.adjust_timer)
        if self.adjust_threshold:
            output += "    Auto-BW Adjustment Threshold: {}%\n".format(self.adjust_threshold)
        if self.adjust_threshold_activate_bandwidth:
            output += "    Auto-BW Adjustment Min BW Activation: "
            output += "{}\n".format(self.adjust_threshold_activate_bandwidth)
        if self.maximum_average_bandwidth:
            output += "    Auto-BW Max Average BW: {}\n".format(self.maximum_average_bandwidth)
        if self.time_to_adjust:
            output += "    Auto-BW Time to Adjust: {} seconds\n".format(self.time_to_adjust)
        if self.autobw_minimum_bandwidth_adjust_interval:
            output += "    Auto-BW Min BW Adjustment Interval: "
            output += "{} seconds\n".format(self.autobw_minimum_bandwidth_adjust_interval)
        if self.autobw_minimum_bandwidth_adjust_threshold_percent:
            output += "    Auto-BW Min BW Adjustment Percent: "
            output += "{}%\n".format(self.autobw_minimum_bandwidth_adjust_threshold_percent)
        if self.overflow_limit:
            output += "    Auto-BW Overflow limit: {}%\n".format(self.overflow_limit)
        if self.underflow_limit:
            output += "    Auto-BW Underflow limit: {}%\n".format(self.underflow_limit)
        if self.overflow_sample_count:
            output += "    Auto-BW Overflow Count: {} samples\n".format(self.overflow_sample_count)
        if self.underflow_sample_count:
            output += "    Auto-BW Underflow Count: {} samples\n".format(self.underflow_sample_count)
        if self.underflow_max_avg_bandwidth:
            output += "    Auto-BW Underflow Max Ave BW: "
            output += "{}\n".format(self.underflow_max_avg_bandwidth)
        output += "    Auto-BW Monitor Only: {}\n".format(self.monitor_lsp_bandwidth)
        # outpt path info
        for path in self.paths:
            output += str(path)

        return output

class LSPHistoryEvent(object):
    """
    This is a LSP status from show mpls lsp extensive
    """
    def __init__(self, sqn=-1, time=None, log=None, route=None):
        self.sqn = int(sqn)
        if time:
            self.time = time
        else:
            self.time = None
        self.log = log
        if route == 'route':
            self.route = None
        else:
            self.route = route

    def __str__(self):
        output = ""
        output += "{:03}: {} : {}".format(self.sqn, self.time, self.log)
        if self.route:
            output += ": {}".format(self.route)
        return output


class EROAddress(object):
    """
    This is an Explicit Route Address
    """
    def __init__(self, hop_address, strict_hop=True):
        # strict_hop is a boolean S:True, L:False
        # address is an IPAddress
        if isinstance(strict_hop, bool):
            self.strict_hop = strict_hop # 
        elif isinstance(strict_hop, str):
            if strict_hop == 'L':
                self.strict_hop  = False
            else:
                self.strict_hop  = True
        if isinstance(hop_address, str):
            try:
                self.address = IPAddress(hop_address)
            except:
                self.address = None
        elif isinstance(hop_address, IPAddress):
            self.address = hop_address
        elif not hop_address:
            self.address = None

    def __str__(self):
        if self.strict_hop and self.address:
            return "S {}".format(str(self.address))
        elif not self.strict_hop and self.address:
            return "L {}".format(str(self.address))
        else:
            return "{}   {}".format(self.strict_hop, self.address)


class LSPPathPriority(object):
    """
    This is a priority for an RSVP signaled LSP
    """
    def __init__(self, setup=-1, hold=-1):
        self.setup = setup # integer
        self.hold = hold # integer

    def __str__(self):
        if self.setup >= 0 and self.hold >= 0:
            output = "Setup: {}   Hold: {}".format(self.setup, self.hold)
        else:
            output = "Setup: NS   Hold: NS"
        return output

class LSPPath(object):
    """
    This is a LSP path object and it's attributes
    """
    def __init__(self, title=None, name=None,
                 path_active=False, path_state=None,
                 optimize_timer=-1, smart_optimize_timer=-1,
                 cspf_status=None, 
                 no_decrement_ttl=False,
                 path_no_recordroute=False
                ):
        self.title = title
        self.name = name
        self.path_active = path_active
        self.priority = None
        self.optimize_timer = optimize_timer
        self.smart_optimize_timer = smart_optimize_timer
        self.cspf_status = []
        self.cspf_metric = -1
        self.recomputation_timer = -1
        self.ero_computed = True
        self.ero = [] # list of ERO objects
        self.history = {}  # dict of history events, the sqn is used as the key, holds history object
        self.bandwidth = None
        self.cos = None
        self.admin_groups = []
        self.path_no_recordroute = path_no_recordroute
        self.no_decrement_ttl = no_decrement_ttl

    def __repr__(self):
        return str(self.name)

    def add_bandwidth(self, bandwidth):
        # add bandwidth as a Bandwidth object
        self.bandwidth = Bandwidth(bandwidth)

    def add_cos(self, cos):
        # add cos to the path
        if cos:
            try:
                cos_val = int(cos)
                if cos_val >=0 and cos_val <=7:
                    self.cos = cos_val
            except:
                self.cos = None


    def add_history(self, sqn=-1, time=None, log=None, route=None):
        # create a history object
        # convert sqn to int
        if int(sqn):
            if int(sqn) > 0 and int(sqn) < 1000:
                hist = LSPHistoryEvent( int(sqn), time, log, route)
                self.history[int(sqn)] = hist

    def add_ero(self, ero_addresses, ero_route_types):
        # add ero item, can be a pair of lists or strings
        # the lists must be equal length
        # normalize to lists
        addrs = []
        rt_types = []
        if isinstance(ero_addresses, list):
            if isinstance (ero_route_types, list):
                if len(ero_addresses) != len(ero_route_types):
                    return False
                else:
                    addrs = ero_addresses
                    rt_types = ero_route_types
            else:
                    return False
        elif isinstance(ero_addresses, str) and isinstance(ero_route_types, str):
            addrs.append(ero_addresses)
            rt_types.append(ero_route_types)
        for i in range(0, len(addrs)):
            if rt_types[i] == 'L':
                mytype = False
            else:
                mytype = True
            myaddr = IPAddress(addrs[i])
            if myaddr:
                self.ero.append(EROAddress(myaddr, mytype))

    def add_admin_group(self, group):
        self.admin_groups.append(group)


    def add_priority(self, setup, hold):
        priority = LSPPathPriority()
        try:
            mysetup = int(setup)
            myhold = int(hold)
        except:
            pass
        if mysetup >= 0 and mysetup <= 7:
            priority.setup = mysetup
        if myhold >= 0 and myhold <= 7:
            priority.hold = myhold
        if priority.setup == -1 or priority.hold == -1:
            # if there are any problems return an empty
            self.priority = LSPPathPriority()
            return False
        else:
            self.priority = priority
            return True

    def add_cspf_status(self, cspf_status):
        """
        Add CSPF status, the input can be a string or a list
        """
        # normalize cspf_status to a list
        status = []
        if isinstance(cspf_status, str):
            status.append(cspf_status)
        elif isinstance(cspf_status, str):
            status = cspf_status
        self.cspf_status = status
        for item in status:
            if 'No computed ERO.' in item:
                self.ero_computed = False
            elif 'Will be enqueued for recomputation in ' in item:
                # figure out how long until recomp
                timer = item[38:].split('second(s).')[0]
                try:
                    self.recomputation_timer = int(timer)
                except:
                    self.recomputation_timer = -1
            elif 'Computed ERO (S [L] denotes strict [loose] hops): ' in item:
                # try to find CSPF metric
                if '(CSPF metric: ' in item:
                    cspf_metric = item.split('(CSPF metric: ')[-1]
                    cspf_metric = cspf_metric.split(')')[0]
                    try:
                        self.cspf_metric = int(cspf_metric)
                    except:
                        self.cspf_metric = -1

    def __str__(self):
        output = "   PATH ATTRIBUTES\n"
        if self.title:
            output += "    Title: {}\n".format(self.title)
        if self.name:
            output += "    Name: {}\n".format(self.name)
        if self.bandwidth:
            output += "    Bandwidth: {}\n".format(self.bandwidth)
        if self.path_active:
            output += "    This path is active.\n"
        else:
            output += "    This is NOT an active path.\n"
        if self.priority:
            output += "    {}\n".format(str(self.priority))
        if self.cos:
            output += "    COS: {}\n".format(self.cos)
        else:
            output += "    COS: Not Specified\n"
        if self.no_decrement_ttl:
            output += "    TTL: Not decremented.\n"
        else:
            output += "    TTL: Will be decremented.\n"
        if self.path_no_recordroute:
            output += "    RRO: Not requested.\n"
        else:
            output += "    RRO: Will be requested.\n"
        if self.optimize_timer >= 0:
            output += "    Optimize Timer: {}\n".format(self.optimize_timer)
        if self.smart_optimize_timer >= 0:
            output += "    Smart Optimize Timer: {}\n".format(self.smart_optimize_timer)
        for status in self.cspf_status:
            output += "    CSPF Status: {}\n".format(status)
        if self.cspf_metric > 0:
            output += "    CSPF Metric: {}\n".format(self.cspf_metric)
        if self.recomputation_timer >= 0:
            output += "    Path Recomputation in: {}\n".format(self.recomputation_timer)
        if self.ero_computed:
            output += "    ERO Computed.\n"
        else:
            output += "    NO ERO Computed!\n"
        for ero in self.ero:
            output += "    ERO Hop: {}\n".format(str(ero))
        if self.received_rro:
            output += "    RRO: {}\n".format(self.received_rro)
        if self.admin_groups:
            for group in self.admin_groups:
                output += "    {}\n".format(group)
        if self.history:
            # print out history items in sequence
            output += "    History:\n"
            for sqn in range(0,1000):
                if sqn in self.history.keys():
                    output += "           {}\n".format(self.history[int(sqn)])
        return output
