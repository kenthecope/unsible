from mpls_tables import MPLSLSPTable
from LSP import LabelSwitchedPath
from LSP import LSPMap
from LSP import LSPPath
from LSP import AdminGroup
from netaddr import IPAddress
from bandwidth import Bandwidth

def populate_lsp_info(device):
    """
    This function populates LSP objects and returns
    a list of them from the device above
    """
    #print "DEBUG: populate_lsp_info(device)", __name__
    #print "     : populating from", device

    # get the lsps from the device
    try:
        lsps = MPLSLSPTable(device).get()
    except Exception as e:
        raise

    # make an LSPmap 
    lsp_map = LSPMap()

    # add lsps to the map
    for lsp in lsps:
        #print "LSP:", lsp
        #print "   :", lsp.session_type
        #print "   :", lsp.count
        #print "   :", lsp.rsvp_session
        #print "   : LSPs "
        for session in lsp.rsvp_session:
            if lsp.name == 'Ingress':
                for mylsp in session.mpls_lsp:
                    LSP = LabelSwitchedPath()
                    LSP.name = mylsp.name
                    LSP.lsp_state = mylsp.lsp_state
                    LSP.session_type = 'Ingress'
                    LSP.ingress = True
                    try:
                        LSP.source_address = IPAddress(mylsp.source_address)
                    except:
                        pass
                    try:
                        LSP.destination_address = IPAddress(mylsp.destination_address)
                    except:
                        pass
                    try:
                        LSP.route_count = int(mylsp.route_count)
                    except:
                        pass 
                    LSP.metric = mylsp.metric
                    LSP.is_linkprotection = mylsp.is_linkprotection
                    LSP.is_nodeprotection = mylsp.is_nodeprotection
                    LSP.add_description(mylsp.lsp_description)
                    LSP.add_active_path(mylsp.active_path)
                    LSP.lsp_type = mylsp.lsp_type
                    LSP.egress_label_operation = mylsp.egress_label_operation
                    LSP.load_balance = mylsp.load_balance
                    LSP.encoding_type = mylsp.encoding_type
                    LSP.switching_type = mylsp.switching_type
                    LSP.is_fastreroute=mylsp.is_fastreroute
                    LSP.gpid = mylsp.gpid
                    LSP.revert_timer = mylsp.revert_timer
                    # autobandwidth related info
                    LSP.add_autobw(minbw = mylsp.minimum_bandwidth,
                                    maxbw = mylsp.maximum_bandwidth,
                                    dynminbw = mylsp.dynamic_minimum_bandwidth,
                                    adjust_timer = mylsp.adjust_timer,
                                    adjust_threshold = mylsp.adjust_threshold,
                                    atabw = mylsp.adjust_threshold_activate_bandwidth,
                                    maximum_average_bandwidth = mylsp.maximum_average_bandwidth,
                                    time_to_adjust = mylsp.time_to_adjust,
                                    min_int = mylsp.autobw_minimum_bandwidth_adjust_interval,
                                    min_percent = mylsp.autobw_minimum_bandwidth_adjust_threshold_percent,
                                    of_limit = mylsp.overflow_limit,
                                    of_count = mylsp.overflow_sample_count,
                                    uf_limit = mylsp.underflow_limit,
                                    uf_count = mylsp.underflow_sample_count,
                                    uf_avebw = mylsp.underflow_max_avg_bandwidth,
                                    monitor = mylsp.monitor_lsp_bandwidth
                                   )
                    try:
                        LSP.mpls_lsp_upstream_label = int(mylsp.mpls_lsp_upstream_label)
                    except:
                        pass
                    # process the path info for the lsp
                    for mypath in mylsp.mpls_lsp_path:
                         path = LSPPath()
                         path.title = mypath.title
                         path.name = mypath.name
                         path.path_active = mypath.path_active
                         path.add_priority(mypath.setup_priority, mypath.hold_priority)
                         path.add_bandwidth(mypath.bandwidth)
                         path.add_cos(mypath.cos)
                         path.path_no_recordroute = mypath.path_no_recordroute
                         path.no_decrement_ttl = mypath.no_decrement_ttl
                         # process all admin groups
                         if mypath.admin_groups_exclude:
                             AG = AdminGroup(exclude=True)
                             AG.add(mypath.admin_groups_exclude)
                             path.add_admin_group(AG)
                         if mypath.admin_groups_include_all:
                             AG = AdminGroup(include_all=True)
                             AG.add(mypath.admin_groups_include_all)
                             path.add_admin_group(AG)
                         if mypath.admin_groups_include_any:
                             AG = AdminGroup(include_any=True)
                             AG.add(mypath.admin_groups_include_any)
                             path.add_admin_group(AG)
                         if mypath.admin_groups_extended_exclude:
                             AG = AdminGroup(exclude=True, extended=True)
                             AG.add(mypath.admin_groups_extended_exclude)
                             path.add_admin_group(AG)
                         if mypath.admin_groups_extended_include_all:
                             AG = AdminGroup(include_all=True, extended=True)
                             AG.add(mypath.admin_groups_extended_include_all)
                             path.add_admin_group(AG)
                         if mypath.admin_groups_extended_include_any:
                             AG = AdminGroup(include_any=True, extended=True)
                             AG.add(mypath.admin_groups_extended_include_any)
                             path.add_admin_group(AG)
                         try:
                             path.optimize_timer = int(mypath.optimize_timer)
                         except:
                             pass
                         try:
                             path.smart_optimize_timer = int(mypath.smart_optimize_timer)
                         except:
                             pass
                         path.add_cspf_status(mypath.cspf_status)
                         path.add_ero(mypath.explicit_route_address, mypath.explicit_route_type)
                         path.received_rro = mypath.received_rro
                         # history
                         for item in mypath.path_history:
                             path.add_history(item.sequence_number, item.time, item.log,
                                              item.route)
                         LSP.add_path(path)



                    lsp_map.add(LSP)
        # display LSP info

    return lsp_map



