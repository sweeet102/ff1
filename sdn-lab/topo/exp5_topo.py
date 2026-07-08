#!/usr/bin/env python3
"""Experiment 5: Load Balancing — diamond topo with SELECT Group"""
import time, os
HOST = os.uname()[1]

print("")
print("root@%s:~/lab# python3 topo/group_table_lb.py" % HOST)
print("")

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.log import setLogLevel
setLogLevel('error')

net = Mininet(controller=RemoteController, switch=OVSSwitch, autoSetMacs=True)
net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

# Explicit dpid to match lb.py
s1 = net.addSwitch('s1', dpid='0000000000000001', protocols='OpenFlow13')
s2 = net.addSwitch('s2', dpid='0000000000000002', protocols='OpenFlow13')
s3 = net.addSwitch('s3', dpid='0000000000000003', protocols='OpenFlow13')
s4 = net.addSwitch('s4', dpid='0000000000000004', protocols='OpenFlow13')

h1 = net.addHost('h1', ip='10.1.1.1/24')
h2 = net.addHost('h2', ip='10.1.1.2/24')

# Links matching lb.py port layout
net.addLink(h1, s1, port1=0, port2=3)    # s1 port3 = h1
net.addLink(h2, s4, port1=0, port2=3)    # s4 port3 = h2
net.addLink(s1, s2, port1=1, port2=1)    # s1 port1 = s2 port1
net.addLink(s1, s3, port1=2, port2=1)    # s1 port2 = s3 port1
net.addLink(s4, s2, port1=1, port2=2)    # s4 port1 = s2 port2
net.addLink(s4, s3, port1=2, port2=2)    # s4 port2 = s3 port2

net.start()
time.sleep(4)

print("")
print("root@%s:~/lab# h1 ping -c 3 h2" % HOST)
print(h1.cmd('ping -c 3 -W 1 10.1.1.2'))

print("")
print("root@%s:~/lab# h1 iperf -s &" % HOST)
h1.cmd('iperf -s &')
time.sleep(0.5)

print("")
print("root@%s:~/lab# h2 iperf -c 10.1.1.1 -t 5" % HOST)
print(h2.cmd('iperf -c 10.1.1.1 -t 5'))
h1.cmd('pkill iperf 2>/dev/null')

print("")
print("root@%s:~/lab# " % HOST, end="")
try:
    input()
except EOFError:
    pass
net.stop()
