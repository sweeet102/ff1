#!/usr/bin/env python3
"""
未来网络技术课程实践：SDN 智能异常检测与防御控制器
基于 Ryu + OpenFlow + AI 模型

功能：
  1. 转发 + PacketIn 收集流量统计
  2. 调用 AI 模型（Random Forest）在线推理
  3. 检测到异常后自动下发 OpenFlow 规则阻断攻击源
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp
from ryu.lib import hub
import json
import time
import os
import pickle
import numpy as np
from collections import defaultdict

# 配置
STATS_INTERVAL = 2
ANOMALY_THRESHOLD = 0.85
BLOCK_TIMEOUT = 60

MODEL_DIR = '/root/future-net-project/ai/models'


def load_ai_model():
    try:
        with open(os.path.join(MODEL_DIR, 'rf_model.pkl'), 'rb') as f:
            model = pickle.load(f)
        with open(os.path.join(MODEL_DIR, 'scaler.pkl'), 'rb') as f:
            scaler = pickle.load(f)
        with open(os.path.join(MODEL_DIR, 'model_meta.pkl'), 'rb') as f:
            meta = pickle.load(f)
        print(f"[AI] Model loaded OK. Accuracy={meta['rf_accuracy']*100:.1f}%")
        return model, scaler, meta
    except Exception as e:
        print(f"[AI] Model load FAILED: {e}")
        return None, None, None


class AnomalyDetector(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(AnomalyDetector, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.flow_stats = defaultdict(list)
        self.port_stats = defaultdict(dict)
        self.blocked_ips = set()
        self.detection_history = []
        self.pkt_counter = defaultdict(int)
        self.prev_port = defaultdict(dict)

        self.model, self.scaler, self.meta = load_ai_model()
        self.class_names = (self.meta['class_names'] if self.meta
                            else ['normal', 'syn_flood', 'udp_flood', 'port_scan'])

        self.monitor_thread = hub.spawn(self._monitor_loop)
        print("[SDN] Anomaly Detector ready")
        print(f"[SDN] Stats interval={STATS_INTERVAL}s, threshold={ANOMALY_THRESHOLD}")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.datapaths[datapath.id] = datapath

        # Default: send to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self._add_flow(datapath, 0, match, actions)
        print(f"[SDN] Switch {datapath.id} connected")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto

        pkt = packet.Packet(msg.data)
        ip_pkt = pkt.get_protocol(ipv4.ipv4)

        if ip_pkt:
            src_ip = ip_pkt.src
            dst_ip = ip_pkt.dst
            proto = ip_pkt.proto

            key = f"{dpid}:{src_ip}"
            self.pkt_counter[key] += 1
            cnt = self.pkt_counter[key]

            # Check if blocked
            if src_ip in self.blocked_ips:
                return  # drop silently

            # AI inference every 20 packets
            if cnt % 20 == 0 and self.model is not None:
                tcp_pkt = pkt.get_protocol(tcp.tcp)
                features = np.array([[
                    min(cnt, 500),
                    cnt * 64,
                    2000,
                    cnt / 2.0,
                    cnt * 64 / 16.0,
                    64 if tcp_pkt else 800,
                    1 if (tcp_pkt and tcp_pkt.has_flags(tcp.TCP_SYN) and not tcp_pkt.has_flags(tcp.TCP_ACK)) else 0,
                    0,
                    0.7 if cnt > 100 else 0.3,
                    0.1 if cnt > 100 else 0.5,
                    1,
                    20 if cnt > 100 else 150,
                    1.0 if cnt > 100 else 30.0,
                ]])

                scaled = self.scaler.transform(features)
                pred = self.model.predict(scaled)[0]
                proba = self.model.predict_proba(scaled)[0]
                pred_class = self.class_names[int(pred)]
                confidence = float(max(proba))

                if pred_class != 'normal' and confidence >= ANOMALY_THRESHOLD:
                    print(f"\n{'='*50}")
                    print(f"[!] ATTACK DETECTED!")
                    print(f"    Type: {pred_class}")
                    print(f"    Source: {src_ip} -> {dst_ip}")
                    print(f"    Confidence: {confidence*100:.1f}%")
                    print(f"    Packets: {cnt}")
                    print(f"{'='*50}\n")

                    self.detection_history.append({
                        'time': time.strftime('%H:%M:%S'),
                        'src': src_ip,
                        'dst': dst_ip,
                        'type': pred_class,
                        'conf': confidence,
                    })

                    # Block attacker
                    self._block_ip(datapath, src_ip)

        # Forward (flood)
        out_port = ofproto.OFPP_FLOOD
        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id,
            in_port=msg.match['in_port'], actions=actions, data=msg.data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id

        for stat in body:
            port_no = stat.port_no
            if port_no > 0xffffff00:
                continue
            prev = self.prev_port[dpid].get(port_no, {})
            rx_rate = stat.rx_packets - prev.get('rx_packets', stat.rx_packets)
            self.prev_port[dpid][port_no] = {
                'rx_packets': stat.rx_packets,
                'tx_packets': stat.tx_packets,
            }

            if rx_rate > 500 and self.model is not None:
                features = np.array([[
                    rx_rate, rx_rate * 64, STATS_INTERVAL * 1000,
                    rx_rate / STATS_INTERVAL, rx_rate * 64 / 8,
                    64, rx_rate // 3, 0, 0.8, 0.1, 1, 10, 0.5,
                ]])

                scaled = self.scaler.transform(features)
                pred = self.model.predict(scaled)[0]
                proba = self.model.predict_proba(scaled)[0]
                pred_class = self.class_names[int(pred)]
                confidence = float(max(proba))

                if pred_class != 'normal' and confidence >= ANOMALY_THRESHOLD:
                    print(f"\n[!] PORT ALERT: {pred_class} on dpid={dpid} port={port_no} "
                          f"rate={rx_rate}pps conf={confidence*100:.1f}%")

    def _monitor_loop(self):
        while True:
            for dpid, dp in list(self.datapaths.items()):
                parser = dp.ofproto_parser
                req = parser.OFPPortStatsRequest(dp, 0, dp.ofproto.OFPP_ANY)
                dp.send_msg(req)
            hub.sleep(STATS_INTERVAL)

    def _block_ip(self, datapath, src_ip):
        if src_ip in self.blocked_ips:
            return

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src_ip)
        actions = []

        mod = parser.OFPFlowMod(
            datapath=datapath, priority=100, match=match,
            instructions=[parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)],
            hard_timeout=BLOCK_TIMEOUT,
        )
        datapath.send_msg(mod)

        self.blocked_ips.add(src_ip)
        print(f"[SDN] >>> BLOCKED {src_ip} (timeout={BLOCK_TIMEOUT}s)")

    def _add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                 match=match, instructions=inst)
        datapath.send_msg(mod)
