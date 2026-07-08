#!/usr/bin/env python3
"""Experiment 2 (L3): IP-based forwarding — pingall + iperf, keeps topology alive"""
import time, os, subprocess, sys

HOST = os.uname()[1]
print("root@%s:~/lab# python3 exp2_l3_mininet.py\n" % HOST)

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.log import setLogLevel
setLogLevel('info')

print("=== L3 Switch: 4 hosts, 1 switch (IP forwarding) ===")
net = Mininet(controller=RemoteController, switch=OVSSwitch, autoSetMacs=True)
net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
s1 = net.addSwitch('s1', protocols='OpenFlow13')
for i in range(1, 5):
    h = net.addHost('h%d' % i, ip='10.0.0.%d/24' % i)
    net.addLink(h, s1)
net.start()
time.sleep(2)

# Test 1: pingall
print("\n=== Test 1: PingAll ===")
net.pingAll()

# Test 2: iperf TCP (h1 server, h2 client)
print("\n=== Test 2: iperf TCP (h1 server, h4 client) ===")
h1, h4 = net.get('h1'), net.get('h4')
h1.cmd('iperf -s &')
time.sleep(0.5)
print(h4.cmd('iperf -c 10.0.0.1 -t 3'))
time.sleep(0.5)
h1.cmd('pkill iperf 2>/dev/null')

# OVS flow table
print("\n=== OVS L3 Flow Table ===")
out = subprocess.check_output(['ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's1']).decode()
print(out)

print("========================================")
print("  L3 Switch experiment complete.")
print("  Topology still running. Press Enter to stop.")
print("========================================\n")
try:
    input()
except EOFError:
    pass
net.stop()
print("Topology stopped.")
