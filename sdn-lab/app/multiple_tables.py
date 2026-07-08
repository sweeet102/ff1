#!/usr/bin/env python3
"""
Multi-Table Matching - OpenFlow Pipeline with multiple flow tables
Demonstrates OpenFlow table pipeline: Table 0 -> Table 5 (filter) -> Table 10 (forward)

Pipeline:
  Table 0  (default): Match all -> Goto Table 5
  Table 5  (filter):  Match ICMP -> DROP; Others -> Goto Table 10
  Table 10 (forward): L2 MAC learning + forwarding

Based on: SDN Lab Guide Section 2.2
Usage: ryu-manager app/multiple_tables.py
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import in_proto

# Table IDs
FILTER_TABLE = 5
FORWARD_TABLE = 10


class MultipleTables(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MultipleTables, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Initialize switch with multi-table pipeline when features are negotiated"""
        datapath = ev.msg.datapath
        self.add_default_table(datapath)
        self.add_filter_table(datapath)
        self.apply_filter_table_rules(datapath)
        self.add_forward_table_miss(datapath)

    def add_default_table(self, datapath):
        """Table 0: Match all traffic, goto Table 5"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()  # Match all
        inst = [parser.OFPInstructionGotoTable(FILTER_TABLE)]
        mod = parser.OFPFlowMod(datapath=datapath,
                                table_id=0,
                                priority=0,
                                match=match,
                                instructions=inst)
        datapath.send_msg(mod)
        self.logger.info("Table 0 installed: ALL -> Goto Table %d", FILTER_TABLE)

    def add_filter_table(self, datapath):
        """Table 5: Default rule -> Goto Table 10 (forwarding table)"""
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()  # Match all non-ICMP
        inst = [parser.OFPInstructionGotoTable(FORWARD_TABLE)]
        mod = parser.OFPFlowMod(datapath=datapath,
                                table_id=FILTER_TABLE,
                                priority=1,
                                match=match,
                                instructions=inst)
        datapath.send_msg(mod)
        self.logger.info("Table %d default: ALL -> Goto Table %d",
                         FILTER_TABLE, FORWARD_TABLE)

    def apply_filter_table_rules(self, datapath):
        """Table 5: Match ICMP -> DROP (no action = implicit drop)"""
        parser = datapath.ofproto_parser

        # Match ICMP packets — no actions specified = DROP
        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,
                                ip_proto=in_proto.IPPROTO_ICMP)
        mod = parser.OFPFlowMod(datapath=datapath,
                                table_id=FILTER_TABLE,
                                priority=10000,
                                match=match,
                                instructions=[])  # Empty instructions = DROP
        datapath.send_msg(mod)
        self.logger.info("Table %d ICMP filter: ICMP -> DROP", FILTER_TABLE)

    def add_forward_table_miss(self, datapath):
        """Table 10: Default table-miss -> CONTROLLER (needed for MAC learning)"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath,
                                table_id=FORWARD_TABLE,
                                priority=0,
                                match=match,
                                instructions=inst)
        datapath.send_msg(mod)
        self.logger.info("Table %d table-miss: ALL -> CONTROLLER", FORWARD_TABLE)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """Install a flow entry in Table 10 (forwarding table)"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, table_id=FORWARD_TABLE,
                                    buffer_id=buffer_id, priority=priority,
                                    match=match, instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, table_id=FORWARD_TABLE,
                                    priority=priority, match=match,
                                    instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """L2 MAC learning in Table 10"""
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src

        if dpid not in self.mac_to_port:
            self.mac_to_port[dpid] = {}
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        self.logger.info("Table %d: packet %s -> %s, in:%s out:%s",
                         FORWARD_TABLE, src, dst, in_port, out_port)

        actions = [parser.OFPActionOutput(out_port)]
        match = parser.OFPMatch(eth_dst=dst)

        if out_port != ofproto.OFPP_FLOOD:
            self.add_flow(datapath, 1, match, actions)

        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=msg.buffer_id,
                                  in_port=in_port,
                                  actions=actions,
                                  data=msg.data)
        datapath.send_msg(out)
