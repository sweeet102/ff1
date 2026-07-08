#!/usr/bin/env python3
# ================================================
# Simple Switch 13 — 二层交换机 (实验指导书 Section 1.2)
# 自学习二层交换机：学习 MAC → Port 映射，下发流表
# ================================================

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types


class SimpleSwitch13(app_manager.RyuApp):
    """二层自学习交换机控制器"""
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        # mac_to_port: {dpid: {mac_address: port_number}}
        # 记录每台交换机上学到的 MAC 地址与端口的映射关系
        self.mac_to_port = {}

    # ============================================================
    #  事件1: EventOFPSwitchFeatures — 交换机特征请求/响应
    #  触发时机: CONFIG_DISPATCHER（配置协商阶段）
    #  对应图1.1 步骤D：Feature Request/Reply
    #  在交换机连接建立后(E)，立即下发 table-miss 缺省流表
    # ============================================================
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        交换机特性事件处理函数
        datapath = 对控制器来说就是一台交换机，由 dpid 唯一标识
        ofproto = OpenFlow 协议定义
        parser  = OpenFlow 消息解析器
        """
        datapath = ev.msg.datapath                  # datapath ≈ switch
        ofproto = datapath.ofproto                  # OpenFlow 协议
        parser = datapath.ofproto_parser            # 解析器

        # 下发 table-miss 流表项：匹配所有包，动作为发送到控制器
        # OFPCML_NO_BUFFER: 无缓冲，直接发送完整包到控制器
        # priority=0: 最低优先级，仅在没有其他匹配时生效
        match = parser.OFPMatch()                   # 空匹配 = 匹配所有包
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER,                 # 发送到控制器
            ofproto.OFPCML_NO_BUFFER                 # 不缓冲
        )]
        self.add_flow(datapath, 0, match, actions)   # priority=0

    # ============================================================
    #  add_flow() — 下发流表到交换机
    #  参数:
    #    datapath   : 目标交换机
    #    priority   : 优先级 (0=CONFIG 阶段, 1=MAIN 阶段)
    #    match      : 匹配条件 (OFMatch)
    #    actions    : 执行动作 (如 output:port)
    #    buffer_id  : 交换机缓冲区 ID
    # ============================================================
    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # OFPIT_APPLY_ACTIONS: 立即应用动作
        inst = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]

        if buffer_id:
            mod = parser.OFPFlowMod(
                datapath=datapath, buffer_id=buffer_id,
                priority=priority, match=match, instructions=inst
            )
        else:
            mod = parser.OFPFlowMod(
                datapath=datapath, priority=priority,
                match=match, instructions=inst
            )
        datapath.send_msg(mod)  # 发送 FlowMod 消息到交换机

    # ============================================================
    #  事件2: EventOFPPacketIn — 数据包到达控制器
    #  触发时机: MAIN_DISPATCHER（主运行阶段）
    #
    #  两种包会触发 Packet-In：
    #    (1) 交换机流表中无匹配条目，无法处理的包
    #    (2) 流表明确要求上传到控制器的包
    #
    #  核心逻辑：MAC 自学习 + 流表下发
    #    ① 记录 src_mac → in_port 映射
    #    ② 查询 dst_mac → out_port
    #    ③ 如果找到 → 下发精确流表 + 转发
    #    ④ 如果找不到 → 泛洪 (FLOOD)
    # ============================================================
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']              # 包进入交换机的端口
        dpid = datapath.id                          # 交换机 ID

        # 解析以太网帧头
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # 忽略 LLDP 链路发现报文
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst   # 目的 MAC 地址
        src = eth.src   # 源 MAC 地址

        # ---- MAC 自学习 ----
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port       # 记录 src_mac → in_port

        self.logger.info("packet in  %s %s %s %s", dpid, src, dst, in_port)

        # ---- 查表转发 ----
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]   # 已知端口，直接转发
        else:
            out_port = ofproto.OFPP_FLOOD            # 未知端口，泛洪

        actions = [parser.OFPActionOutput(out_port)]

        # ---- 下发流表（避免下次同样包再触发 Packet-In）----
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(
                in_port=in_port, eth_dst=dst, eth_src=src
            )
            # 如果有 buffer_id，可复用交换机缓存的包
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)

        # ---- 发送 Packet-Out 包到交换机 ----
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data  # 没缓存就重新发

        out = parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id,
            in_port=in_port, actions=actions, data=data
        )
        datapath.send_msg(out)
