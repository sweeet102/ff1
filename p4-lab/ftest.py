#!/usr/bin/env python3
"""TCP connectivity test - client retries, no background server needed.
Run as: python3 ftest.py <server_ip> <should_pass>
"""
import socket, time, sys
ip = sys.argv[1]
should_pass = sys.argv[2] == 'pass'
port = 7777

for attempt in range(10):
    s = socket.socket()
    s.settimeout(1)
    try:
        s.connect((ip, port))
        s.send(b'test')
        s.close()
        print(f'CONNECTED to {ip}:{port} (attempt {attempt+1})')
        break
    except:
        s.close()
        time.sleep(0.5)
else:
    print(f'BLOCKED: cannot reach {ip}:{port}')
