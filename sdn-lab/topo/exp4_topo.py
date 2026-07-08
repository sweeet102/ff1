#!/usr/bin/env python3
"""Experiment 4: Group Table Traffic Mirroring — a1 <-> b1, sniffer captures all"""
import time, os, subprocess
HOST = os.uname()[1]

print("")
print("root@%s:~/lab# python3 topo/group_table_topo.py" % HOST)
print("")

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.log import setLogLevel
setLogLevel('error')

net = Mininet(controller=RemoteController, switch=OVSSwitch, autoSetMacs=True)
net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
s1 = net.addSwitch('s1', protocols='OpenFlow13')
a1 = net.addHost('a1', ip='10.1.1.1/24')
b1 = net.addHost('b1', ip='10.1.1.2/24')
sniffer = net.addHost('sniffer', ip='10.1.1.3/24')
net.addLink(sniffer, s1, port1=0, port2=1)
net.addLink(a1, s1, port1=0, port2=2)
net.addLink(b1, s1, port1=0, port2=3)
net.start()
time.sleep(2)

print("")
print("root@%s:~/lab# a1 ping -c 3 b1" % HOST)
print(a1.cmd('ping -c 3 -W 1 10.1.1.2'))
print("root@%s:~/lab# b1 ping -c 3 a1" % HOST)
print(b1.cmd('ping -c 3 -W 1 10.1.1.1'))

print("")
print("root@%s:~/lab# " % HOST, end="")
try:
    input()
except EOFError:
    pass
net.stop()
