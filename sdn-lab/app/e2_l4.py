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

h1, h4 = net.get('h1'), net.get('h4')
h2, h3 = net.get('h2'), net.get('h3')

print("")
print("root@%s:~/lab# h1 iperf -s &" % HOST)
print("")
h1.cmd('iperf -s &')
time.sleep(0.5)
print("root@%s:~/lab# h4 iperf -c 10.0.0.1 -t 3" % HOST)
print("")
print(h4.cmd('iperf -c 10.0.0.1 -t 3'))
h1.cmd('pkill iperf 2>/dev/null')

print("")
print("root@%s:~/lab# h2 iperf -s -u &" % HOST)
print("")
h2.cmd('iperf -s -u &')
time.sleep(0.5)
print("root@%s:~/lab# h3 iperf -c 10.0.0.2 -u -t 3 -b 1M" % HOST)
print("")
print(h3.cmd('iperf -c 10.0.0.2 -u -t 3 -b 1M'))
h2.cmd('pkill iperf 2>/dev/null')

print("root@%s:~/lab# " % HOST, end="")
try:
    input()
except EOFError:
    pass
net.stop()
