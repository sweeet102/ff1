#!/usr/bin/env python3
"""
Ryu SDN 控制器：L2 转发 + 端口统计采集 + 调用 AI API 分类
AI 模型通过独立微服务运行 (ai_server.py, 端口 5001)
"""
import time
import json
import os
from collections import defaultdict, deque

import requests
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet
from ryu.lib import hub

AI_API = 'http://127.0.0.1:5001/predict'
RESULTS_FILE = '/tmp/qos_results.json'


class L2AIQoS(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(L2AIQoS, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.prev_stats = {}
        self.port_history = defaultdict(lambda: deque(maxlen=5))
        self.port_classes = {}
        self.class_log = []
        self.total_requests = 0

        # 检查 AI 服务是否可用
        try:
            r = requests.get('http://127.0.0.1:5001/health', timeout=2)
            if r.status_code == 200:
                self.logger.info("AI 推理服务已连接 (端口 5001)")
                self.ai_available = True
            else:
                self.logger.warning("AI 服务异常: %s", r.status_code)
                self.ai_available = False
        except Exception:
            self.logger.warning("AI 推理服务未启动，请先运行 ai_server.py")
            self.ai_available = False

        self.logger.info("L2 + AI QoS 控制器启动 (AI API 模式)")
        hub.spawn(self._stats_loop)
        hub.spawn(self._results_writer)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        dpid = dp.id
        self.datapaths[dpid] = dp
        self.mac_to_port.setdefault(dpid, {})
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        dp.send_msg(parser.OFPFlowMod(datapath=dp, priority=0, match=match, instructions=inst))
        self.logger.info("交换机 %016x 已连接", dpid)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        self.mac_to_port[dp.id][eth.src] = in_port
        out_port = self.mac_to_port[dp.id].get(eth.dst, ofp.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofp.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=eth.dst)
            inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
            dp.send_msg(parser.OFPFlowMod(datapath=dp, priority=1, match=match, instructions=inst))

        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        dp.send_msg(parser.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id,
            in_port=in_port, actions=actions, data=data
        ))

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        dp = ev.msg.datapath
        dpid = dp.id
        now = time.time()

        for stat in ev.msg.body:
            port = stat.port_no
            if port > 100:
                continue

            prev = self.prev_stats.get((dpid, port), {})
            prev_rx = prev.get('rx', stat.rx_packets)
            prev_rx_bytes = prev.get('rx_bytes', stat.rx_bytes)
            prev_tx = prev.get('tx', stat.tx_packets)
            prev_tx_bytes = prev.get('tx_bytes', stat.tx_bytes)
            prev_time = prev.get('time', now)

            dt = max(now - prev_time, 0.1)
            rx_pkts = stat.rx_packets - prev_rx
            rx_bytes = stat.rx_bytes - prev_rx_bytes
            tx_pkts = stat.tx_packets - prev_tx
            tx_bytes = stat.tx_bytes - prev_tx_bytes

            self.prev_stats[(dpid, port)] = {
                'rx': stat.rx_packets, 'rx_bytes': stat.rx_bytes,
                'tx': stat.tx_packets, 'tx_bytes': stat.tx_bytes,
                'time': now
            }

            if prev_time == now or rx_pkts < 10 or not self.ai_available:
                continue

            # 构建 10 维特征向量
            pkt_rate = rx_pkts / dt
            byte_rate = rx_bytes / dt
            avg_pkt_size = rx_bytes / max(rx_pkts, 1)
            tx_pkt_rate = tx_pkts / dt
            rx_tx_ratio = rx_pkts / max(tx_pkts, 1)

            features = [
                rx_pkts, rx_bytes, tx_pkts, tx_bytes,
                pkt_rate, byte_rate, avg_pkt_size,
                tx_pkt_rate, dt * 1000, min(rx_tx_ratio, 100)
            ]

            # 调用 AI API 推理
            try:
                r = requests.post(AI_API, json={'features': features}, timeout=0.5)
                if r.status_code == 200:
                    result = r.json()
                    cls = result['class']
                    conf = result['confidence']
                    self.total_requests += 1
                else:
                    continue
            except Exception:
                continue

            # 滑动窗口投票去抖
            self.port_history[(dpid, port)].append(cls)
            votes = list(self.port_history[(dpid, port)])
            stable_cls = max(set(votes), key=votes.count) if votes else cls

            old_cls = self.port_classes.get((dpid, port))
            if old_cls != stable_cls and conf > 0.7:
                self.port_classes[(dpid, port)] = stable_cls
                ts = time.strftime('%H:%M:%S')
                icon = {'video': '📹', 'web': '🌐', 'download': '📥'}.get(stable_cls, '?')
                qos = {'video': '⬆ 高优先', 'web': '→ 中优先', 'download': '⬇ 限速'}.get(stable_cls, '?')
                self.logger.info("%s 端口%d %s %s %s (%.0f%%, API请求#%d)",
                                 ts, port, icon, stable_cls, qos, conf * 100, self.total_requests)
                self.class_log.append({
                    'time': ts, 'port': port, 'class': stable_cls,
                    'confidence': conf, 'pkt_rate': round(pkt_rate, 1),
                    'avg_pkt_size': round(avg_pkt_size, 1),
                    'rx_pkts': int(rx_pkts), 'rx_bytes': int(rx_bytes),
                    'tx_pkts': int(tx_pkts), 'tx_bytes': int(tx_bytes),
                    'tx_pkt_rate': round(tx_pkt_rate, 1),
                    'interval_ms': round(dt * 1000, 1),
                    'rx_tx_ratio': round(min(rx_tx_ratio, 100), 1),
                    'api_request': self.total_requests,
                })

    def _stats_loop(self):
        while True:
            for dp in list(self.datapaths.values()):
                req = dp.ofproto_parser.OFPPortStatsRequest(dp, 0, dp.ofproto.OFPP_ANY)
                dp.send_msg(req)
            hub.sleep(2)

    def _results_writer(self):
        while True:
            hub.sleep(3)
            try:
                with open(RESULTS_FILE, 'w') as f:
                    json.dump({
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'port_classes': {str(k[1]): v for k, v in self.port_classes.items()},
                        'log': self.class_log[-20:],
                        'api_requests': self.total_requests,
                        'model': {'type': 'Random Forest (via API)', 'classes': ['video', 'web', 'download']},
                    }, f, indent=2)
            except Exception:
                pass
