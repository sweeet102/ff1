#!/usr/bin/env python3
"""
未来网络技术课程实践：AI 异常流量检测模型训练
基于流统计特征的随机森林 + MLP 分类器
"""

import numpy as np
import pandas as pd
import pickle
import os
import sys
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import StandardScaler

# ============================================================
# 1. 生成合成流量特征数据集
# ============================================================
# 特征说明（每条流统计）：
#   [0]  flow_pkt_count       - 流的包数
#   [1]  flow_byte_count      - 流的字节数
#   [2]  flow_duration_ms     - 流持续时间(ms)
#   [3]  pkt_rate             - 包速率 (pps)
#   [4]  byte_rate            - 字节速率 (bps)
#   [5]  avg_pkt_size         - 平均包大小
#   [6]  syn_count            - SYN 标志计数
#   [7]  fin_count            - FIN 标志计数
#   [8]  src_port_entropy     - 源端口熵 (归一化)
#   [9]  dst_port_entropy     - 目的端口熵 (归一化)
#   [10] unique_dst_count     - 连接的不同目的IP数
#   [11] pkt_size_std         - 包大小标准差
#   [12] inter_arrival_mean   - 平均到达间隔(ms)
#
# 类别：
#   0 - normal   正常流量
#   1 - syn_flood SYN洪水攻击
#   2 - udp_flood UDP洪水攻击
#   3 - port_scan 端口扫描

np.random.seed(42)

def generate_normal_flow(n_samples=500):
    """正常流量：中等速率，多种协议，多种端口"""
    data = []
    for _ in range(n_samples):
        pkt_count = int(np.random.normal(50, 30))
        pkt_count = max(5, min(pkt_count, 500))
        avg_size = np.random.normal(800, 300)
        avg_size = max(64, min(avg_size, 1500))
        byte_count = int(pkt_count * avg_size)
        duration = np.random.exponential(2000) + 200
        pkt_rate = pkt_count / (duration / 1000) if duration > 0 else pkt_count

        data.append([
            pkt_count,
            byte_count,
            duration,
            pkt_rate,
            pkt_rate * avg_size / 8,
            avg_size,
            np.random.poisson(1),           # syn_count 少量SYN
            np.random.poisson(1),           # fin_count 少量FIN
            np.random.beta(2, 2),           # src_port_entropy 适中
            np.random.beta(3, 5),           # dst_port_entropy 低（访问少量服务）
            np.random.poisson(2),           # unique_dst_count
            np.random.exponential(100),     # pkt_size_std
            np.random.exponential(20)       # inter_arrival_mean
        ])
    return np.array(data), np.zeros(n_samples, dtype=int)

def generate_syn_flood(n_samples=200):
    """SYN洪水：极高包速率，大量SYN，小包，源端口多样化"""
    data = []
    for _ in range(n_samples):
        pkt_count = int(np.random.uniform(500, 5000))
        avg_size = np.random.normal(64, 10)
        avg_size = max(40, min(avg_size, 100))
        byte_count = int(pkt_count * avg_size)
        duration = np.random.exponential(500) + 50
        pkt_rate = pkt_count / (duration / 1000) if duration > 0 else pkt_count

        data.append([
            pkt_count,
            byte_count,
            duration,
            pkt_rate,                        # 极高包速率
            pkt_rate * avg_size / 8,
            avg_size,                        # 小包
            pkt_count * 0.95,                # syn_count ≈ 包数 (几乎全是SYN)
            0,                               # fin_count ≈ 0
            np.random.beta(5, 1),            # src_port_entropy 高 (伪造源端口)
            np.random.beta(1, 8),            # dst_port_entropy 极低 (攻击同一端口)
            np.random.poisson(1),            # unique_dst_count 少
            np.random.uniform(0, 30),        # pkt_size_std 小 (包大小一致)
            np.random.exponential(0.5)       # inter_arrival_mean 极小
        ])
    return np.array(data), np.ones(n_samples, dtype=int)

