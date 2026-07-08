#!/usr/bin/env python3
"""
未来网络技术课程实践：Mininet 网络拓扑 + 流量生成 + 攻击模拟 + 性能评估
运行环境：Docker 容器内 (p4-lab)
用法: python3 net_topo.py [normal|attack|full]
"""

import sys
import os
import time
import threading
import json
import subprocess
from datetime import datetime

# 将项目根目录添加到 path
PROJECT_ROOT = '/root/future-net-project'
sys.path.insert(0, PROJECT_ROOT)

try:
    from mininet.net import Mininet
    from mininet.node import RemoteController, OVSSwitch, Host
    from mininet.cli import CLI
    from mininet.log import setLogLevel, info, error
    from mininet.link import TCLink
except ImportError:
    print("[WARN] Mininet not found, some functions unavailable")

# ============================================================
# 配置
# ============================================================
TOPOLOGY_CONFIG = {
    'controller_ip': '127.0.0.1',
    'controller_port': 6653,
    'switch_dpid': '0000000000000001',
}

TRAFFIC_CONFIG = {
    'normal_duration': 60,       # 正常流量持续时间(秒)
    'attack_duration': 30,       # 攻击流量持续时间(秒)
    'iperf_duration': 20,        # iperf 测试时长
    'ping_count': 10,
}

HOSTS = {
    'h1': {'ip': '10.0.0.1', 'mac': '00:00:00:00:00:01', 'role': 'normal'},
    'h2': {'ip': '10.0.0.2', 'mac': '00:00:00:00:00:02', 'role': 'normal'},
    'h3': {'ip': '10.0.0.3', 'mac': '00:00:00:00:00:03', 'role': 'attacker'},
    'h4': {'ip': '10.0.0.4', 'mac': '00:00:00:00:00:04', 'role': 'server'},
}

# ============================================================
# 性能结果记录
# ============================================================
class PerformanceLogger:
    """记录和导出性能测试结果"""

    def __init__(self):
        self.results = {
            'start_time': None,
            'end_time': None,
            'phases': [],
            'ping_results': [],
            'iperf_results': [],
            'attack_events': [],
            'detection_events': [],
            'summary': {},
        }
        self._lock = threading.Lock()

    def log_phase(self, name, status='start'):
        entry = {'phase': name, 'status': status, 'timestamp': time.time()}
        with self._lock:
            self.results['phases'].append(entry)
        print(f"  [{status.upper()}] {name}")

    def log_ping(self, src, dst, loss_rate, avg_rtt):
        entry = {
            'timestamp': time.time(),
            'src': src, 'dst': dst,
            'loss_rate': loss_rate,
            'avg_rtt_ms': avg_rtt,
        }
        with self._lock:
            self.results['ping_results'].append(entry)

    def log_iperf(self, src, dst, bandwidth_mbps):
        entry = {
            'timestamp': time.time(),
            'src': src, 'dst': dst,
            'bandwidth_mbps': bandwidth_mbps,
        }
        with self._lock:
            self.results['iperf_results'].append(entry)

    def log_attack(self, attack_type, src, dst, details=''):
        entry = {
            'timestamp': time.time(),
            'type': attack_type,
            'src': src,
            'dst': dst,
            'details': details,
        }
        with self._lock:
            self.results['attack_events'].append(entry)

    def log_detection(self, result):
        with self._lock:
            self.results['detection_events'].append({
                'timestamp': time.time(),
                **result
            })

    def export(self, filepath):
        with self._lock:
            self.results['end_time'] = time.time()
            if self.results['start_time']:
                self.results['duration'] = self.results['end_time'] - self.results['start_time']

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n[结果] 性能数据已导出到 {filepath}")

logger = PerformanceLogger()


