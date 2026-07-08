#!/usr/bin/env python3
"""
Load Balancing with Group Tables (SELECT type)
Demonstrates weighted traffic distribution across multiple paths.

Topology (Figure 2.8):
          +-- s2 --+
         /          \
    h1--s1          s4--h2
         \          /
          +-- s3 --+

- s1/s4 use Group Table 50 (SELECT) to distribute traffic between s2 and s3
- Weight: s2=30%, s3=70%
- s2/s3 do simple L2 forwarding

Usage: ryu-manager app/lb.py
       (then start mininet with group_table_lb.py)
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types


class LoadBalancer(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # Weight configuration (percentage)
    LB_WEIGHT1 = 30  # s2 path
    LB_WEIGHT2 = 70  # s3 path

    def __init__(self, *args, **kwargs):
        super(LoadBalancer, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    def send_group_mod(self, datapath):
        """Create Group Table with SELECT type for load balancing"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Bucket 1: output to port 1 (s2) with weight 30
        actions1 = [parser.OFPActionOutput(1)]
        # Bucket 2: output to port 2 (s3) with weight 70
        actions2 = [parser.OFPActionOutput(2)]

        watch_port = ofproto.OFPP_ANY
        watch_group = ofproto.OFPG_ANY

        buckets = [parser.OFPBucket(LB_WEIGHT1, watch_port, watch_group,
                                    actions=actions1),
                   parser.OFPBucket(LB_WEIGHT2, watch_port, watch_group,
                                    actions=actions2)]

        req = parser.OFPGroupMod(datapath, ofproto.OFPGC_ADD,
                                 ofproto.OFPGT_SELECT, 50, buckets)
        datapath.send_msg(req)
        self.logger.info("Group Table 50 (SELECT): s2=%d%%, s3=%d%%",
                         self.LB_WEIGHT1, self.LB_WEIGHT2)

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
        """Initialize all switches with their roles"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Default table-miss entry for all switches
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        # === Switch s1 (dpid=1): Edge switch, LB entry point ===
        if datapath.id == 1:
            self.send_group_mod(datapath)

            # Traffic from port 3 (h1) -> Group 50 (LB to s2 or s3)
            actions = [parser.OFPActionGroup(group_id=50)]
            match = parser.OFPMatch(in_port=3)
            self.add_flow(datapath, 10, match, actions)

            # Return traffic from port 1 or 2 -> forward to port 3 (h1)
            actions = [parser.OFPActionOutput(3)]
            match = parser.OFPMatch(in_port=1)
            self.add_flow(datapath, 10, match, actions)
            match = parser.OFPMatch(in_port=2)
            self.add_flow(datapath, 10, match, actions)

            self.logger.info("Switch 1 (edge) configured")

        # === Switch s4 (dpid=4): Edge switch, LB return entry point ===
        elif datapath.id == 4:
            self.send_group_mod(datapath)

            # Traffic from port 3 (h2) -> Group 50 (LB to s2 or s3)
            actions = [parser.OFPActionGroup(group_id=50)]
            match = parser.OFPMatch(in_port=3)
            self.add_flow(datapath, 10, match, actions)

            # Return traffic from port 1 or 2 -> forward to port 3 (h2)
            actions = [parser.OFPActionOutput(3)]
            match = parser.OFPMatch(in_port=1)
            self.add_flow(datapath, 10, match, actions)
            match = parser.OFPMatch(in_port=2)
            self.add_flow(datapath, 10, match, actions)

            self.logger.info("Switch 4 (edge) configured")

        # === Switch s2 (dpid=2): Transit switch ===
        elif datapath.id == 2:
            # Port 1 -> Port 2 (forward)
            actions = [parser.OFPActionOutput(2)]
            match = parser.OFPMatch(in_port=1)
            self.add_flow(datapath, 10, match, actions)
            # Port 2 -> Port 1 (reverse)
            actions = [parser.OFPActionOutput(1)]
            match = parser.OFPMatch(in_port=2)
            self.add_flow(datapath, 10, match, actions)
            self.logger.info("Switch 2 (transit) configured")

        # === Switch s3 (dpid=3): Transit switch ===
        elif datapath.id == 3:
            # Port 1 -> Port 2 (forward)
            actions = [parser.OFPActionOutput(2)]
            match = parser.OFPMatch(in_port=1)
            self.add_flow(datapath, 10, match, actions)
            # Port 2 -> Port 1 (reverse)
            actions = [parser.OFPActionOutput(1)]
            match = parser.OFPMatch(in_port=2)
            self.add_flow(datapath, 10, match, actions)
            self.logger.info("Switch 3 (transit) configured")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """Fallback L2 learning (should not be heavily used after flow install)"""
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
