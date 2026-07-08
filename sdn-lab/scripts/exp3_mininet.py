#!/usr/bin/env python3
"""Experiment 3: Multi-Table Pipeline (ICMP DROP)
   Pipeline: Table 0 → Table 5 (ICMP→DROP, others→Goto 10) → Table 10 (forward)
   预期: TCP 通, ICMP 不通, Table 5 有 ICMP DROP 规则"""
import time, os, subprocess

HOST = os.uname()[1]
print("root@%s:~/lab# python3 exp3_mininet.py\n" % HOST)

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.log import setLogLevel
setLogLevel('error')

net = Mininet(controller=RemoteController, switch=OVSSwitch, autoSetMacs=True)
net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
s1 = net.addSwitch('s1', protocols='OpenFlow13')
for i in range(1, 5):
    net.addHost('h%d' % i, ip='10.0.0.%d/24' % i)
    net.addLink(net.get('h%d' % i), s1)
net.start()
time.sleep(3)

h1, h4 = net.get('h1'), net.get('h4')

# Let ARP settle first
print("=== ARP warmup (h1 ping h2 — but this is also ICMP...) ===")
# Actually all ICMP is blocked. Let's just start with iperf.

print("\n=== Test 1: iperf TCP h1(server) <-> h4(client) ===")
h1.cmd('iperf -s &')
time.sleep(0.5)
iperf_out = h4.cmd('iperf -c 10.0.0.1 -t 3')
print(iperf_out)
h1.cmd('pkill iperf 2>/dev/null')
time.sleep(0.3)
if 'Mbits/sec' in iperf_out or 'Kbits/sec' in iperf_out:
    print(">>> TCP: SUCCESS — h1 ↔ h4")
else:
    print(">>> TCP: FAILED")

print("\n=== Test 2: ping h1 -> h4 (ICMP, expect FAIL) ===")
ping_out = h1.cmd('ping -c 3 -W 1 10.0.0.4')
print(ping_out)
if '100% packet loss' in ping_out or '0 received' in ping_out:
    print(">>> Ping: FAILED (100% loss) — ICMP blocked at Table 5")
else:
    print(">>> Ping: unexpectedly succeeded")

# Compare: ping between h2/h3 (also ICMP, should fail too)
print("=== Test 3: ping h2 -> h3 (also ICMP, should also fail) ===")
out2 = net.get('h2').cmd('ping -c 2 -W 1 10.0.0.3')
print(out2)

print("\n" + "="*60)
print("  FLOW TABLES")
print("="*60)

print("\n--- Table 0: All → Goto Table 5 ---")
subprocess.run(['ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's1', 'table=0'])

print("--- Table 5: ICMP priority=10000 → DROP, others → Table 10 ---")
subprocess.run(['ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's1', 'table=5'])

print("--- Table 10: L2 Forwarding ---")
subprocess.run(['ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's1', 'table=10'])

print("="*60)
print("  KEY: ICMP → DROP | TCP → Table 10 → FORWARD")
print("  Topology alive. Press Enter to stop.")
print("="*60)
try:
    input()
except EOFError:
    pass
net.stop()