# ============================================================
# 网络拓扑构建
# ============================================================
def create_topology():
    """创建 Mininet 拓扑：3个客户端 + 1个服务器 + 1个 OVS 交换机"""
    info('*** 创建网络拓扑\n')

    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        host=Host,
        link=TCLink,
        autoSetMacs=True,
    )

    # 添加控制器
    c0 = net.addController(
        'c0',
        controller=RemoteController,
        ip=TOPOLOGY_CONFIG['controller_ip'],
        port=TOPOLOGY_CONFIG['controller_port'],
    )

    # 添加交换机
    s1 = net.addSwitch('s1', dpid=TOPOLOGY_CONFIG['switch_dpid'])

    # 添加主机
    h1 = net.addHost('h1', ip=f"{HOSTS['h1']['ip']}/24", mac=HOSTS['h1']['mac'])
    h2 = net.addHost('h2', ip=f"{HOSTS['h2']['ip']}/24", mac=HOSTS['h2']['mac'])
    h3 = net.addHost('h3', ip=f"{HOSTS['h3']['ip']}/24", mac=HOSTS['h3']['mac'])
    h4 = net.addHost('h4', ip=f"{HOSTS['h4']['ip']}/24", mac=HOSTS['h4']['mac'])

    # 连接：所有主机连到 s1
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s1)
    net.addLink(h4, s1)

    info('*** 启动网络\n')
    net.build()
    c0.start()
    s1.start([c0])

    # 等待控制器连接
    info('*** 等待 SDN 控制器连接...\n')
    time.sleep(3)

    return net, h1, h2, h3, h4, s1


# ============================================================
# 流量生成
# ============================================================
def start_http_server(host, port=80):
    """在主机上启动简单的 HTTP 服务器（用 netcat 模拟）"""
    host.cmd(f'pkill -f "nc -l {port}" 2>/dev/null; true')
    host.cmd(f'while true; do echo -e "HTTP/1.1 200 OK\\r\\n\\r\\nOK" | nc -l {port} -w 1; done &')
    print(f"  HTTP 服务启动: {host.name}:{port}")

def start_iperf_server(host, port=5001):
    """启动 iperf 服务端"""
    host.cmd('pkill -f "iperf -s" 2>/dev/null; true')
    time.sleep(0.5)
    host.cmd(f'iperf -s -p {port} &')
    print(f"  iperf 服务启动: {host.name}:{port}")

