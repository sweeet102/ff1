#!/usr/bin/env python3
"""Run firewall test using Mininet API directly."""
import sys, time, os, socket
sys.path.insert(0, '/root/lab/tutorials/utils')
os.chdir('/root/lab/tutorials/exercises/firewall')

from run_exercise import ExerciseRunner

print("Starting network...", flush=True)
r = ExerciseRunner('pod-topo/topology.json', 'logs', 'pcaps', 'build/basic.json', 'simple_switch_grpc')
r.create_network()
r.program_switches()

# Wait for gRPC servers to be ready
time.sleep(2)
for port in [50051, 50052, 50053, 50054]:
    for retry in range(5):
        try:
            s = socket.socket()
            s.settimeout(1)
            s.connect(('127.0.0.1', port))
            s.close()
            break
        except:
            time.sleep(0.5)

net = r.net
h1, h2, h3 = net.get('h1', 'h2', 'h3')

print("\n=== Pingall ===", flush=True)
loss = net.pingAll()
print(f"Ping loss: {loss}%", flush=True)

print("\n=== h1 -> h2 (internal, should PASS) ===", flush=True)
try:
    result = net.iperf([h1, h2], l4Type='TCP', seconds=2)
    print(f"h1->h2: {result}", flush=True)
except Exception as e:
    print(f"h1->h2 FAIL: {e}", flush=True)

print("\n=== h3 -> h1 (external, should be BLOCKED) ===", flush=True)
try:
    result = net.iperf([h3, h1], l4Type='TCP', seconds=2)
    print(f"h3->h1: {result}", flush=True)
except Exception as e:
    print(f"h3->h1 BLOCKED (expected): {e}", flush=True)

print("\n=== Done ===", flush=True)
net.stop()
