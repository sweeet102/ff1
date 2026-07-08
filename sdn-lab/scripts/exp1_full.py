#!/usr/bin/env python3
"""Experiment 1: L2 Switch — Full test with pcap capture"""
import subprocess, os, time, signal, sys

os.system("pkill ryu-manager 2>/dev/null; mn -c 2>/dev/null; sleep 1")

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.log import setLogLevel
setLogLevel('info')

# Start tshark capture in background
tshark_proc = subprocess.Popen(
    ['tshark', '-i', 'any', '-w', '/root/lab/output/exp1_capture.pcap', '-q'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
time.sleep(1)

# Start Ryu controller
print("=== Starting Ryu Controller ===")
ryu_proc = subprocess.Popen(
    ['ryu-manager', 'ryu.app.simple_switch_13'],
    stdout=open('/root/lab/output/ryu_exp1.log', 'w'),
    stderr=subprocess.STDOUT
)
time.sleep(3)

# Build and start network
print("=== Building Topology (4 hosts, 1 switch) ===")
net = Mininet(controller=RemoteController, switch=OVSSwitch, autoSetMacs=True)
c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
s1 = net.addSwitch('s1', protocols='OpenFlow13')
for i in range(1, 5):
    h = net.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
    net.addLink(h, s1)
net.start()
time.sleep(1)

# Test 1: Ping pair
print("\n=== Test 1: h1 ping h2 ===")
result = net.ping([net.get('h1'), net.get('h2')])
print(f"Loss: {result}%")

# OVS flow table
print("\n=== OVS Flow Table ===")
out = subprocess.check_output(['ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's1']).decode()
print(out)

# Test 2: PingAll
print("=== Test 2: PingAll (4 hosts) ===")
result = net.pingAll()
print(f"Loss: {result}%")

# Show OVS info
print("\n=== OVS Switch Info ===")
out = subprocess.check_output(['ovs-vsctl', 'show']).decode()
print(out)

# Stop capture
time.sleep(1)
tshark_proc.send_signal(signal.SIGTERM)
tshark_proc.wait(timeout=5)
net.stop()

# Kill ryu
ryu_proc.terminate()
ryu_proc.wait(timeout=5)

# Analyze capture
print("\n=== Pcap Analysis ===")
try:
    out = subprocess.check_output(
        ['tshark', '-r', '/root/lab/output/exp1_capture.pcap', '-T', 'fields',
         '-e', 'frame.number', '-e', 'ip.src', '-e', 'ip.dst',
         '-e', '_ws.col.Protocol', '-e', 'ofp.type',
         'ip or openflow_v4'],
        timeout=10
    ).decode()
    print(out[:2000] if out else "(no matching packets)")
except subprocess.TimeoutExpired:
    print("(tshark analysis timeout)")

print(f"\nPcap saved: output/exp1_capture.pcap")
print("=== Experiment 1 Complete ===")
