#!/usr/bin/env python3
"""
Layer 3 Switch - IP-based forwarding
Extends L2 switching with IP src/dst matching.

Based on: SDN Lab Guide Section 2.1
Usage: ryu-manager app/l3switch.py
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4


class L3Switch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(L3Switch, self).__init__(*args, **kwargs)
        # MAC address to port mapping: {dpid: {mac: port}}
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch features request: install default table-miss entry"""
        datapath = ev.msg.datapath  # datapath ~= switch
        ofproto = datapath.ofproto  # OpenFlow protocol
        parser = datapath.ofproto_parser  # OpenFlow parser

        # Default rule: send to controller (table-miss)
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """Install a flow entry on the switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # OFPIT_APPLY_ACTIONS: applies the action(s) immediately
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

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """Handle incoming packets"""
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id

        # Parse Ethernet header
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # Ignore LLDP packets
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src

        # Store MAC -> port mapping
        if dpid not in self.mac_to_port:
            self.mac_to_port[dpid] = {}
        self.mac_to_port[dpid][src] = in_port

        # ===== L3 Extension: Parse IP header =====
        if eth.ethertype == ether_types.ETH_TYPE_IP:
            ip = pkt.get_protocol(ipv4.ipv4)
            srcip = ip.src
            dstip = ip.dst

            if dst in self.mac_to_port[dpid]:
                out_port = self.mac_to_port[dpid][dst]
            else:
                out_port = ofproto.OFPP_FLOOD

            # L3 match: use IP src/dst in addition to ethertype
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,
                                    ipv4_src=srcip,
                                    ipv4_dst=dstip)

            self.logger.info("L3: packet from %s to %s, in:%s out:%s",
                             srcip, dstip, in_port, out_port)
        else:
            # L2 fallback for non-IP traffic
            if dst in self.mac_to_port[dpid]:
                out_port = self.mac_to_port[dpid][dst]
            else:
                out_port = ofproto.OFPP_FLOOD

            match = parser.OFPMatch(eth_dst=dst)
            self.logger.info("L2: packet from %s to %s, in:%s out:%s",
                             src, dst, in_port, out_port)

        actions = [parser.OFPActionOutput(out_port)]

        # Install flow to avoid packet-in next time
        if out_port != ofproto.OFPP_FLOOD:
            self.add_flow(datapath, 1, match, actions)

        # Send packet out
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=msg.buffer_id,
                                  in_port=in_port,
                                  actions=actions,
                                  data=msg.data)
        datapath.send_msg(out)
