#!/usr/bin/python3
"""
Custom topology for SDN load balancing experiment (Section 2.4)

Topology (Figure 2.8):
          +-- s2 --+
         /          \
    h1--s1          s4--h2
         \          /
          +-- s3 --+

s1 Ports:
    eth1 -> s2
    eth2 -> s3
    eth3 -> h1

s4 Ports:
    eth1 -> s2
    eth2 -> s3
    eth3 -> h2

s2 Ports:
    eth1 -> s1
    eth2 -> s4

s3 Ports:
    eth1 -> s1
    eth2 -> s4

Load balancing weights: s2=30%, s3=70% (configurable in controller)

Usage:
    sudo python3 group_table_lb.py
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel


def create_topo():
    """Build load balancing topology"""
    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        autoSetMacs=True,
    )

    print("[*] Adding controller")
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1')

    print("[*] Adding switches")
    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    s2 = net.addSwitch('s2', protocols='OpenFlow13')
    s3 = net.addSwitch('s3', protocols='OpenFlow13')
    s4 = net.addSwitch('s4', protocols='OpenFlow13')

    print("[*] Adding hosts")
    h1 = net.addHost('h1', ip='10.1.1.1/24')
    h2 = net.addHost('h2', ip='10.1.1.2/24')

    print("[*] Creating links")
    # h1 <-> s1 (port 3), h2 <-> s4 (port 3)
    net.addLink(h1, s1, port1=0, port2=3)
    net.addLink(h2, s4, port1=0, port2=3)

    # s1 <-> s2, s1 <-> s3
    net.addLink(s1, s2, port1=1, port2=1)
    net.addLink(s1, s3, port1=2, port2=1)

    # s4 <-> s2, s4 <-> s3
    net.addLink(s4, s2, port1=1, port2=2)
    net.addLink(s4, s3, port1=2, port2=2)

    print("[*] Starting network")
    net.start()

    print("\n" + "=" * 50)
    print("Load Balancing Topology ready.")
    print("  h1 (10.1.1.1) <-> s1 <-> s2/s3 <-> s4 <-> h2 (10.1.1.2)")
    print("  LB Weight: s2=30%, s3=70%")
    print("=" * 50)
    print("To test: h1 iperf -s & ; h2 iperf -c 10.1.1.1 -t 30")
    print("To check groups: ovs-ofctl -O OpenFlow13 dump-groups s1")
    print("                  ovs-ofctl -O OpenFlow13 dump-flows s2")
    print("                  ovs-ofctl -O OpenFlow13 dump-flows s3")
    print("=" * 50 + "\n")

    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    create_topo()
