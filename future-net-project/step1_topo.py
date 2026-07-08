#!/usr/bin/env python3
"""
步骤1: 启动 Mininet 拓扑
用法: python3 step1_topo.py
"""
import time, sys
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.log import setLogLevel
setLogLevel('info')

net = Mininet(controller=RemoteController, switch=OVSSwitch, autoSetMacs=True)
net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
net.addSwitch('s1', protocols='OpenFlow13')
for i in range(1, 5):
    net.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
for i in range(1, 5):
    net.addLink(f'h{i}', 's1')
net.start()
time.sleep(2)

h1, h2, h3, h4 = net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')

print("""
============================================================
  拓扑已创建
============================================================
  h1  10.0.0.1  ─┐
  h2  10.0.0.2  ─┤
  h3  10.0.0.3  ─┼── s1 (OVS) ── Ryu 控制器
  h4  10.0.0.4  ─┘
""")

print("--- 连通性测试 ---")
r = net.pingAll(timeout='1')
print(f"丢包率: {r}%\n")

print("拓扑保持存活中。输入 Mininet 命令测试，输入 exit 退出。")
print("例如: h1 ping h4")
from mininet.cli import CLI
CLI(net)
net.stop()
print("拓扑已停止。")
