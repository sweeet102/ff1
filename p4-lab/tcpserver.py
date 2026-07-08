#!/usr/bin/env python3
import socket, sys
port = int(sys.argv[1]) if len(sys.argv) > 1 else 5555
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', port))
s.listen(1)
print(f"listening on port {port}...")
try:
    s.settimeout(5)
    conn, addr = s.accept()
    data = conn.recv(1024)
    print(f"GOT: {data.decode()}")
    conn.close()
except socket.timeout:
    print("timeout (no connection)")
s.close()
