import time, os
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.log import setLogLevel
setLogLevel('info')

HOST = os.uname()[1]

print("")
print("root@%s:~/lab# mn --controller=remote,ip=127.0.0.1 --mac --switch=ovsk,protocols=OpenFlow13 --topo=single,4 --test pingall" % HOST)
print("")

net = Mininet(controller=RemoteController, switch=OVSSwitch, autoSetMacs=True)
net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
s1 = net.addSwitch('s1', protocols='OpenFlow13')
for i in range(1, 5):
    h = net.addHost('h%d' % i, ip='10.0.0.%d/24' % i)
    net.addLink(h, s1)
net.start()
time.sleep(1)

net.pingAll()

print("")
print("root@%s:~/lab# " % HOST, end="")
import sys
sys.stdout.flush()
try:
    input()
except EOFError:
    pass
net.stop()
