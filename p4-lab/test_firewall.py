#!/usr/bin/env python3
"""Test firewall: iperf h1->h2 (OK), h3->h1 (BLOCKED)"""
import os, sys, time, subprocess

sys.path.insert(0, '/root/lab/tutorials/utils')
sys.path.insert(0, '/root/lab/tutorials/exercises/firewall')

from run_exercise import ExerciseRunner

os.chdir('/root/lab/tutorials/exercises/firewall')

ex = ExerciseRunner('pod-topo/topology.json', 'build/firewall.json', 'simple_switch_grpc')
ex.create_network()
ex.program_switches()

net = ex.net
h1, h2, h3, h4 = net.get('h1', 'h2', 'h3', 'h4')

print("=== Test 1: iperf h1 -> h2 (internal->internal: should work) ===")
sys.stdout.flush()
try:
    result = net.iperf([h1, h2], l4Type='TCP', seconds=2)
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")

time.sleep(1)

print("\n=== Test 2: iperf h3 -> h1 (external->internal: should be BLOCKED) ===")
sys.stdout.flush()
try:
    result = net.iperf([h3, h1], l4Type='TCP', seconds=2)
    print(f"Result: {result}")
except Exception as e:
    print(f"BLOCKED (expected): {e}")

time.sleep(1)

print("\n=== Test 3: pingall ===")
sys.stdout.flush()
try:
    loss = net.pingAll()
    print(f"Ping loss: {loss}%")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Done ===")
net.stop()
