#!/usr/bin/env python3
"""L4 Switch: TCP/UDP/ICMP forwarding — ping + iperf, keeps topology alive"""
import time, os, subprocess

HOST = os.uname()[1]
print("root@%s:~/lab# python3 exp2_l4_mininet.py\n" % HOST)

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.log import setLogLevel
setLogLevel('info')

print("=== L4 Switch: 4 hosts, 1 switch (TCP/UDP/ICMP forwarding) ===")
net = Mininet(controller=RemoteController, switch=OVSSwitch, autoSetMacs=True)
net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
s1 = net.addSwitch('s1', protocols='OpenFlow13')
for i in range(1, 5):
    h = net.addHost('h%d' % i, ip='10.0.0.%d/24' % i)
    net.addLink(h, s1)
net.start()
time.sleep(2)

# Test 1: pingall (ICMP)
print("\n=== Test 1: PingAll (ICMP) ===")
net.pingAll()

# Test 2: iperf TCP (h1 server, h4 client)
print("\n=== Test 2: iperf TCP (h1 server, h4 client) ===")
h1, h4 = net.get('h1'), net.get('h4')
h1.cmd('iperf -s &')
time.sleep(0.5)
print(h4.cmd('iperf -c 10.0.0.1 -t 2'))
h1.cmd('pkill iperf 2>/dev/null')

# Test 3: iperf UDP (h2 server, h3 client)
print("\n=== Test 3: iperf UDP (h2 server, h3 client) ===")
h2, h3 = net.get('h2'), net.get('h3')
h2.cmd('iperf -s -u &')
time.sleep(0.5)
print(h3.cmd('iperf -c 10.0.0.2 -u -t 2 -b 1M'))
h2.cmd('pkill iperf 2>/dev/null')

# OVS flow table
print("\n=== OVS L4 Flow Table ===")
out = subprocess.check_output(['ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's1']).decode()
print(out)

# Filter: show only L4 matches (with tcp/udp/icmp proto)
print("=== L4-specific flows (IP proto + ports) ===")
for line in out.split('\n'):
    if 'tcp' in line or 'udp' in line or 'icmp' in line:
        print(line)

print("========================================")
print("  L4 Switch experiment complete.")
print("  Press Enter to stop topology.")
print("========================================")
try:
    input()
except EOFError:
    pass
net.stop()
