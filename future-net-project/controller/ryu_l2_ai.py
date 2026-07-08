#!/usr/bin/env python3
"""
Ryu SDN 控制器：L2 交换机 + 实时端口统计 + AI 异常检测
"""
import pickle, time, os, numpy as np
from collections import defaultdict
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4
from ryu.lib import hub

MODEL_DIR = '/root/future-net-project/ai/models'

class L2SwitchWithAI(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(L2SwitchWithAI, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.prev_stats = {}
        self.blocked = set()
        self.history = []

        # Load AI model
        with open(os.path.join(MODEL_DIR, 'rf_model.pkl'), 'rb') as f:
            self.model = pickle.load(f)
        with open(os.path.join(MODEL_DIR, 'scaler.pkl'), 'rb') as f:
            self.scaler = pickle.load(f)
        with open(os.path.join(MODEL_DIR, 'model_meta.pkl'), 'rb') as f:
            self.meta = pickle.load(f)
        self.classes = self.meta['class_names']
        print(f"[AI] Model loaded: RF {self.meta['rf_accuracy']*100:.0f}%")
        print(f"[SDN] L2 Switch + AI Detector ready")
        hub.spawn(self._stats_loop)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        self.datapaths[dp.id] = dp
        self.mac_to_port.setdefault(dp.id, {})
        # Table-miss: send to controller
        match = dp.ofproto_parser.OFPMatch()
        actions = [dp.ofproto_parser.OFPActionOutput(dp.ofproto.OFPP_CONTROLLER, dp.ofproto.OFPCML_NO_BUFFER)]
        self._add_flow(dp, 0, match, actions)
        print(f"[SDN] Switch {dp.id} connected")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # Learn src MAC
        self.mac_to_port[dp.id][eth.src] = in_port

        # L2 forwarding
        dst = eth.dst
        if dst in self.mac_to_port[dp.id]:
            out_port = self.mac_to_port[dp.id][dst]
        else:
            out_port = ofp.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # Install flow for future packets
        if out_port != ofp.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self._add_flow(dp, 1, match, actions)

        out = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                   in_port=in_port, actions=actions, data=msg.data)
        dp.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        dp = ev.msg.datapath
        dpid = dp.id
        now = time.time()

        for stat in ev.msg.body:
            port = stat.port_no
            if port > 100:  # skip special ports
                continue

            prev = self.prev_stats.get((dpid, port), {})
            prev_pkts = prev.get('rx', stat.rx_packets)
            prev_bytes = prev.get('rx_bytes', stat.rx_bytes)
            prev_time = prev.get('time', now)

            rx_rate = stat.rx_packets - prev_pkts
            byte_rate = stat.rx_bytes - prev_bytes
            dt = max(now - prev_time, 0.1)

            self.prev_stats[(dpid, port)] = {
                'rx': stat.rx_packets, 'rx_bytes': stat.rx_bytes, 'time': now
            }

            # High packet rate → check with AI
            pps = rx_rate / dt
            if pps > 200:
                features = np.array([[
                    rx_rate, byte_rate, dt * 1000,
                    pps, byte_rate / dt,
                    64, rx_rate * 0.9, 0,
                    0.85, 0.1, 1, 10, 1.0 / max(pps, 1) * 1000,
                ]])
                scaled = self.scaler.transform(features)
                pred = self.model.predict(scaled)[0]
                conf = self.model.predict_proba(scaled)[0].max()
                cls = self.classes[int(pred)]

                if cls != 'normal' and conf > 0.85:
                    print(f"\n[!] DETECTED {cls} on port {port} (rate={pps:.0f}pps, conf={conf*100:.0f}%)")
                    # Block the port by dropping all from it
                    match = dp.ofproto_parser.OFPMatch(in_port=port)
                    self._add_flow(dp, 100, match, [], hard_timeout=60)
                    self.blocked.add((dpid, port))
                    self.history.append(f"{time.strftime('%H:%M:%S')} {cls} port={port} conf={conf*100:.0f}%")

    def _stats_loop(self):
        while True:
            for dp in list(self.datapaths.values()):
                req = dp.ofproto_parser.OFPPortStatsRequest(dp, 0, dp.ofproto.OFPP_ANY)
                dp.send_msg(req)
            hub.sleep(2)

    def _add_flow(self, dp, prio, match, acts, hard_timeout=None):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, acts)]
        mod = parser.OFPFlowMod(datapath=dp, priority=prio, match=match,
                                 instructions=inst, hard_timeout=hard_timeout)
        dp.send_msg(mod)