def generate_udp_flood(n_samples=200):
    """UDP洪水：高包速率，大包，固定目标"""
    data = []
    for _ in range(n_samples):
        pkt_count = int(np.random.uniform(300, 3000))
        avg_size = np.random.normal(1200, 100)
        avg_size = max(500, min(avg_size, 1500))
        byte_count = int(pkt_count * avg_size)
        duration = np.random.exponential(1000) + 100
        pkt_rate = pkt_count / (duration / 1000) if duration > 0 else pkt_count

        data.append([
            pkt_count,
            byte_count,
            duration,
            pkt_rate,                        # 高包速率
            pkt_rate * avg_size / 8,
            avg_size,                        # 大包
            0,                               # syn_count = 0 (UDP无SYN)
            0,                               # fin_count = 0
            np.random.beta(1, 8),            # src_port_entropy 低
            np.random.beta(1, 10),           # dst_port_entropy 极低
            np.random.poisson(1),
            np.random.uniform(50, 200),      # pkt_size_std 中等
            np.random.exponential(0.3)       # inter_arrival_mean 小
        ])
    return np.array(data), np.full(n_samples, 2, dtype=int)

def generate_port_scan(n_samples=200):
    """端口扫描：连接大量不同端口，低字节量"""
    data = []
    for _ in range(n_samples):
        pkt_count = int(np.random.uniform(100, 500))
        avg_size = np.random.normal(60, 10)
        avg_size = max(40, min(avg_size, 80))
        byte_count = int(pkt_count * avg_size)
        duration = np.random.exponential(3000) + 500
        pkt_rate = pkt_count / (duration / 1000) if duration > 0 else pkt_count

        data.append([
            pkt_count,
            byte_count,
            duration,
            pkt_rate,
            pkt_rate * avg_size / 8,
            avg_size,                        # 小包
            60,                              # 大量SYN (尝试连接)
            30,                              # 有FIN (关闭连接)
            np.random.beta(1, 5),            # src_port_entropy 低
            np.random.beta(5, 1),            # dst_port_entropy 极高 (扫描多端口)
            np.random.randint(20, 100),      # unique_dst_count 大量
            np.random.uniform(5, 30),        # pkt_size_std
            np.random.exponential(2)         # inter_arrival_mean
        ])
    return np.array(data), np.full(n_samples, 3, dtype=int)

# ============================================================
# 2. 数据集构建
# ============================================================
print("=" * 60)
print("未来网络技术课程实践 - AI 异常流量检测模型")
print("=" * 60)

print("\n[1/5] 生成训练数据集...")
X_n, y_n = generate_normal_flow(600)
X_s, y_s = generate_syn_flood(250)
X_u, y_u = generate_udp_flood(250)
X_p, y_p = generate_port_scan(250)

X = np.vstack([X_n, X_s, X_u, X_p])
y = np.hstack([y_n, y_s, y_u, y_p])

feature_names = [
    'flow_pkt_count', 'flow_byte_count', 'flow_duration_ms',
    'pkt_rate', 'byte_rate', 'avg_pkt_size',
    'syn_count', 'fin_count', 'src_port_entropy',
    'dst_port_entropy', 'unique_dst_count', 'pkt_size_std',
    'inter_arrival_mean'
]

class_names = ['normal', 'syn_flood', 'udp_flood', 'port_scan']

print(f"  总样本: {len(X)}")
for i, cls in enumerate(class_names):
    print(f"    {cls}: {np.sum(y == i)} 条")

# 划分训练/测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ============================================================
# 3. 模型训练
# ============================================================
print("\n[2/5] 训练 Random Forest 模型...")
rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    min_samples_split=5,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)
rf.fit(X_train_scaled, y_train)
rf_pred = rf.predict(X_test_scaled)
rf_acc = accuracy_score(y_test, rf_pred)
print(f"  Random Forest 准确率: {rf_acc:.4f} ({rf_acc*100:.2f}%)")

print("\n[3/5] 训练 MLP 神经网络模型...")
mlp = MLPClassifier(
    hidden_layer_sizes=(64, 32, 16),
    activation='relu',
    solver='adam',
    max_iter=500,
    early_stopping=True,
    validation_fraction=0.1,
    random_state=42
)
mlp.fit(X_train_scaled, y_train)
mlp_pred = mlp.predict(X_test_scaled)
mlp_acc = accuracy_score(y_test, mlp_pred)
print(f"  MLP 准确率: {mlp_acc:.4f} ({mlp_acc*100:.2f}%)")

# ============================================================
# 4. 模型评估
# ============================================================
print("\n[4/5] 模型评估报告...")

