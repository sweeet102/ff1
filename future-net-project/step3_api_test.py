#!/usr/bin/env python3
"""
步骤3: AI API 直接测试 + 结果汇总
前提: AI Server 在运行 (ai_server.py)
用法: python3 step3_api_test.py
"""
import requests
import json
import os

print("""
============================================================
  步骤3: AI 推理 API 测试
============================================================
""")

# 1. 查看 AI 服务信息
print("--- AI 服务信息 ---")
r = requests.get('http://127.0.0.1:5001/', timeout=2)
info = r.json()
print(f"  服务: {info['service']}")
print(f"  模型: {info['model']}")
print(f"  准确率: {info['accuracy']*100:.0f}%")
print(f"  分类: {info['classes']}")
print(f"  已处理请求: {info['requests_served']}")

# 2. 测试 3 种流量分类
print("\n--- 单次推理测试 ---")

# 这些特征是真实的 OVS 端口统计数据格式
tests = [
    ("视频流", [400, 480000, 3, 192, 180.0, 192000.0, 1200.0, 1.5, 2000.0, 100.0]),
    ("网页浏览", [60, 33000, 45, 22500, 30.0, 16500.0, 550.0, 22.5, 2000.0, 1.3]),
    ("文件下载", [150, 9600, 800, 1120000, 80.0, 4800.0, 64.0, 400.0, 2000.0, 0.19]),
]

for label, feats in tests:
    r = requests.post('http://127.0.0.1:5001/predict',
                      json={'features': feats}, timeout=2)
    result = r.json()
    print(f"  {label:<8} → {result['class']:<10} "
          f"置信度 {result['confidence']*100:.0f}%  "
          f"请求#{result['request_id']}")

# 3. 查看实验数据
print("\n--- 实验数据 ---")
try:
    with open('/tmp/qos_results.json') as f:
        data = json.load(f)
    pc = data.get('port_classes', {})
    log = data.get('log', [])
    print(f"  分类端口数: {len(pc)}")
    print(f"  记录数: {len(log)}")
    print(f"  API 累计请求: {data.get('api_requests', 0)}")
    if log:
        print(f"  最后一条: {log[-1]['time']} 端口{log[-1]['port']} → {log[-1]['class']} "
              f"置信度{log[-1]['confidence']*100:.0f}%")
except Exception:
    print("  暂无实验数据")

print("\n步骤3 完成。")
