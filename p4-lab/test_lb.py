#!/usr/bin/env python3
"""Test P4 ECMP load balance: h1 sends to 10.0.0.1, distributed to h2/h3."""
import sys, time, os, threading
sys.path.insert(0, '/root/lab/tutorials/utils')
os.chdir('/root/lab/tutorials/exercises/load_balance')

from run_exercise import ExerciseRunner

print("Starting network...")
r = ExerciseRunner('topology.json', 'logs', 'pcaps', 'build/load_balance.json', 'simple_switch_grpc')
r.create_network()
r.program_switches()
time.sleep(2)
net = r.net
h1, h2, h3 = net.get('h1', 'h2', 'h3')

# Clear
h2.cmd('ip link set lo up; pkill -f "python3 -c" 2>/dev/null')
h3.cmd('ip link set lo up; pkill -f "python3 -c" 2>/dev/null')
h1.cmd('ip link set lo up; pkill -f "python3 -c" 2>/dev/null')
time.sleep(0.5)

# Start listener on h2
h2.cmd('''python3 -c "
import socket, time
s=socket.socket()
s.setsockopt(1,2,1)
s.bind(('',8888))
s.listen(10)
s.settimeout(15)
while True:
    try:
        c,a=s.accept()
        d=c.recv(1024)
        c.close()
        open('/tmp/h2_count','a').write('x')
    except:
        break
s.close()
" &''')

# Start listener on h3
h3.cmd('''python3 -c "
import socket, time
s=socket.socket()
s.setsockopt(1,2,1)
s.bind(('',8888))
s.listen(10)
s.settimeout(15)
while True:
    try:
        c,a=s.accept()
        d=c.recv(1024)
        c.close()
        open('/tmp/h3_count','a').write('x')
    except:
        break
s.close()
" &''')

time.sleep(1)

# Send 20 packets from h1 to LB address 10.0.0.1
print("Sending 20 packets to 10.0.0.1:8888...")
for i in range(20):
    h1.cmd('python3 -c "import socket,random;s=socket.socket();s.settimeout(1);s.setsockopt(1,2,1);s.bind((\"\",{}));s.connect((\"10.0.0.1\",8888));s.send(b\"x\");s.close()" 2>/dev/null'.format(50000 + i))
    time.sleep(0.05)

time.sleep(2)

# Count results
h2_recv = 0
h3_recv = 0
try: h2_recv = len(open('/tmp/h2_count').read())
except: pass
try: h3_recv = len(open('/tmp/h3_count').read())
except: pass

total = h2_recv + h3_recv
print(f"\n=== Load Balance Results ===")
print(f"h2 received: {h2_recv} ({h2_recv*100//total if total else 0}%)")
print(f"h3 received: {h3_recv} ({h3_recv*100//total if total else 0}%)")
print(f"Total: {total}/20")

if h2_recv > 0 and h3_recv > 0:
    print("LOAD BALANCE WORKS - both h2 and h3 received packets!")
elif total > 0:
    print(f"All {total} packets went to one host (need more samples)")
else:
    print("ERROR: no packets received")

print("\n=== Pingall ===")
loss = net.pingAll()
print(f"Ping loss: {loss}%")

net.stop()
