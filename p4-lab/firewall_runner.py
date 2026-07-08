#!/usr/bin/env python3
"""Run firewall experiment and test all scenarios."""
import sys, time
sys.path.insert(0, '/root/lab/tutorials/utils')
from run_exercise import ExerciseRunner
from mininet.net import Mininet

r = ExerciseRunner('pod-topo/topology.json', 'build/firewall.json', 'simple_switch_grpc')
r.create_network()
r.program_switches()
net = r.net
h1, h2, h3, h4 = net.get('h1', 'h2', 'h3', 'h4')

print("\n=== Test 1: pingall (ICMP, should all pass) ===")
loss = net.pingAll()
print(f"Ping loss: {loss}%")

print("\n=== Test 2: h1 -> h2 TCP (internal->internal, SHOULD work) ===")
h2.cmd('nc -l 5555 &')
time.sleep(0.5)
out = h1.cmd('echo OK | nc -w 2 10.0.2.2 5555')
print(f"Result: {'PASS - connection succeeded' if out else 'FAIL - no response'}")

print("\n=== Test 3: h1 -> h3 TCP (internal->external, SHOULD work) ===")
h3.cmd('nc -l 5556 &')
time.sleep(0.5)
out = h1.cmd('echo OK | nc -w 2 10.0.3.3 5556')
print(f"Result: {'PASS - connection succeeded' if out else 'FAIL - no response'}")

print("\n=== Test 4: h3 -> h1 TCP (external->internal, should be BLOCKED) ===")
h1.cmd('nc -l 5557 &')
time.sleep(0.5)
out = h3.cmd('echo BLOCKED | nc -w 3 10.0.1.1 5557 2>&1')
print(f"Result: {'BLOCKED (expected)' if not out else 'WARNING - connection succeeded (should be blocked)'}")

print("\n=== Test 5: h4 -> h2 TCP (external->internal, should be BLOCKED) ===")
h2.cmd('pkill nc 2>/dev/null; nc -l 5558 &')
time.sleep(0.5)
out = h4.cmd('echo BLOCKED | nc -w 3 10.0.2.2 5558 2>&1')
print(f"Result: {'BLOCKED (expected)' if not out else 'WARNING - connection succeeded (should be blocked)'}")

print("\n=== All tests complete ===")
net.stop()
