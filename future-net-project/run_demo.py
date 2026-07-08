#!/usr/bin/env python3
"""
实时仪表盘 — 窗口3
读取 Ryu 控制器输出的 /tmp/qos_results.json 并格式化展示

用法: python3 run_demo.py
（需要先启动窗口1(Ryu)和窗口2(topo.py)）
"""
import json
import time
import os
import sys

RESULT_FILE = '/tmp/qos_results.json'


def print_dashboard(data):
    """打印格式化仪表盘"""
    os.system('clear' if os.name != 'nt' else 'cls')

    print("╔" + "═" * 58 + "╗")
    print("║  SDN + AI 智能流量分类与 QoS 管理系统" + " " * 19 + "║")
    print("║  " + "Future Network Technology Course" + " " * 24 + "║")
    print("╚" + "═" * 58 + "╝")

    port_classes = data.get('port_classes', {})
    log = data.get('log', [])[-10:]  # 最近10条

    print(f"\n  ⏱ {data.get('timestamp', '--')}  |  已分类端口: {len(port_classes)}")

    # 端口分类状态
    if port_classes:
        print(f"\n  ┌── 端口流量分类 ──────────────────────────────────┐")
        print(f"  │ {'端口':<6} {'流量类型':<12} {'QoS 策略':<20} │")
        print(f"  │ {'-'*40} │")
        for port, cls in sorted(port_classes.items()):
            icon = {'video': '📹 视频流', 'web': '🌐 网页浏览', 'download': '📥 文件下载'}.get(cls, cls)
            qos = {'video': '⬆ 高优先级 无限制',
                   'web': '→ 中优先级',
                   'download': '⬇ 限速 10Mbps'}.get(cls, '?')
            print(f"  │ 端口{port:<4} {icon:<12} {qos:<20} │")
        print(f"  └──────────────────────────────────────────────────┘")

    # 最近分类日志
    if log:
        print(f"\n  ┌── 最近分类事件 ──────────────────────────────────┐")
        print(f"  │ {'时间':<10} {'端口':<6} {'分类':<10} {'置信度':<8} │")
        print(f"  │ {'-'*38} │")
        for entry in log[-8:]:
            cls_icon = {'video': '📹', 'web': '🌐', 'download': '📥'}.get(entry['class'], '?')
            print(f"  │ {entry['time']:<10} 端口{str(entry['port']):<4} {cls_icon} {entry['class']:<7} {entry['confidence']*100:>6.1f}% │")
        print(f"  └──────────────────────────────────────────────────┘")

    # 图例
    print(f"""
  ┌── 实验拓扑 ───────────────────────────────────────┐
  │   h1 (10.0.0.1) ─┐                                │
  │     📹 视频流     ├── s1 (OVS) ── h4 (10.0.0.4)   │
  │   h2 (10.0.0.2) ─┤        ↑         服务器         │
  │     🌐 网页浏览   │    Ryu+AI                      │
  │   h3 (10.0.0.3) ─┘                                │
  │     📥 文件下载                                     │
  └────────────────────────────────────────────────────┘

  QoS 策略:
    📹 视频流 → 高优先级 (无速率限制)
    🌐 网页浏览 → 中优先级
    📥 文件下载 → 限速 10Mbps (保障视频带宽)

  [Ctrl+C] 退出
""")

    model = data.get('model', {})
    if model:
        print(f"  AI 模型: {model.get('type', '?')} | 准确率: {model.get('accuracy', 0)*100:.0f}%")
        print(f"  分类: {model.get('classes', [])}")


def main():
    print("等待 Ryu 控制器数据...\n")

    last_update = 0
    while True:
        try:
            if os.path.exists(RESULT_FILE):
                mtime = os.path.getmtime(RESULT_FILE)
                if mtime > last_update:
                    with open(RESULT_FILE) as f:
                        data = json.load(f)
                    print_dashboard(data)
                    last_update = mtime
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n退出")
            sys.exit(0)
        except Exception as e:
            time.sleep(1)


if __name__ == '__main__':
    main()
