#!/usr/bin/env python3
"""Simple LB test: send TCP SYNs from h1 to 10.0.0.1, check switch logs for port distribution."""
import sys, time, os, glob
sys.path.insert(0, '/root/lab/tutorials/utils')
os.chdir('/root/lab/tutorials/exercises/load_balance')

print("Starting mininet...")
from run_exercise import ExerciseRunner
r = ExerciseRunner('topology.json', 'logs', 'pcaps', 'build/load_balance.json', 'simple_switch_grpc')
r.create_network()

# Wait for gRPC - use simple retry
import socket as sock
for port in [50051, 50052, 50053]:
    for i in range(40):
        try:
            s = sock.socket()
            s.settimeout(0.5)
            s.connect(('127.0.0.1', port))
            s.close()
            break
        except:
            time.sleep(0.3)

r.program_switches()
net = r.net
h1 = net.get('h1')

print("Sending 30 TCP SYNs with different source ports to 10.0.0.1:9999...")
for i in range(30):
    src_port = 20000 + i
    h1.cmd(f'python3 -c "import socket;s=socket.socket();s.settimeout(0.3);s.bind((\"\",{src_port}));s.connect((\"10.0.0.1\",9999));s.close()" 2>/dev/null &')
    time.sleep(0.02)

time.sleep(3)

# Check s1 log for forwarding decisions
print("\n=== s1 forwarding log (last 50 lines) ===")
log = h1.cmd('tail -50 /root/lab/tutorials/exercises/load_balance/logs/s1.log 2>/dev/null || echo "no log"')
for line in log.split('\n'):
    if 'egress_port' in line.lower() or 'egress_spec' in line.lower() or 'port' in line.lower():
        print(line[:200])

# Pingall
print("\n=== Pingall ===")
loss = net.pingAll()
print(f"Ping loss: {loss}%")
net.stop()