print("\n--- Random Forest ---")
print(classification_report(y_test, rf_pred, target_names=class_names, digits=4))
print("混淆矩阵:")
cm = confusion_matrix(y_test, rf_pred)
print(f"{'':>12} {'normal':>8} {'syn_flood':>10} {'udp_flood':>10} {'port_scan':>11}")
for i, cls in enumerate(class_names):
    print(f"  {cls:>10} {cm[i][0]:>8} {cm[i][1]:>10} {cm[i][2]:>10} {cm[i][3]:>11}")

print("\n--- MLP Neural Network ---")
print(classification_report(y_test, mlp_pred, target_names=class_names, digits=4))

# 交叉验证
print("\n  交叉验证 (5-fold):")
rf_cv = cross_val_score(rf, X_train_scaled, y_train, cv=5)
mlp_cv = cross_val_score(mlp, X_train_scaled, y_train, cv=5)
print(f"    Random Forest: {rf_cv.mean():.4f} (+/- {rf_cv.std()*2:.4f})")
print(f"    MLP:           {mlp_cv.mean():.4f} (+/- {mlp_cv.std()*2:.4f})")

# 特征重要性
print("\n--- 特征重要性 (Random Forest) ---")
importances = rf.feature_importances_
indices = np.argsort(importances)[::-1]
for i in indices:
    print(f"  {feature_names[i]:>22s}: {importances[i]:.4f}")

# ============================================================
# 5. 保存模型
# ============================================================
print("\n[5/5] 导出模型文件...")

model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
os.makedirs(model_dir, exist_ok=True)

# 保存 Random Forest（推荐，准确率高且稳定）
with open(os.path.join(model_dir, 'rf_model.pkl'), 'wb') as f:
    pickle.dump(rf, f)

# 保存 MLP
with open(os.path.join(model_dir, 'mlp_model.pkl'), 'wb') as f:
    pickle.dump(mlp, f)

# 保存 Scaler（重要！推理时必须用同样的 scaler）
with open(os.path.join(model_dir, 'scaler.pkl'), 'wb') as f:
    pickle.dump(scaler, f)

# 保存元数据
meta = {
    'feature_names': feature_names,
    'class_names': class_names,
    'n_features': len(feature_names),
    'rf_accuracy': rf_acc,
    'mlp_accuracy': mlp_acc,
    'scaler_mean': scaler.mean_.tolist(),
    'scaler_scale': scaler.scale_.tolist(),
}
with open(os.path.join(model_dir, 'model_meta.pkl'), 'wb') as f:
    pickle.dump(meta, f)

print(f"\n  模型文件保存在: {model_dir}/")
print(f"    - rf_model.pkl    (Random Forest: {rf_acc*100:.1f}%)")
print(f"    - mlp_model.pkl   (MLP Neural Net: {mlp_acc*100:.1f}%)")
print(f"    - scaler.pkl      (特征标准化器)")
print(f"    - model_meta.pkl  (模型元数据)")

# 选择最佳模型
best = 'rf' if rf_acc >= mlp_acc else 'mlp'
print(f"\n  推荐使用: {'Random Forest' if best == 'rf' else 'MLP'} 模型用于在线推理")

# ============================================================
# 6. 推理示例
# ============================================================
print("\n" + "=" * 60)
print("推理示例测试")
print("=" * 60)

def test_inference(scaler, model, class_names, features, label):
    """单条推理测试"""
    scaled = scaler.transform([features])
    pred = model.predict(scaled)[0]
    proba = model.predict_proba(scaled)[0]
    return pred, proba

print("\n  测试样本推理结果:")
print(f"  {'样本类型':<12} {'预测':<12} {'置信度':>8}")
print(f"  {'-'*40}")

test_samples = [
    (generate_normal_flow(1)[0][0], 0, "正常流量"),
    (generate_syn_flood(1)[0][0], 1, "SYN洪水"),
    (generate_udp_flood(1)[0][0], 2, "UDP洪水"),
    (generate_port_scan(1)[0][0], 3, "端口扫描"),
]

for features, true_label, desc in test_samples:
    pred, proba = test_inference(scaler, rf, class_names, features, true_label)
    correct = "✓" if pred == true_label else "✗"
    print(f"  {desc:<12} {class_names[pred]:<12} {max(proba)*100:>7.1f}% {correct}")

print("\n模型训练完成！")
