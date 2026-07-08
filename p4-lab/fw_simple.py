#!/usr/bin/env python3
"""Simple TCP test: server + client in one process using fork."""
import socket, time, os, sys

t = sys.argv[1]  # 'server' or 'client'
host = sys.argv[2] if len(sys.argv) > 2 else '0.0.0.0'
port = 8888

if t == 'server':
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(1)
    s.settimeout(8)
    print(f"Server listening on {port}")
    try:
        c, a = s.accept()
        d = c.recv(1024)
        print(f"RECEIVED from {a}: {d.decode()}")
        c.close()
    except socket.timeout:
        print("Server: no connection received")
    s.close()
elif t == 'client':
    time.sleep(0.5)
    s = socket.socket()
    s.settimeout(5)
    try:
        s.connect((host, port))
        s.send(b'hello_firewall_test')
        print(f"CONNECTED to {host}:{port}")
        s.close()
    except Exception as e:
        print(f"BLOCKED ({e})")
