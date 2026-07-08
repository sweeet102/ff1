#!/usr/bin/env python3
import sys, time
sys.path.insert(0, '/root/lab/tutorials/utils')
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.link import TCLink
from p4_mininet import P4Host, P4Switch
from p4runtime_switch import P4RuntimeSwitch
import p4runtime_lib.simple_controller
import json, os

os.chdir('/root/lab/tutorials/exercises/firewall')

# Read topology
with open('pod-topo/topology.json') as f:
    topo_data = json.load(f)

# Build Mininet topology
net = Mininet(topo=None, host=P4Host, switch=P4RuntimeSwitch, link=TCLink, controller=None)

# Add switches
switches = {}
for sw_name, sw_conf in topo_data['switches'].items():
    prog = sw_conf.get('program', 'build/basic.json')
    sw = net.addSwitch(sw_name, sw_path='simple_switch_grpc',
                       json_path=prog,
                       log_console=True,
                       pcap_dump='pcaps')
    switches[sw_name] = sw

# Add hosts
hosts = {}
for host_name, host_conf in topo_data['hosts'].items():
    h = net.addHost(host_name, ip=host_conf['ip'], mac=host_conf['mac'])
    hosts[host_name] = h

# Add links
for link in topo_data['links']:
    net.addLink(link[0], link[1])

# Start network
net.start()

# Program switches via P4Runtime
for sw_name, sw_conf in topo_data['switches'].items():
    sw = switches[sw_name]
    runtime_file = sw_conf.get('runtime_json')
    if runtime_file:
        p4info = sw_conf.get('program', 'build/basic.json').replace('.json', '.p4.p4info.txtpb')
        bmv2_json = sw_conf.get('program', 'build/basic.json')
        p4runtime_lib.simple_controller.program_switch(
            addr='127.0.0.1:%d' % sw.grpc_port,
            device_id=sw.device_id,
            sw_state_file=runtime_file,
            p4info_path=p4info,
            bmv2_json_file_path=bmv2_json,
        )

h1, h2, h3 = net.get('h1', 'h2', 'h3')

print("\n=== Test 1: h1 -> h2 (internal, should PASS) ===")
out = h1.cmd('python3 -c "import socket;s=socket.socket();s.settimeout(3);s.connect((\"10.0.2.2\",7777));s.send(b\"hi\");s.close();print(\"CONNECTED\")" 2>&1 &')
time.sleep(0.3)
out2 = h2.cmd('timeout 5 python3 -c "import socket;s=socket.socket();s.setsockopt(1,2,1);s.bind((\"\",7777));s.listen(1);s.settimeout(4);c,a=s.accept();print(\"RECEIVED\");c.close();s.close()" 2>&1')
print(f"h2 server: {out2.strip()}")

time.sleep(0.5)
out3 = h1.cmd('python3 -c "import socket;s=socket.socket();s.settimeout(3);s.connect((\"10.0.2.2\",7777));s.send(b\"hi\");s.close();print(\"CONNECTED\")" 2>&1')
print(f"h1 client: {out3.strip()}")

print("\n=== Test 2: h3 -> h1 (external, should be BLOCKED) ===")
out = h1.cmd('timeout 5 python3 -c "import socket;s=socket.socket();s.setsockopt(1,2,1);s.bind((\"\",7778));s.listen(1);s.settimeout(4);c,a=s.accept();print(\"RECEIVED\");c.close();s.close()" 2>&1 &')
time.sleep(0.5)
out2 = h3.cmd('python3 -c "import socket;s=socket.socket();s.settimeout(5);s.connect((\"10.0.1.1\",7778));s.send(b\"hi\");s.close();print(\"CONNECTED\")" 2>&1')
print(f"h3 client: {out2.strip()}")
time.sleep(1)

print("\n=== Pingall ===")
loss = net.pingAll()
print(f"Loss: {loss}%")

net.stop()
