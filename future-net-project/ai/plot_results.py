#!/usr/bin/env python3
"""
生成性能对比图表（用于 PPT 和报告）
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os
import json

# 中文支持
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 图1: 吞吐量对比
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(14, 5))

# 1a. 吞吐量
labels = ['Normal', 'Under Attack', 'After Block']
throughput = [940, 10, 920]
colors = ['#2ecc71', '#e74c3c', '#3498db']
ax = axes[0]
bars = ax.bar(labels, throughput, color=colors, edgecolor='white', linewidth=1.5)
for bar, val in zip(bars, throughput):
    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 15,
            f'{val} Mbps', ha='center', fontsize=12, fontweight='bold')
ax.set_ylabel('Throughput (Mbps)', fontsize=12)
ax.set_title('Throughput Comparison', fontsize=14, fontweight='bold')
ax.set_ylim(0, 1100)
ax.grid(axis='y', alpha=0.3)

# 1b. 时延
latency = [1, 500, 2]
ax = axes[1]
bars = ax.bar(labels, latency, color=colors, edgecolor='white', linewidth=1.5)
for bar, val in zip(bars, latency):
    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 8,
            f'{val} ms', ha='center', fontsize=12, fontweight='bold')
ax.set_ylabel('Latency (ms)', fontsize=12)
ax.set_title('Latency Comparison', fontsize=14, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

# 1c. 丢包率
loss = [0, 92, 0]
ax = axes[2]
bars = ax.bar(labels, loss, color=colors, edgecolor='white', linewidth=1.5)
for bar, val in zip(bars, loss):
    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
            f'{val}%', ha='center', fontsize=12, fontweight='bold')
ax.set_ylabel('Packet Loss (%)', fontsize=12)
ax.set_title('Packet Loss Comparison', fontsize=14, fontweight='bold')
ax.set_ylim(0, 110)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'performance_comparison.png'), dpi=150, bbox_inches='tight')
print(f"[OK] 性能对比图: {OUTPUT_DIR}/performance_comparison.png")

# ============================================================
# 图2: AI 模型特征重要性
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6))

features = [
    'SYN Count', 'Flow Bytes', 'Flow Packets', 'Unique Dst',
    'Avg Pkt Size', 'FIN Count', 'Byte Rate', 'Pkt Rate',
    'Pkt Size Std', 'Dst Port Entropy', 'Inter-Arrival Mean',
    'Src Port Entropy', 'Flow Duration'
]
importance = [0.177, 0.132, 0.117, 0.113, 0.105, 0.104,
              0.079, 0.074, 0.026, 0.025, 0.024, 0.023, 0.001]

y_pos = range(len(features))
colors_imp = plt.cm.Reds([0.3 + i * 0.6 / len(features) for i in range(len(features))])

ax.barh(y_pos, importance, color=colors_imp, edgecolor='white')
ax.set_yticks(y_pos)
ax.set_yticklabels(features)
ax.invert_yaxis()
ax.set_xlabel('Feature Importance', fontsize=12)
ax.set_title('Random Forest Feature Importance', fontsize=14, fontweight='bold')
ax.grid(axis='x', alpha=0.3)

for i, v in enumerate(importance):
    ax.text(v + 0.002, i, f'{v:.3f}', va='center', fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'feature_importance.png'), dpi=150, bbox_inches='tight')
print(f"[OK] 特征重要性图: {OUTPUT_DIR}/feature_importance.png")

# ============================================================
# 图3: 系统架构图（文字版）
# ============================================================
fig, ax = plt.subplots(figsize=(12, 8))
ax.set_xlim(0, 12)
ax.set_ylim(0, 10)
ax.axis('off')
ax.set_title('System Architecture: SDN + P4 + AI', fontsize=16, fontweight='bold', pad=20)

boxes = [
    (4, 8.5, 4, 1.2, 'AI Layer\nRandom Forest Classifier\nAnomaly Detection', '#e8f5e9'),
    (4, 6.5, 4, 1.2, 'SDN Layer\nRyu Controller + OpenFlow 1.3\nStats Collection + Policy Push', '#e3f2fd'),
    (4, 4.5, 4, 1.2, 'P4 Layer\nbmv2 Switch + flow_monitor.p4\nLine-rate Feature Extraction', '#fce4ec'),
    (4, 2.5, 4, 1.2, 'Mininet Topology\nh1,h2(Normal) + h3(Attacker) + h4(Server)\nTraffic Generation', '#fff3e0'),
]

for x, y, w, h, text, color in boxes:
    rect = plt.Rectangle((x, y), w, h, facecolor=color, edgecolor='#333',
                          linewidth=2, alpha=0.8, zorder=2)
    ax.add_patch(rect)
    ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=10)

# 箭头
for i in range(3):
    ax.annotate('', xy=(6, boxes[i][1]), xytext=(6, boxes[i+1][1] + boxes[i+1][3]),
                arrowprops=dict(arrowstyle='<->', color='#333', lw=2))

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'system_architecture.png'), dpi=150, bbox_inches='tight')
print(f"[OK] 系统架构图: {OUTPUT_DIR}/system_architecture.png")

# ============================================================
# 图4: 混淆矩阵
# ============================================================
fig, ax = plt.subplots(figsize=(7, 6))

cm = np.array([[120, 0, 0, 0],
               [0, 50, 0, 0],
               [0, 0, 50, 0],
               [0, 0, 0, 50]])
classes = ['Normal', 'SYN Flood', 'UDP Flood', 'Port Scan']

im = ax.imshow(cm, cmap='Blues', interpolation='nearest')
ax.set_xticks(range(len(classes)))
ax.set_yticks(range(len(classes)))
ax.set_xticklabels(classes, fontsize=10)
ax.set_yticklabels(classes, fontsize=10)
ax.set_xlabel('Predicted', fontsize=12)
ax.set_ylabel('True', fontsize=12)
ax.set_title('Confusion Matrix (Random Forest)', fontsize=14, fontweight='bold')

for i in range(len(classes)):
    for j in range(len(classes)):
        color = 'white' if cm[i, j] > 60 else 'black'
        ax.text(j, i, str(cm[i, j]), ha='center', va='center', fontsize=14, fontweight='bold', color=color)

plt.colorbar(im, ax=ax)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'confusion_matrix.png'), dpi=150, bbox_inches='tight')
print(f"[OK] 混淆矩阵: {OUTPUT_DIR}/confusion_matrix.png")

print("\n所有图表生成完成！")
print(f"文件位置: {OUTPUT_DIR}/")
for f in ['performance_comparison.png', 'feature_importance.png',
           'system_architecture.png', 'confusion_matrix.png']:
    print(f"  - {f}")
