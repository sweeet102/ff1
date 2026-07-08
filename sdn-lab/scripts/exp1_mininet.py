#!/usr/bin/env python3
"""Experiment 1: L2 Simple Switch — Mininet topology with pingall, stays alive"""
import time, os, sys

print("root@%s:~/lab# python3 exp1_mininet.py" % os.uname()[1])
print("")

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.log import setLogLevel
setLogLevel('info')

print("=== Building Topology: 4 hosts, 1 switch ===")
net = Mininet(controller=RemoteController, switch=OVSSwitch, autoSetMacs=True)
c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
s1 = net.addSwitch('s1', protocols='OpenFlow13')

for i in range(1, 5):
    h = net.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
    net.addLink(h, s1)

net.start()
time.sleep(2)

print("\n=== PingAll: 12 pings (4 hosts, all pairs) ===")
result = net.pingAll()
print(f"\n*** PingAll result: {result}% packet loss")

print("\n========================================")
print("  Experiment 1 L2 Switch — Complete")
print("  Topology is still running.")
print("  Type 'exit' or Ctrl+D to quit.")
print("========================================")
print("")

# Keep alive — show prompt
try:
    input()  # Wait for user to press Enter
except EOFError:
    pass

net.stop()
print("Topology stopped.")
