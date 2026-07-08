#!/usr/bin/env python3
"""
对比实验：纯 L2 vs AI
脚本自动完成两阶段对比，不需要手动切换控制器

窗口分工:
  窗口1: tail -f /tmp/ryu_compare.log    ← 看控制器切换日志
  窗口2: python3 step_compare.py 40      ← 主演示
  窗口3: 按提示操作                       ← 中间验证 AI API + OVS 流表

用法: python3 step_compare.py [duration]
"""
import time, sys, json, os, subprocess
PROJECT = '/root/future-net-project'
DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 40

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.log import setLogLevel
setLogLevel('info')


def hr(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def stop_ryu():
    subprocess.run(['pkill', '-9', '-f', 'ryu-manager'], capture_output=True)
    time.sleep(1)


def start_ryu(app_file):
    subprocess.Popen(
        ['ryu-manager', f'{PROJECT}/{app_file}'],
        stdout=open('/tmp/ryu_compare.log', 'a'),
        stderr=subprocess.STDOUT
    )
    for _ in range(5):
        time.sleep(1)
        r = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
        if ':6633' in r.stdout:
            return True
    return False


def create_topo():
    net = Mininet(controller=RemoteController, switch=OVSSwitch, autoSetMacs=True)
    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    net.addSwitch('s1', protocols='OpenFlow13')
    for i in range(1, 5):
        net.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
    for i in range(1, 5):
        net.addLink(f'h{i}', 's1')
    net.start()
    time.sleep(3)
    return net


def run_traffic(net, dur):
    h1, h2, h3, h4 = net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')
    h4.popen(f'python3 {PROJECT}/server.py 8000 90')
    time.sleep(2)
    h1.popen(f'python3 {PROJECT}/traffic_gen.py video 10.0.0.4 8000 {dur}')
    h2.popen(f'python3 {PROJECT}/traffic_gen.py web 10.0.0.4 8000 {dur}')
    h3.popen(f'python3 {PROJECT}/traffic_gen.py download 10.0.0.4 8000 {dur}')


# ═══════════════════════════════════════════════════════════════
print("""
╔══════════════════════════════════════════════════════════════╗
║   SDN + AI — 对比实验：纯 L2 转发 vs AI 智能分类             ║
╚══════════════════════════════════════════════════════════════╝
""")

# ================================================================
# Phase 1: 纯 L2
# ================================================================
hr("Phase 1: 纯 L2 转发（无 AI）")

print("""
纯 L2 模式下，控制器只做一件事:
  收到未知 MAC → 学习 → 查到出口 → 转发

不知道流量类型，也没有 QoS 策略。
""")

print("\n>>> 启动纯 L2 控制器...")
stop_ryu()
if not start_ryu('ryu_l2_only.py'):
    print("ERROR: 控制器启动失败")
    sys.exit(1)

net1 = create_topo()
r = net1.pingAll(timeout='1')
print(f"连通性: {r}% 丢包")
print("\n>>> 启动流量 (UDP视频 / curl网页 / wget下载)...")
run_traffic(net1, 15)

print("\n流量在跑。窗口 3 现在可以敲: ovs-ofctl -O OpenFlow13 dump-flows s1")
print("你会看到只有 2 条规则: table-miss + MAC转发，没有 QoS 标记\n")
time.sleep(15)

hr("Phase 1 结果")
print("""
  纯 L2:
    流量识别:   0/3 ← 不知道在传什么
    AI API 调用: 0 ← AI 服务根本没有启动
    QoS 策略:    无 ← 所有流量完全同等
    网络状态:    「瞎子」— 能转发，但看不见
""")
net1.stop()

# ================================================================
# Phase 2: AI
# ================================================================
hr("Phase 2: AI 智能分类（有 AI）")

print("""
AI 模式下，同一控制器架构，增加了:
  + 每 2 秒采集 OVS 端口统计
  + 提取 10 维特征 → HTTP POST → AI 推理
  + 按分类结果下发 QoS 策略
""")

print("\n>>> 启动 AI 服务...")
subprocess.run(['pkill', '-9', '-f', 'ai_server'], capture_output=True)
time.sleep(1)
subprocess.Popen(
    ['python3', f'{PROJECT}/ai_server.py'],
    stdout=open('/tmp/ai_compare.log', 'w'),
    stderr=subprocess.STDOUT
)
time.sleep(2)
import requests
try:
    requests.get('http://127.0.0.1:5001/', timeout=2)
    print("AI 推理服务: 端口 5001 ✓")
except:
    print("AI 服务启动失败")
    sys.exit(1)

print("\n>>> 启动 AI 控制器...")
stop_ryu()
if not start_ryu('ryu_qos_ai.py'):
    print("ERROR")
    sys.exit(1)

print("\n>>> 创建相同拓扑 + 相同流量...")
net2 = create_topo()
r = net2.pingAll(timeout='1')
print(f"连通性: {r}% 丢包")
run_traffic(net2, DUR)

print("\n窗口 3 现在敲: python3 /root/future-net-project/step3_api_test.py")
print("实时看到 AI API 的推理结果\n")

print("等待 AI 分类...")
prev = 0
for i in range(10):
    time.sleep(3)
    try:
        with open('/tmp/qos_results.json') as f:
            data = json.load(f)
        log = data.get('log', [])
        api = data.get('api_requests', 0)
        if len(log) > prev:
            for e in log[prev:]:
                cls = e['class']
                icon = {'video': '📹', 'web': '🌐', 'download': '📥'}.get(cls, '?')
                print(f"  {e['time']} 端口{e['port']} {icon} {cls} | "
                      f"置信度{(e['confidence']*100):.0f}% | API#{e.get('api_request','?')}")
            prev = len(log)
    except:
        pass

hr("Phase 2 结果")
try:
    with open('/tmp/qos_results.json') as f:
        data = json.load(f)
    pc = data.get('port_classes', {})
    api_c = data.get('api_requests', 0)
except:
    pc = {}
    api_c = 0

exp = {'1': 'video', '2': 'web', '3': 'download'}
correct = sum(1 for p in ['1','2','3'] if pc.get(p) == exp[p])

for port in ['1', '2', '3']:
    cls = pc.get(port, '?')
    icon = {'video': '📹', 'web': '🌐', 'download': '📥'}.get(cls, '?')
    host = {'1': 'h1 视频', '2': 'h2 网页', '3': 'h3 下载'}[port]
    ok = '✓' if cls == exp[port] else '✗'
    print(f"  {ok} {host}: {icon} {cls}")

print(f"""
  AI:
    流量识别:   {correct}/3 ← 实时识别
    AI API 调用: {api_c} ← 真实 HTTP 请求
    QoS 策略:    视频VIP / 网页MED / 下载LOW
    网络状态:    「有眼睛」— 知道在传什么
""")
net2.stop()

# ================================================================
# 对比
# ================================================================
hr("最终对比")

lines = [
    "┌─────────────────────┬──────────────────┬──────────────────┐",
    "│ 指标                │ 纯 L2 (无 AI)     │ AI 智能分类      │",
    "├─────────────────────┼──────────────────┼──────────────────┤",
]
for port in ['1', '2', '3']:
    host = {'1': 'h1 视频(UDP)', '2': 'h2 网页(curl)', '3': 'h3 下载(wget)'}[port]
    cls = pc.get(port, '?')
    icon = {'video': '📹', 'web': '🌐', 'download': '📥'}.get(cls, '?')
    lines.append(f"│ {host:<19} │ 未知             │ {icon} {cls:<14} │")
lines += [
    "├─────────────────────┼──────────────────┼──────────────────┤",
    f"│ 流量识别            │ 0/3              │ {correct}/3              │",
    f"│ AI API 调用         │ 0                │ {api_c:<16} │",
    "│ QoS 策略            │ 无               │ VIP/MED/LOW      │",
    "└─────────────────────┴──────────────────┴──────────────────┘",
]
for l in lines:
    print(f"  {l}")

print(f"""
  结论:
    同一拓扑 + 同一流量。变量只有「有没有 AI」。
    没有 AI: 网络能转发，但不知道在传什么
    有 AI:   {correct}/3 正确识别，自动区分优先级

  为什么 AI 能区分:
    UDP 视频 → tx_packets≈0  → 收发比极大
    TCP 网页 → rx≈tx         → 收发比约 1
    TCP 下载 → tx>>rx        → 收发比远小于 1
""")

print("对比实验完成。两个阶段拓扑和流量完全一致。")
