#!/usr/bin/python3
"""
Custom topology for SDN traffic mirroring experiment (Section 2.3)

Topology:
    a1 --- s1 --- b1
           |
        sniffer (monitoring port)

S1 Ports:
    eth1: sniffer host (traffic mirror output)
    eth2: a1
    eth3: b1

Usage:
    sudo python3 group_table_topo.py
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel


def create_topo():
    """Build traffic mirroring topology"""
    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        autoSetMacs=True,
    )

    print("[*] Adding controller")
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1')

    print("[*] Adding switch s1")
    s1 = net.addSwitch('s1', protocols='OpenFlow13')

    print("[*] Adding hosts")
    a1 = net.addHost('a1', ip='10.1.1.1/24')
    b1 = net.addHost('b1', ip='10.1.1.2/24')
    sniffer = net.addHost('sniffer', ip='10.1.1.3/24')

    print("[*] Creating links")
    net.addLink(sniffer, s1, port1=0, port2=1)  # s1-eth1: sniffer port
    net.addLink(a1, s1, port1=0, port2=2)        # s1-eth2: a1
    net.addLink(b1, s1, port1=0, port2=3)        # s1-eth3: b1

    print("[*] Starting network")
    net.start()

    print("\n" + "=" * 50)
    print("Topology ready. Switch s1 ports:")
    print("  s1-eth1 -> sniffer (mirror port)")
    print("  s1-eth2 -> a1")
    print("  s1-eth3 -> b1")
    print("=" * 50)
    print("To test: a1 ping b1")
    print("To capture: wireshark -i s1-eth1 -k &")
    print("=" * 50 + "\n")

    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    create_topo()
