#!/usr/bin/env python3
import socket, sys, time
host = sys.argv[1]
port = int(sys.argv[2])
msg = sys.argv[3] if len(sys.argv) > 3 else "hello"
try:
    s = socket.socket()
    s.settimeout(3)
    s.connect((host, port))
    s.send(msg.encode())
    s.close()
    print(f"CONNECTED to {host}:{port}")
except Exception as e:
    print(f"BLOCKED: {e}")