def generate_normal_traffic(client, server, duration=60):
    """生成正常流量：ping + HTTP请求 + iperf"""
    server_ip = server.IP()
    client_name = client.name
    print(f"\n  [{client_name}] 生成正常流量 -> {server.name} ({server_ip})")

    # iperf TCP 流量（后台）
    client.cmd(f'timeout {duration} iperf -c {server_ip} -t {duration} -p 5001 &')

    # 周期性 ping
    def ping_loop():
        for i in range(duration // 2):
            if i % 10 == 0:
                result = client.cmd(f'ping -c 5 -W 1 {server_ip} 2>&1')
                # 解析丢包率
                if 'packet loss' in result:
                    for line in result.split('\n'):
                        if 'packet loss' in line:
                            loss_str = line.split('%')[0].split()[-1]
                            try:
                                loss = float(loss_str)
                                logger.log_ping(client_name, server.name, loss, 0)
                            except:
                                pass
            time.sleep(2)

    threading.Thread(target=ping_loop, daemon=True).start()

    # HTTP 请求（模拟 Web 流量）
    def http_loop():
        for i in range(duration // 5):
            client.cmd(f'echo "GET / HTTP/1.1" | timeout 2 nc {server_ip} 80 2>/dev/null || true')
            time.sleep(5)

    threading.Thread(target=http_loop, daemon=True).start()

def launch_syn_flood(attacker, target, duration=30):
    """SYN Flood 攻击（使用 hping3）"""
    target_ip = target.IP()
    print(f"\n  [!] {attacker.name} 发起 SYN Flood -> {target.name} ({target_ip})")
    print(f"  攻击持续时间: {duration}s")

    logger.log_attack('syn_flood', attacker.name, target.name,
                      f'SYN flood to {target_ip}, duration={duration}s')

    # hping3 SYN flood: --flood 极速模式, -S SYN标志, -p 目的端口
    attacker.cmd(f'timeout {duration} hping3 -S --flood -p 80 {target_ip} 2>&1 &')
    time.sleep(0.5)

def launch_udp_flood(attacker, target, duration=30):
    """UDP Flood 攻击"""
    target_ip = target.IP()
    print(f"\n  [!] {attacker.name} 发起 UDP Flood -> {target.name} ({target_ip})")

    logger.log_attack('udp_flood', attacker.name, target.name,
                      f'UDP flood to {target_ip}, duration={duration}s')

    attacker.cmd(f'timeout {duration} hping3 --udp --flood -p 53 {target_ip} 2>&1 &')
    time.sleep(0.5)


# ============================================================
# 性能评估
# ============================================================
def measure_connectivity(net, label):
    """测量连通性（pingall）"""
    print(f"\n  --- 连通性测试: {label} ---")
    result = net.pingAll(timeout='1')
    print(f"  丢包率: {result}%")
    return result

def measure_throughput(client, server, duration=10):
    """测量吞吐量（iperf）"""
    server_ip = server.IP()
    print(f"\n  --- 吞吐量测试: {client.name} -> {server.name} ---")

    # 确保服务端运行
    server.cmd('pkill -f "iperf -s" 2>/dev/null; true')
    time.sleep(0.3)
    server.cmd(f'iperf -s -p 5555 &')
    time.sleep(0.5)

    result = client.cmd(f'iperf -c {server_ip} -t {duration} -p 5555 2>&1')

    # 解析带宽
    bandwidth = 0
    for line in result.split('\n'):
        if 'Mbits/sec' in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == 'Mbits/sec' and i > 0:
                    try:
                        bandwidth = float(parts[i-1])
                    except:
                        pass

    print(f"  带宽: {bandwidth} Mbps")
    logger.log_iperf(client.name, server.name, bandwidth)
    return bandwidth

def measure_latency(client, server, count=10):
    """测量时延"""
    server_ip = server.IP()
    result = client.cmd(f'ping -c {count} -W 1 {server_ip} 2>&1')

    avg_rtt = 0
    loss = 0
    for line in result.split('\n'):
        if 'rtt min/avg/max' in line:
            try:
                avg_rtt = float(line.split('/')[4])
            except:
                pass
        if 'packet loss' in line:
            try:
                loss = float(line.split('%')[0].split()[-1])
            except:
                pass

    print(f"  时延: {avg_rtt}ms, 丢包率: {loss}%")
    return avg_rtt, loss


# ============================================================
# 主流程
# ============================================================
def run_full_experiment():
    """运行完整实验：正常流量 → 攻击 → 检测 → 阻断 → 性能对比"""
    print("=" * 70)
    print("  未来网络技术课程实践")
    print("  SDN + P4 + AI 智能网络流量异常检测与防御系统")
    print("=" * 70)

    logger.results['start_time'] = time.time()

    # Phase 1: 创建拓扑
    print("\n[Phase 1] 创建网络拓扑...")
    logger.log_phase('create_topology')
    net, h1, h2, h3, h4, s1 = create_topology()

    print(f"\n  拓扑信息:")
    print(f"    h1 (正常用户): {h1.IP()}")
    print(f"    h2 (正常用户): {h2.IP()}")
    print(f"    h3 (攻击者):   {h3.IP()}")
    print(f"    h4 (服务器):   {h4.IP()}")
    print(f"    s1 (OVS交换机, SDN控制)")
    print(f"    Ryu 控制器: {TOPOLOGY_CONFIG['controller_ip']}:{TOPOLOGY_CONFIG['controller_port']}")

    # Phase 2: 初始连通性测试
    print("\n[Phase 2] 初始连通性测试...")
    logger.log_phase('initial_connectivity')
    measure_connectivity(net, '初始状态')

    # Phase 3: 正常流量
    print("\n[Phase 3] 生成正常流量...")
    logger.log_phase('normal_traffic', 'start')

    # 启动服务
    start_http_server(h4, 80)
    start_iperf_server(h4, 5001)
    time.sleep(1)

    # h1, h2 生成正常流量
    t1 = threading.Thread(target=generate_normal_traffic, args=(h1, h4, 30), daemon=True)
    t2 = threading.Thread(target=generate_normal_traffic, args=(h2, h4, 30), daemon=True)
    t1.start()
    t2.start()

    # 测量正常状态下的性能
    time.sleep(5)
    print("\n  --- 正常状态性能基准 ---")
    bw_before = measure_throughput(h1, h4, 5)
    lat_before, loss_before = measure_latency(h1, h4, 5)

    # Phase 4: 攻击流量
    print("\n[Phase 4] 发起攻击...")
    logger.log_phase('attack_traffic', 'start')

    # h3 发起 SYN flood
    launch_syn_flood(h3, h4, duration=30)

    time.sleep(3)

    # h3 发起 UDP flood
    launch_udp_flood(h3, h4, duration=20)

    # Phase 5: 攻击期间性能测量
    print("\n[Phase 5] 攻击期间性能测量...")
    logger.log_phase('attack_measurement')

    time.sleep(5)
    print("\n  --- 攻击状态性能 ---")
    bw_during = measure_throughput(h1, h4, 5)
    lat_during, loss_during = measure_latency(h1, h4, 5)

    measure_connectivity(net, '攻击期间')

    # Phase 6: 等待 SDN 检测和阻断
    print("\n[Phase 6] 等待 SDN 控制器检测并阻断攻击...")
    logger.log_phase('detection_wait')
    time.sleep(10)

    # Phase 7: 阻断后性能测量
    print("\n[Phase 7] 阻断后性能测量...")
    logger.log_phase('after_block')

    time.sleep(5)
    print("\n  --- 阻断后状态性能 ---")
    bw_after = measure_throughput(h1, h4, 5)
    lat_after, loss_after = measure_latency(h1, h4, 5)

    measure_connectivity(net, '阻断后')

    # Phase 8: 结果汇总
    print("\n[Phase 8] 性能评估汇总...")
    logger.log_phase('summary')

    print("\n  " + "=" * 60)
    print("  性能评估结果")
    print("  " + "=" * 60)
    print(f"  {'指标':<20} {'正常状态':<15} {'攻击期间':<15} {'阻断后':<15}")
    print(f"  {'-'*60}")
    print(f"  {'吞吐量 (Mbps)':<20} {bw_before:<15.2f} {bw_during:<15.2f} {bw_after:<15.2f}")
    print(f"  {'时延 (ms)':<20} {lat_before:<15.2f} {lat_during:<15.2f} {lat_after:<15.2f}")
    print(f"  {'丢包率 (%)':<20} {loss_before:<15.1f} {loss_during:<15.1f} {loss_after:<15.1f}")

    # 计算改善
    if bw_during > 0:
        improvement = (bw_after - bw_during) / bw_during * 100
        print(f"\n  吞吐量恢复: +{improvement:.1f}%")
    if lat_during > 0:
        reduction = (lat_during - lat_after) / lat_during * 100
        print(f"  时延降低: {reduction:.1f}%")

    logger.results['summary'] = {
        'throughput': {'before': bw_before, 'during': bw_during, 'after': bw_after},
        'latency': {'before': lat_before, 'during': lat_during, 'after': lat_after},
        'loss_rate': {'before': loss_before, 'during': loss_during, 'after': loss_after},
    }

    # 导出结果
    results_file = os.path.join(PROJECT_ROOT, 'results', 'performance_results.json')
    logger.export(results_file)

    # Phase 9: 进入 CLI（可选）
    print("\n" + "=" * 70)
    print("  实验完成！进入 Mininet CLI")
    print("  输入 'exit' 退出")
    print("=" * 70)

    try:
        CLI(net)
    except:
        pass

    net.stop()
    print("\n实验结束。")

def run_normal_only():
    """仅运行正常流量（用于生成训练数据）"""
    net, h1, h2, h3, h4, s1 = create_topology()

    start_http_server(h4, 80)
    start_iperf_server(h4, 5001)
    time.sleep(1)

    print("\n生成正常流量 60 秒...")
    generate_normal_traffic(h1, h4, 60)
    generate_normal_traffic(h2, h4, 60)
    time.sleep(60)

    measure_connectivity(net, '最终')
    net.stop()

def run_attack_only():
    """仅运行攻击流量（用于测试检测效果）"""
    net, h1, h2, h3, h4, s1 = create_topology()

    time.sleep(3)

    # 先正常 ping
    measure_connectivity(net, '攻击前')

    # SYN flood
    launch_syn_flood(h3, h4, 20)

    time.sleep(5)
    measure_connectivity(net, '攻击中')

    time.sleep(15)
    measure_connectivity(net, '攻击后')

    net.stop()


# ============================================================
# 入口
# ============================================================
if __name__ == '__main__':
    setLogLevel('info')

    mode = sys.argv[1] if len(sys.argv) > 1 else 'full'

    if mode == 'normal':
        run_normal_only()
    elif mode == 'attack':
        run_attack_only()
    else:
        run_full_experiment()
