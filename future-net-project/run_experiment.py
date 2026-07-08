#!/usr/bin/env python3
"""
SDN + AI 流量分类实验 — 终端输出版
每个步骤输出清晰，可截图用于报告
"""
import time
import sys
import json
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.log import setLogLevel

setLogLevel('info')
PROJECT = '/root/future-net-project'
DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 60

print()
print("=" * 60)
print("  未来网络技术课程实践")
print("  SDN + AI 智能流量分类实验")
print("=" * 60)


def hr(title):
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


# ================================================================
# Step 1: 创建拓扑
# ================================================================
hr("Step 1: 创建 Mininet 拓扑")
net = Mininet(topo=None, build=False)
net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
net.addSwitch('s1', cls=OVSSwitch, protocols='OpenFlow13')
for i in range(1, 5):
    net.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
for i in range(1, 5):
    net.addLink(f'h{i}', 's1')
net.build()
net.start()
time.sleep(2)

h1, h2, h3, h4 = net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')

print(f"""
  拓扑信息:
    h1  10.0.0.1  ─┐
    h2  10.0.0.2  ─┤
    h3  10.0.0.3  ─┼── s1 (OVS) ── Ryu+AI 控制器
    h4  10.0.0.4  ─┘
""")

# 连通性
r = net.pingAll(timeout='1')
print(f"  连通性测试: {r}% 丢包")

# ================================================================
# Step 2: 验证 AI 服务连接
# ================================================================
hr("Step 2: 验证 AI 推理服务")
import requests
try:
    resp = requests.get('http://127.0.0.1:5001/', timeout=2)
    info = resp.json()
    print(f"  AI 服务: ✓ 已连接")
    print(f"  模型: {info.get('model')}")
    print(f"  准确率: {info.get('accuracy', 0)*100:.0f}%")
    print(f"  分类: {info.get('classes')}")
    print(f"  API: POST http://127.0.0.1:5001/predict")
except Exception as e:
    print(f"  AI 服务: ✗ 未连接 ({e})")
    print(f"  请先启动: python3 {PROJECT}/ai_server.py &")

# ================================================================
# Step 3: 生成流量
# ================================================================
hr("Step 3: 启动流量生成")
print(f"""
  h1 (10.0.0.1) → 视频流模拟  UDP 大包高频 (~200pps, 1200B/包)
  h2 (10.0.0.2) → 网页浏览模拟  TCP 间歇连接 (用户点击)
  h3 (10.0.0.3) → 文件下载模拟  TCP 持续大流量
  h4 (10.0.0.4) → 服务器       接收并响应
""")

h4.popen(f'python3 {PROJECT}/server.py 120')
time.sleep(2)
h1.popen(f'python3 {PROJECT}/traffic_gen.py video 10.0.0.4 {DUR}')
h2.popen(f'python3 {PROJECT}/traffic_gen.py web 10.0.0.4 {DUR}')
h3.popen(f'python3 {PROJECT}/traffic_gen.py download 10.0.0.4 {DUR}')
print("  流量已启动，等待 AI 分类...")

# ================================================================
# Step 4: 观察 AI 推理
# ================================================================
hr("Step 4: AI 实时分类结果")

prev_count = 0
for i in range(8):
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
                ts = e['time']
                port = e['port']
                conf = e['confidence'] * 100
                rate = e['pkt_rate']
                size = e['avg_pkt_size']
                api_n = e.get('api_request', 0)
                print('  {} | API#{} | 端口{} {} {} | 置信度{:.0f}% | 速率{:.0f}pps | 包大小{:.0f}B'.format(
                    ts, api_n, port, icon, cls, conf, rate, size))
            prev_count = len(log)

        if api_reqs:
            print(f"  >>> AI API 累计请求: {api_reqs} 次", end='\r')
    except Exception:
        pass
print()

# ================================================================
# Step 5: 最终分类结果
# ================================================================
hr("Step 5: 最终分类结果")
time.sleep(3)

try:
    with open('/tmp/qos_results.json') as f:
        data = json.load(f)
    pc = data.get('port_classes', {})
    log = data.get('log', [])

    # 统计每个端口的最新分类
    print(f"\n  端口映射:")
    print(f"  {'端口':<6} {'主机':<8} {'IP':<14} {'分类':<12} {'标签':<14}")
    print(f"  {'─' * 54}")

    host_map = {'1': ('h1', '10.0.0.1'), '2': ('h2', '10.0.0.2'),
                '3': ('h3', '10.0.0.3'), '4': ('h4', '10.0.0.4')}

    for port in sorted(pc, key=int):
        cls = pc[port]
        host, ip = host_map.get(port, ('?', '?'))
        expected = {'1': '视频流', '2': '网页浏览', '3': '文件下载', '4': '服务器'}.get(port, '-')
        icon = {'video': '📹', 'web': '🌐', 'download': '📥'}.get(cls, '?')
        status = '✓' if (
            (port == '1' and cls == 'video') or
            (port == '2' and cls == 'web') or
            (port == '3' and cls == 'download')
        ) else ' '
        print(f"  {status} 端口{port:<4} {host:<8} {ip:<14} {icon} {cls:<9} {expected}")

    # 准确率
    correct = 0
    for port in ['1', '2', '3']:
        expected = {'1': 'video', '2': 'web', '3': 'download'}[port]
        if pc.get(port) == expected:
            correct += 1
    if correct == 3:
        print(f"\n  ✓ AI 分类全部正确！(3/3)")
    else:
        print(f"\n  分类结果: {correct}/3 正确")

    print(f"\n  AI API 累计请求: {data.get('api_requests', 0)} 次")

except Exception as e:
    print(f"  读取结果失败: {e}")

# ================================================================
# Step 6: 测试 AI 推理 API 示例
# ================================================================
hr("Step 6: 直接测试 AI API")

test_feats = {
    '视频流': [400, 480000, 3, 192, 180, 192000, 1200, 1.5, 2000, 100],
    '网页浏览': [60, 33000, 45, 22500, 30, 16500, 550, 22.5, 2000, 1.3],
    '文件下载': [150, 9600, 800, 1120000, 80, 4800, 64, 400, 2000, 0.19],
}

print()
for label, feats in test_feats.items():
    try:
        r = requests.post('http://127.0.0.1:5001/predict',
                          json={'features': feats}, timeout=2)
        if r.status_code == 200:
            result = r.json()
            print(f"  {label:<8} → {result['class']:<10} "
                  f"置信度 {result['confidence']*100:.0f}%  "
                  f"(API请求 #{result['request_id']})")
        else:
            print(f"  {label}: API 错误 {r.status_code}")
    except Exception as e:
        print(f"  {label}: 请求失败 - {e}")

# ================================================================
# 完成
# ================================================================
hr("实验完成")
print(f"""
  总结:
  ✓ Mininet 拓扑: 4 主机 + 1 OVS 交换机
  ✓ 流量生成: Python socket (视频/网页/下载)
  ✓ SDN 控制: Ryu + OpenFlow 1.3 采集端口统计
  ✓ AI 推理: Random Forest 微服务 API (POST /predict)
  ✓ 架构: Ryu → HTTP → AI API → 分类结果 → QoS 策略

  截图要点:
  1. 连通性测试结果 (Step 1)
  2. AI API 服务信息 (Step 2)
  3. 实时分类日志 (Step 4)
  4. 最终分类结果 + 准确率 (Step 5)
  5. API 直接测试 (Step 6)
""")

net.stop()
print("\n实验结束。")
