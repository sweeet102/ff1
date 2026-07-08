#!/bin/bash
# SDN Lab — Docker 方案
# 所有实验在容器中运行，pcap 文件输出到 output/ 目录
# 用 Mac 原生 Wireshark 打开 pcap 查看

set -e
LAB_DIR="$(cd "$(dirname "$0")" && pwd)"

_start_container() {
    cd "$LAB_DIR" && docker compose up -d 2>/dev/null
    docker exec sdn-lab bash -c "
        ovs-vsctl --no-wait init 2>/dev/null
        ovs-vswitchd --pidfile --detach --log-file 2>/dev/null
        sleep 1
    "
}

exp1() {
    _start_container
    echo "=== Experiment 1: L2 Simple Switch ==="
    docker exec sdn-lab bash /root/lab/scripts/exp1.sh 2>&1
    echo ""
    echo "Pcap 文件在: sdn-lab/output/exp1_capture.pcap"
    echo "用 Wireshark 打开查看抓包"
}

exp2_l3() {
    _start_container
    docker exec sdn-lab bash -c "
        pkill ryu-manager 2>/dev/null; mn -c 2>/dev/null; sleep 1
        ryu-manager /root/lab/app/l3switch.py &>/root/lab/output/ryu_l3.log &
        sleep 3
        mn --controller=remote,ip=127.0.0.1:6633 --mac --switch=ovsk,protocols=OpenFlow13 --topo=single,4 --test pingall
    "
}

exp2_l4() {
    _start_container
    docker exec sdn-lab bash -c "
        pkill ryu-manager 2>/dev/null; mn -c 2>/dev/null; sleep 1
        ryu-manager /root/lab/app/l4switch.py &>/root/lab/output/ryu_l4.log &
        sleep 3
        mn --controller=remote,ip=127.0.0.1:6633 --mac --switch=ovsk,protocols=OpenFlow13 --topo=single,4 --test pingall
    "
}

exp3() {
    _start_container
    docker exec sdn-lab bash -c "
        pkill ryu-manager 2>/dev/null; mn -c 2>/dev/null; sleep 1
        ryu-manager /root/lab/app/multiple_tables.py &>/root/lab/output/ryu_multitable.log &
        sleep 3
        mn --controller=remote,ip=127.0.0.1:6633 --mac --switch=ovsk,protocols=OpenFlow13 --topo=single,4
        echo 'To test ICMP drop: h1 ping h4 (should fail)'
        echo 'To test TCP ok: h1 iperf -s & ; h4 iperf -c h1'
    "
}

exp4() {
    _start_container
    docker exec sdn-lab bash -c "
        pkill ryu-manager 2>/dev/null; mn -c 2>/dev/null; sleep 1
        ryu-manager /root/lab/app/group_tables.py &>/root/lab/output/ryu_mirror.log &
        sleep 3
        python3 /root/lab/topo/group_table_topo.py
    "
}

exp5() {
    _start_container
    docker exec sdn-lab bash -c "
        pkill ryu-manager 2>/dev/null; mn -c 2>/dev/null; sleep 1
        ryu-manager /root/lab/app/lb.py &>/root/lab/output/ryu_lb.log &
        sleep 3
        python3 /root/lab/topo/group_table_lb.py
    "
}

exp6() {
    _start_container
    docker exec sdn-lab bash -c "
        pkill ryu-manager 2>/dev/null; mn -c 2>/dev/null; sleep 1
        ryu-manager ryu.app.ofctl_rest ryu.app.simple_switch_13 &>/root/lab/output/ryu_rest.log &
        sleep 3
        mn --controller=remote,ip=127.0.0.1:6633 --mac --switch=ovsk,protocols=OpenFlow13 --topo=single,4 &
        sleep 5
        echo '=== REST API: Get switches ==='
        curl -s http://127.0.0.1:8080/stats/switches
        echo ''
        echo '=== REST API: Get switch desc ==='
        curl -s http://127.0.0.1:8080/stats/desc/1
    "
}

build()  { cd "$LAB_DIR" && docker compose build; }
start() { _start_container; echo "Ready."; }
stop()  { cd "$LAB_DIR" && docker compose down; }
shell() { _start_container; docker exec -it sdn-lab bash; }

case "${1:-help}" in
    build) build ;;
    start) start ;;
    stop)  stop ;;
    shell) shell ;;
    exp1)  exp1 ;;
    exp2-l3) exp2_l3 ;;
    exp2-l4) exp2_l4 ;;
    exp3)  exp3 ;;
    exp4)  exp4 ;;
    exp5)  exp5 ;;
    exp6)  exp6 ;;
    all)   exp1; echo; exp2_l3; echo; exp2_l4; echo; exp3; echo; exp4; echo; exp5; echo; exp6 ;;
    *)
        echo "SDN Lab — Docker 实验环境"
        echo ""
        echo "  build    构建镜像"
        echo "  start    启动容器"
        echo "  shell    进入容器"
        echo "  stop     停止容器"
        echo ""
        echo "  exp1     Section 1.3  L2 二层交换 (含 pcap 抓包)"
        echo "  exp2-l3  Section 2.1  三层交换 (IP)"
        echo "  exp2-l4  Section 2.1  四层交换 (TCP/UDP/ICMP)"
        echo "  exp3     Section 2.2  多表匹配 (ICMP 过滤)"
        echo "  exp4     Section 2.3  流量镜像 (Group Table)"
        echo "  exp5     Section 2.4  负载均衡 (SELECT Group)"
        echo "  exp6     Section 3.1  北向 REST API"
        echo ""
        echo "  all      运行全部实验"
        echo ""
        echo "抓包文件在 output/ 目录，Mac 上装 Wireshark 打开即可"
        echo "Wireshark: https://www.wireshark.org/download.html"
        ;;
esac
