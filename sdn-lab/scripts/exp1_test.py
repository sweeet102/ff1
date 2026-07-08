#!/usr/bin/env python3
"""Experiment 1: L2 switch test with flow table capture"""
import subprocess, time, os

# Start topology and keep it alive
os.system("mn -c 2>/dev/null")

# Run a test that keeps topology alive during capture
script = """
import subprocess, time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

setLogLevel('info')

net = Mininet(
    controller=RemoteController,
    switch=OVSSwitch,
    autoSetMacs=True
)
c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
s1 = net.addSwitch('s1', protocols='OpenFlow13')
h1 = net.addHost('h1', ip='10.0.0.1/24')
h2 = net.addHost('h2', ip='10.0.0.2/24')
h3 = net.addHost('h3', ip='10.0.0.3/24')
h4 = net.addHost('h4', ip='10.0.0.4/24')
net.addLink(h1, s1)
net.addLink(h2, s1)
net.addLink(h3, s1)
net.addLink(h4, s1)
net.start()

time.sleep(1)
print("\\n=== OVS Flow Table (initial) ===")
out = subprocess.check_output(['ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's1']).decode()
print(out)

print("\\n=== Ping from h1 to h2 ===")
result = net.ping([h1, h2])
print(f"Result: {result}% loss")

time.sleep(0.5)
print("\\n=== OVS Flow Table (after ping) ===")
out = subprocess.check_output(['ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's1']).decode()
print(out)

print("\\n=== PingAll ===")
result = net.pingAll()
print(f"Result: {result}% loss")

print("\\n=== OVS Show ===")
out = subprocess.check_output(['ovs-vsctl', 'show']).decode()
print(out)

net.stop()
print("=== Experiment 1 Complete ===")
"""

with open('/tmp/exp1_runner.py', 'w') as f:
    f.write(script)

result = os.system("python3 /tmp/exp1_runner.py 2>&1")
print(f"\nExit code: {result}")
