#!/usr/bin/env python3
"""
Group Tables - Traffic Mirroring
Uses OpenFlow Group Table (type=ALL) to mirror traffic to a monitoring port.

Scenario (Figure 2.6):
  - Packets from port 2 (a1) -> forward to port 3 (b1) AND port 1 (sniffer)
  - Packets from port 3 (b1) -> forward to port 2 (a1) AND port 1 (sniffer)

Group Table 50: type=ALL, buckets=[output:1, output:3]
Group Table 51: type=ALL, buckets=[output:1, output:2]

Usage: ryu-manager app/group_tables.py
       (then start mininet with group_table_topo.py)
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types


class GroupTables(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(GroupTables, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    def send_group_mod(self, datapath):
        """Create Group Tables for traffic mirroring"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Group 50: port 2 -> mirror to port 1 (sniffer) AND port 3 (b1)
        actions1 = [parser.OFPActionOutput(1)]  # Sniffer port
        actions2 = [parser.OFPActionOutput(3)]  # b1 port
        buckets = [parser.OFPBucket(actions=actions1),
                   parser.OFPBucket(actions=actions2)]
        req = parser.OFPGroupMod(datapath, ofproto.OFPGC_ADD,
                                 ofproto.OFPGT_ALL, 50, buckets)
        datapath.send_msg(req)
        self.logger.info("Group 50 (ALL): port2 -> mirror to port1 & port3")

        # Group 51: port 3 -> mirror to port 1 (sniffer) AND port 2 (a1)
        actions1 = [parser.OFPActionOutput(1)]  # Sniffer port
        actions2 = [parser.OFPActionOutput(2)]  # a1 port
        buckets = [parser.OFPBucket(actions=actions1),
                   parser.OFPBucket(actions=actions2)]
        req = parser.OFPGroupMod(datapath, ofproto.OFPGC_ADD,
                                 ofproto.OFPGT_ALL, 51, buckets)
        datapath.send_msg(req)
        self.logger.info("Group 51 (ALL): port3 -> mirror to port1 & port2")

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """Install a flow entry"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Initialize switch s1 with Group Tables and flow entries"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Default table-miss entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        # Only configure switch 1 (the mirror switch)
        if datapath.id == 1:
            # Create Group Tables
            self.send_group_mod(datapath)

            # Entry 1: Ingress port 2 -> Group 50 (mirror to 1 & 3)
            actions = [parser.OFPActionGroup(group_id=50)]
            match = parser.OFPMatch(in_port=2)
            self.add_flow(datapath, 10, match, actions)

            # Entry 2: Ingress port 3 -> Group 51 (mirror to 1 & 2)
            actions = [parser.OFPActionGroup(group_id=51)]
            match = parser.OFPMatch(in_port=3)
            self.add_flow(datapath, 10, match, actions)

            self.logger.info("Switch 1 mirror rules installed")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """Fallback L2 learning for switches without explicit rules"""
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
