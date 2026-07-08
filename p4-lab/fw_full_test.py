#!/usr/bin/env python3
"""Firewall end-to-end test using Mininet Python API."""
import sys, time, threading, socket
sys.path.insert(0, '/root/lab/utils')
from run_exercise import ExerciseRunner

os.chdir = lambda x: None  # no-op, use abs paths
import os
os.chdir('/root/lab/tutorials/exercises/firewall')

# Start Mininet
print("Starting network...")
r = ExerciseRunner('pod-topo/topology.json', 'build/firewall.json', 'simple_switch_grpc')
r.create_network()
r.program_switches()
net = r.net
h1, h2, h3 = net.get('h1', 'h2', 'h3')

results = []

# Test function: start server on host A, client on host B
def tcp_test(client_host, server_host, server_ip, test_name, should_pass):
    time.sleep(0.3)
    # Start server
    s_out = server_host.cmd('timeout 8 python3 -c "
import socket
s=socket.socket()
s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
s.bind((\"\",5559))
s.listen(1)
s.settimeout(6)
try:
    c,a=s.accept()
    d=c.recv(1024)
    c.close()
    print(\"RECEIVED:\"+d.decode())
except:
    print(\"NO_CONNECTION\")
s.close()
" &')
    time.sleep(0.5)
    c_out = client_host.cmd('timeout 5 python3 -c "
import socket
try:
    s=socket.socket()
    s.settimeout(3)
    s.connect((\"' + server_ip + '\",5559))
    s.send(b\"test\")
    s.close()
    print(\"CONNECTED\")
except Exception as e:
    print(\"BLOCKED\")
"')
    time.sleep(1)
    # Parse result
    if 'CONNECTED' in c_out:
        actual = 'PASS'
    else:
        actual = 'BLOCKED'
    expected = 'PASS' if should_pass else 'BLOCKED'
    ok = (actual == expected)
    status = 'OK' if ok else 'WRONG'
    results.append((test_name, actual, expected, status))
    print(f"[{status}] {test_name}: {actual} (expected {expected})")
    server_host.cmd('pkill -9 -f "socket" 2>/dev/null; pkill -9 -f "timeout 8" 2>/dev/null')

# Test 1: h1 → h2, internal, should pass
tcp_test(h1, h2, '10.0.2.2', 'h1->h2 (internal)', True)

# Test 2: h3 → h1, external, should be blocked
tcp_test(h3, h1, '10.0.1.1', 'h3->h1 (external)', False)

# Pingall
time.sleep(1)
loss = net.pingAll()
print(f"\nPingall loss: {loss}%")

# Summary
print("\n" + "="*40)
for name, actual, expected, status in results:
    print(f"[{status}] {name}: {actual}")
print(f"Pingall: {loss}% loss")
print("="*40)

net.stop()
