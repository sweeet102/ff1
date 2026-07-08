#!/usr/bin/env python3
"""
HTTP 文件服务器 — 运行在 h4 (服务器)
提供大型二进制文件（模拟视频下载）和 HTML 页面（模拟网页浏览）

用法: python3 server.py [port] [duration_seconds]
默认端口 8000，时长 120 秒
"""
import socket
import sys
import threading
import time
import os

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
DURATION = int(sys.argv[2]) if len(sys.argv) > 2 else 120

# 预生成内容
BIG_FILE = os.urandom(50 * 1024 * 1024)  # 50MB 随机数据（模拟视频文件）
HTML_PAGE = b"""HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: %d\r\n\r\n%s"""
with open('/etc/hostname', 'r') as f:
    hostname = f.read().strip()
PAGE_BODY = f"""<html><head><title>{hostname}</title></head>
<body><h1>Welcome to {hostname}</h1><p>SDN+AI Traffic Classification Demo</p>
<img src="/video" width="1" height="1"><p>{os.urandom(512).hex()}</p></body></html>""".encode()

start_time = time.time()
request_count = [0]


def handle_client(conn, addr):
    try:
        data = conn.recv(4096)
        path = b'/'
        for line in data.split(b'\r\n'):
            if line.startswith(b'GET '):
                path = line.split()[1]
                break

        if path == b'/video' or path == b'/download':
            # 大型文件 → 模拟视频流/文件下载
            header = f"HTTP/1.1 200 OK\r\nContent-Type: application/octet-stream\r\nContent-Length: {len(BIG_FILE)}\r\n\r\n"
            conn.send(header.encode())
            # 分块发送，控制速率，产生持续流量
            chunk = 65536
            for i in range(0, len(BIG_FILE), chunk):
                if time.time() - start_time > DURATION:
                    break
                conn.send(BIG_FILE[i:i + chunk])
                time.sleep(0.002)  # 控制发送速率，产生持续流
        elif path == b'/health':
            conn.send(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
        else:
            # 普通 HTML 页面 → 模拟网页浏览
            body = PAGE_BODY
            header = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\n\r\n"
            conn.send(header.encode() + body)
        request_count[0] += 1
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.settimeout(1)
    s.bind(('0.0.0.0', PORT))
    s.listen(10)
    print(f"[Server] HTTP 文件服务器启动，端口 {PORT}，时长 {DURATION}s")

    while time.time() - start_time < DURATION:
        try:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except socket.timeout:
            continue
        except Exception:
            break

    s.close()
    print(f"[Server] 服务结束，共处理 {request_count[0]} 个请求")


if __name__ == '__main__':
    main()
