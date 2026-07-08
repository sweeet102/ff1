#!/usr/bin/env python3
"""Experiment 5: Load Balancing — SELECT Group Table, s2=30% s3=70%"""
import time, os, subprocess
HOST = os.uname()[1]

print("")
print("root@%s:~/lab# python3 topo/exp5.py" % HOST)
print("")

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.log import setLogLevel
setLogLevel('error')

net = Mininet(controller=RemoteController, switch=OVSSwitch, autoSetMacs=True)
c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
s1 = net.addSwitch('s1', dpid='0000000000000001', protocols='OpenFlow13')
s2 = net.addSwitch('s2', dpid='0000000000000002', protocols='OpenFlow13')
s3 = net.addSwitch('s3', dpid='0000000000000003', protocols='OpenFlow13')
s4 = net.addSwitch('s4', dpid='0000000000000004', protocols='OpenFlow13')
h1 = net.addHost('h1', ip='10.1.1.1/24')
h2 = net.addHost('h2', ip='10.1.1.2/24')
net.addLink(h1, s1, port2=3)
net.addLink(h2, s4, port2=3)
net.addLink(s1, s2, port1=1, port2=1)
net.addLink(s1, s3, port1=2, port2=1)
net.addLink(s4, s2, port1=1, port2=2)
net.addLink(s4, s3, port1=2, port2=2)
net.start()
time.sleep(5)

# Ping first
print("")
print("root@%s:~/lab# h1 ping -c 2 h2" % HOST)
print(h1.cmd('ping -c 2 -W 1 10.1.1.2'))

# iperf
print("")
print("root@%s:~/lab# h1 iperf -s &" % HOST)
h1.cmd('iperf -s &')
time.sleep(0.5)
print("root@%s:~/lab# h2 iperf -c 10.1.1.1 -t 5" % HOST)
print(h2.cmd('iperf -c 10.1.1.1 -t 5'))
h1.cmd('pkill iperf 2>/dev/null')

# OVS queries
print("")
print("root@%s:~/lab# ovs-ofctl -O OpenFlow13 dump-groups s1" % HOST)
subprocess.run(['ovs-ofctl', '-O', 'OpenFlow13', 'dump-groups', 's1'])
print("")
print("root@%s:~/lab# ovs-ofctl -O OpenFlow13 dump-flows s2" % HOST)
subprocess.run(['ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's2'])
print("")
print("root@%s:~/lab# ovs-ofctl -O OpenFlow13 dump-flows s3" % HOST)
subprocess.run(['ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's3'])

print("")
print("root@%s:~/lab# " % HOST, end="")
try:
    input()
except EOFError:
    pass
net.stop()
