#!/usr/bin/env python3
"""Test P4 ECMP load balancing: h1 -> 10.0.0.1 -> h2 or h3."""
import sys, time, os, socket
sys.path.insert(0, '/root/lab/tutorials/utils')
os.chdir('/root/lab/tutorials/exercises/load_balance')

from run_exercise import ExerciseRunner

print("Starting network...")
r = ExerciseRunner('topology.json', 'logs', 'pcaps', 'build/load_balance.json', 'simple_switch_grpc')
r.create_network()

# Wait for gRPC servers
print("Waiting for switches...")
for port in range(50051, 50054):
    ok = False
    for attempt in range(30):
        try:
            s = socket.socket()
            s.settimeout(1)
            s.connect(('127.0.0.1', port))
            s.close()
            ok = True
            break
        except:
            time.sleep(0.3)
    if not ok:
        print(f"Switch on port {port} not ready")
    else:
        print(f"Switch on port {port} ready")

time.sleep(1)

# Program switches with retry
for attempt in range(5):
    try:
        r.program_switches()
        print("Switches programmed!")
        break
    except Exception as e:
        print(f"Retry {attempt+1}: {e}")
        time.sleep(1)

net = r.net
h1, h2, h3 = net.get('h1', 'h2', 'h3')

# Start TCP servers on h2 and h3 to catch LB traffic
h2.cmd('pkill -f "listen" 2>/dev/null; rm -f /tmp/h2_count')
h3.cmd('pkill -f "listen" 2>/dev/null; rm -f /tmp/h3_count')
time.sleep(0.5)

# Start receivers in background using mnexec
h2.sendCmd('while true; do echo x | nc -l 8888 -w 0.5 >> /tmp/h2_count 2>/dev/null; done &')
h3.sendCmd('while true; do echo x | nc -l 8888 -w 0.5 >> /tmp/h3_count 2>/dev/null; done &')
time.sleep(1)

# Send 20 packets from h1
print("\nSending 20 TCP connections to 10.0.0.1:8888...")
for i in range(20):
    h1.cmd(f'python3 -c "import socket;s=socket.socket();s.settimeout(0.5);s.connect((\"10.0.0.1\",8888));s.send(b\"x\");s.close()" 2>/dev/null &')
    time.sleep(0.03)

time.sleep(2)

# Stop servers
h2.sendInt()
h3.sendInt()
time.sleep(0.5)

# Count results
def count_file(path):
    try:
        c = h1.cmd(f'cat /proc/$(pgrep -f "nobody" || echo 1)/fd/1 2>/dev/null || echo 0')
        out = h2.cmd(f'wc -c < {path} 2>/dev/null || echo 0').strip()
        return int(out)
    except:
        return 0

h2_recv = h2.cmd('wc -c < /tmp/h2_count 2>/dev/null || echo 0').strip()
h3_recv = h3.cmd('wc -c < /tmp/h3_count 2>/dev/null || echo 0').strip()

try: h2_recv = int(h2_recv)
except: h2_recv = 0
try: h3_recv = int(h3_recv)
except: h3_recv = 0

print(f"\n=== Load Balance Results ===")
print(f"h2 received: {h2_recv}")
print(f"h3 received: {h3_recv}")

if h2_recv > 0 and h3_recv > 0:
    print("SUCCESS: traffic distributed between h2 and h3!")
elif h2_recv > 0 or h3_recv > 0:
    print("Traffic went to one host only (need more/different source ports)")
else:
    print("No response (may need different test approach)")

print("\n=== Pingall ===")
loss = net.pingAll()
print(f"Ping loss: {loss}%")

net.stop()
