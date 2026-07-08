// SPDX-License-Identifier: Apache-2.0
// 未来网络技术课程实践：P4 流特征提取与异常检测辅助模块
// 功能：线速统计流特征、SYN Flood 检测、流量镜像

#include <core.p4>
#include <v1model.p4>

// ============================================================
// Header 定义
// ============================================================
header ethernet_t {
    bit<48> dstAddr;
    bit<48> srcAddr;
    bit<16> etherType;
}

header ipv4_t {
    bit<4>  version;
    bit<4>  ihl;
    bit<8>  diffserv;
    bit<16> totalLen;
    bit<16> identification;
    bit<3>  flags;
    bit<13> fragOffset;
    bit<8>  ttl;
    bit<8>  protocol;
    bit<16> hdrChecksum;
    bit<32> srcAddr;
    bit<32> dstAddr;
}

header tcp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  dataOffset;
    bit<3>  res;
    bit<3>  ecn;
    bit<6>  ctrl;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}

header udp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<16> length;
    bit<16> checksum;
}

// ============================================================
// Metadata（内部元数据，携带流统计信息给出口处理）
// ============================================================
struct metadata {
    bit<16> flow_hash;          // 流哈希值（五元组）
    bit<1>  is_syn;             // 是否为 SYN 包
    bit<1>  is_syn_flood;       // Bloom Filter 检测到的 SYN Flood 标记
}

// ============================================================
// Header 集合
// ============================================================
struct headers {
    ethernet_t ethernet;
    ipv4_t     ipv4;
    tcp_t      tcp;
    udp_t      udp;
}

// ============================================================
// Parser（解析器）
// ============================================================
parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {

    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            0x0800: parse_ipv4;
            default: accept;
        }
    }

    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            6:  parse_tcp;
            17: parse_udp;
            default: accept;
        }
    }

    state parse_tcp {
        packet.extract(hdr.tcp);
        transition accept;
    }

    state parse_udp {
        packet.extract(hdr.udp);
        transition accept;
    }
}

// ============================================================
// Checksum 验证（透传）
// ============================================================
control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

// ============================================================
// Ingress Pipeline（入口流水线：核心特征提取逻辑）
// ============================================================
control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    // ---- 寄存器：每条流的包计数器（4096条流）----
    Register<bit<32>, bit<12>>(4096) reg_flow_pkt_count;
    // ---- 寄存器：每条流的字节计数器 ----
    Register<bit<32>, bit<12>>(4096) reg_flow_byte_count;
    // ---- 寄存器：SYN 计数器 ----
    Register<bit<32>, bit<12>>(4096) reg_syn_count;

    // ---- Bloom Filter 寄存器（SYN Flood 检测）----
    Register<bit<1>, bit<12>>(4096) bloom_reg_1;
    Register<bit<1>, bit<12>>(4096) bloom_reg_2;

    // ---- Counter：全局统计（包数+字节数）----
    Counter<bit<32>, bit<12>>(4096, CounterType.packets_and_bytes) flow_counter;

    // ---- 定义动作 ----
    action drop() {
        mark_to_drop(standard_metadata);
    }

    action set_flow_hash() {
        // 基于源IP、目的IP、协议计算流哈希
        hash(meta.flow_hash,
             HashAlgorithm.crc16,
             (bit<16>)0,
             { hdr.ipv4.srcAddr, hdr.ipv4.dstAddr,
               hdr.ipv4.protocol },
             (bit<32>)4096);
    }

    action update_flow_stats() {
        // 更新流的包计数和字节计数
        bit<32> old_pkt;
        bit<32> old_byte;
        reg_flow_pkt_count.read(old_pkt, (bit<12>)meta.flow_hash);
        reg_flow_byte_count.read(old_byte, (bit<12>)meta.flow_hash);
        reg_flow_pkt_count.write((bit<12>)meta.flow_hash, old_pkt + 1);
        reg_flow_byte_count.write((bit<12>)meta.flow_hash, old_byte + (bit<32>)hdr.ipv4.totalLen);
        // 更新全局计数器
        flow_counter.count((bit<12>)meta.flow_hash);
    }

    action detect_syn() {
        // 标记 SYN 包
        meta.is_syn = 1;
        bit<32> old_syn;
        reg_syn_count.read(old_syn, (bit<12>)meta.flow_hash);
        reg_syn_count.write((bit<12>)meta.flow_hash, old_syn + 1);

        // Bloom Filter 写入（两哈希函数）
        hash(bit<12> pos1, HashAlgorithm.crc16, (bit<16>)0xABCD,
             { hdr.ipv4.srcAddr }, (bit<32>)4096);
        hash(bit<12> pos2, HashAlgorithm.crc32, (bit<32>)0x12345678,
             { hdr.ipv4.srcAddr }, (bit<32>)4096);
        bloom_reg_1.write(pos1, 1);
        bloom_reg_2.write(pos2, 1);
    }

    action check_bloom_filter() {
        // 检查 Bloom Filter：源IP是否发送过SYN
        bit<12> pos1;
        bit<12> pos2;
        bit<1> val1;
        bit<1> val2;
        hash(pos1, HashAlgorithm.crc16, (bit<16>)0xABCD,
             { hdr.ipv4.srcAddr }, (bit<32>)4096);
        hash(pos2, HashAlgorithm.crc32, (bit<32>)0x12345678,
             { hdr.ipv4.srcAddr }, (bit<32>)4096);
        bloom_reg_1.read(val1, pos1);
        bloom_reg_2.read(val2, pos2);

        if (val1 == 1 && val2 == 1) {
            meta.is_syn_flood = 1;
        }
    }

    action forward_to_port(bit<9> port) {
        standard_metadata.egress_spec = port;
    }

    // ---- 流表：流分类（LPM on dst IP）----
    table flow_classify {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            forward_to_port;
            drop;
        }
        size = 256;
        default_action = forward_to_port(1);
    }

    // ---- 应用逻辑 ----
    apply {
        if (hdr.ipv4.isValid()) {
            // Step 1: 计算流哈希
            set_flow_hash();

            // Step 2: 更新流统计（包计数+字节计数）
            update_flow_stats();

            // Step 3: TCP SYN 检测
            if (hdr.tcp.isValid() && hdr.tcp.ctrl[1:1] == 1) {
                detect_syn();
            }

            // Step 4: Bloom Filter 检查
            check_bloom_filter();

            // Step 5: 正常转发
            flow_classify.apply();
        }
    }
}

// ============================================================
// Egress Pipeline（出口流水线：MAC重写）
// ============================================================
control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply { }
}

// ============================================================
// Checksum 计算
// ============================================================
control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply {
        update_checksum(
            hdr.ipv4.isValid(),
            { hdr.ipv4.version, hdr.ipv4.ihl, hdr.ipv4.diffserv,
              hdr.ipv4.totalLen, hdr.ipv4.identification,
              hdr.ipv4.flags, hdr.ipv4.fragOffset,
              hdr.ipv4.ttl, hdr.ipv4.protocol,
              hdr.ipv4.srcAddr, hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16);
    }
}

// ============================================================
// Deparser（逆解析器：重组包）
// ============================================================
control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.tcp);
        packet.emit(hdr.udp);
    }
}

// ============================================================
// V1Switch 主入口
// ============================================================
V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;
