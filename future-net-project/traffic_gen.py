#!/usr/bin/env python3
"""
流量生成脚本 — 在 Mininet 主机上运行
用法: python3 traffic_gen.py <type> <server_ip> [duration]

类型:
  video      — curl 循环下载大文件（模拟视频流，持续大流量）
  web        — curl 循环请求 HTML 页面（模拟网页浏览，间歇连接）
  download   — wget 下载大文件（模拟文件下载，单次长时间传输）
  socket_v   — Python socket UDP（旧版视频流，用于对比）
"""
import subprocess
import sys
import time
import random

TYPE = sys.argv[1]
SERVER = sys.argv[2]
PORT = sys.argv[3] if len(sys.argv) > 3 else '8000'
DUR = int(sys.argv[4]) if len(sys.argv) > 4 else 120

runners = {}


def run_video(server, port, dur):
    """UDP 大包高频发送 → 模拟视频流（UDP 单向，特征与 TCP 下载明显不同）"""
    import socket as sock
    print(f"[video] UDP 大包 → {server}:9999，持续 {dur}s")
    s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
    s.setsockopt(sock.SOL_SOCKET, sock.SO_REUSEADDR, 1)
    end = time.time() + dur
    seq = 0
    while time.time() < end:
        try:
            s.sendto(b'\x00' * 1200, (server, 9999))
            seq += 1
            time.sleep(0.005)  # ~200 pps
        except Exception:
            time.sleep(0.01)
    s.close()


def run_web(server, port, dur):
    """curl 间歇请求 HTML 页面 → 模拟用户浏览网页"""
    print(f"[web] curl 间歇请求 / 页面，持续 {dur}s")
    end = time.time() + dur
    while time.time() < end:
        # 模拟用户一次请求多个对象（HTML + 内嵌资源）
        for _ in range(random.randint(2, 5)):
            subprocess.run(
                ['timeout', '5', 'curl', '-s', '-o', '/dev/null',
                 f'http://{server}:{port}/'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            time.sleep(random.uniform(0.1, 0.5))
        time.sleep(random.uniform(0.5, 3.0))  # 用户阅读间隔


def run_download(server, port, dur):
    """wget 下载大文件 → 模拟文件下载"""
    print(f"[download] wget 下载 /download，持续 {dur}s")
    end = time.time() + dur
    while time.time() < end:
        subprocess.run(
            ['timeout', '30', 'wget', '-q', '-O', '/dev/null',
             f'http://{server}:{port}/download'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(2)  # 下载完成后间隔


runners = {
    'video': run_video,
    'web': run_web,
    'download': run_download,
}

if TYPE not in runners:
    print(f"未知类型: {TYPE}，可选: {list(runners.keys())}")
    sys.exit(1)

print(f"[{TYPE}] → http://{SERVER}:{PORT}/ 时长 {DUR}s")
runners[TYPE](SERVER, PORT, DUR)
print(f"[{TYPE}] 完成")
