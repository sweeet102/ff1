#!/usr/bin/env python3
"""
步骤2: 启动流量 + AI 实时分类
前提: Ryu + AI Server 已启动（窗口1）
用法: python3 step2_traffic.py [duration]
"""
import time, sys, json
PROJECT = '/root/future-net-project'
DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 45

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.log import setLogLevel
setLogLevel('info')

# 验证 AI 服务
import requests
try:
    r = requests.get('http://127.0.0.1:5001/', timeout=2)
    info = r.json()
    print(f"AI 服务: 已连接 | 模型: {info['model']} | 准确率: {info['accuracy']*100:.0f}%")
except Exception:
    print("AI 服务: 未连接！请先在窗口1启动 ai_server.py")
    sys.exit(1)

print("""
============================================================
  步骤2: 启动拓扑 + 流量 + AI 实时分类
============================================================
""")

# 创建拓扑
print("创建 Mininet 拓扑...")
net = Mininet(controller=RemoteController, switch=OVSSwitch, autoSetMacs=True)
net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
net.addSwitch('s1', protocols='OpenFlow13')
for i in range(1, 5):
    net.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
for i in range(1, 5):
    net.addLink(f'h{i}', 's1')
net.start()
time.sleep(3)

h1, h2, h3, h4 = net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')

# 连通性
print("连通性测试...")
r = net.pingAll(timeout='1')
print(f"丢包率: {r}%\n")

# 启动 h4 HTTP 文件服务器
print("启动 HTTP 文件服务器 (h4:8000)...")
h4.popen(f'python3 {PROJECT}/server.py 8000 120')
time.sleep(2)

print("""
流量产生:
  h1 → Python socket UDP 大包  (模拟视频流，UDP单向高频)
  h2 → curl 间歇请求 /         (模拟网页浏览，TCP双向)
  h3 → wget 下载 /download      (模拟文件下载，TCP单向大流量)

AI 分类依据: OVS 端口统计（不关心上层用什么工具）
  UDP 视频 → 大包、高频、几乎无回包 → tx_packets≈0
  TCP 网页 → 中包、间歇、双向通信   → rx≈tx
  TCP 下载 → 小包ACK、大量tx数据   → tx>>rx
""")

# 启动流量
# h1: Python socket UDP 大包 → h4:9999（模拟视频流，UDP单向，与TCP下载可区分）
h1.popen(f'python3 {PROJECT}/traffic_gen.py video 10.0.0.4 8000 {DUR}')
# h2: curl 间歇请求 → h4:8000（模拟网页浏览，TCP双向）
h2.popen(f'python3 {PROJECT}/traffic_gen.py web 10.0.0.4 8000 {DUR}')
# h3: wget 下载 → h4:8000（模拟文件下载，TCP单向大流量）
h3.popen(f'python3 {PROJECT}/traffic_gen.py download 10.0.0.4 8000 {DUR}')

# 实时观察 AI 分类
print("等待 AI 分类 (每 2 秒采集 OVS 端口统计)...\n")
prev_count = 0
start = time.time()
while time.time() - start < min(DUR, 40):
    time.sleep(3)
    try:
        with open('/tmp/qos_results.json') as f:
            data = json.load(f)
        log = data.get('log', [])
        api_reqs = data.get('api_requests', 0)

        if len(log) > prev_count:
            for e in log[prev_count:]:
                cls = e['class']
                icon = {'video': '📹', 'web': '🌐', 'download': '📥'}.get(cls, '?')
                print(f"  {e['time']} 端口{e['port']} {icon} {cls} | "
                      f"置信度{e['confidence']*100:.0f}% | "
                      f"速率{e['pkt_rate']:.0f}pps | "
                      f"API #{e.get('api_request','?')}")
            prev_count = len(log)

        if api_reqs > 0:
            elapsed = int(time.time() - start)
            print(f"  [{elapsed}s] AI API 累计: {api_reqs} 次", end='\r')
    except Exception:
        pass

print()

# 最终结果
print("============================================================")
print("  最终分类结果")
print("============================================================")
try:
    with open('/tmp/qos_results.json') as f:
        data = json.load(f)
    pc = data.get('port_classes', {})

    host_tool = {'1': 'h1 - curl /video', '2': 'h2 - curl /', '3': 'h3 - wget /download'}
    expected = {'1': 'video', '2': 'web', '3': 'download'}
    correct = 0
    for port in ['1', '2', '3']:
        cls = pc.get(port, '?')
        exp = expected[port]
        ok = '✓' if cls == exp else '✗'
        if cls == exp:
            correct += 1
        icon = {'video': '📹', 'web': '🌐', 'download': '📥'}.get(cls, '?')
        print(f"  {ok} 端口{port} ({host_tool[port]}) → {icon} {cls}")

    print(f"\n  分类正确: {correct}/3")
    print(f"  AI API 累计请求: {data.get('api_requests', 0)} 次")
    print(f"  说明: 无论上层用 curl/wget/socket，AI 只看交换机统计")
except Exception as e:
    print(f"  读取结果失败: {e}")

net.stop()
print("\n步骤2 完成。")
