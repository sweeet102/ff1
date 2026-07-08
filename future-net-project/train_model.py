#!/usr/bin/env python3
"""
AI 流量分类模型训练 v2
优先使用真实采集数据（collect_data.py 输出），无真实数据时用合成数据
"""
import json
import os
import sys
import pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import StandardScaler

np.random.seed(42)

PROJECT = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(PROJECT, 'ai', 'models')
DATA_FILE = os.path.join(PROJECT, 'ai', 'training_data.json')

FEATURE_NAMES = [
    'rx_packets', 'rx_bytes', 'tx_packets', 'tx_bytes',
    'pkt_rate', 'byte_rate', 'avg_pkt_size',
    'tx_pkt_rate', 'interval_ms', 'rx_tx_ratio'
]
CLASS_NAMES = ['video', 'web', 'download']


def load_real_data():
    """加载真实采集数据，转为特征矩阵"""
    if not os.path.exists(DATA_FILE):
        return None, None

    with open(DATA_FILE) as f:
        raw = json.load(f)

    X, y = [], []
    label_map = {name: i for i, name in enumerate(CLASS_NAMES)}

    for label, entry in raw:
        if label not in label_map:
            continue
        try:
            feat = [
                entry.get('rx_packets', entry.get('pkt_rate', 0) * 2),
                entry.get('rx_bytes', entry.get('pkt_rate', 0) * entry.get('avg_pkt_size', 800)),
                entry.get('tx_packets', 1),
                entry.get('tx_bytes', 64),
                entry.get('pkt_rate', 0),
                entry.get('pkt_rate', 0) * entry.get('avg_pkt_size', 800) / 8,
                entry.get('avg_pkt_size', 800),
                entry.get('tx_pkt_rate', 0),
                entry.get('interval_ms', 2000),
                entry.get('rx_tx_ratio', 10),
            ]
            X.append(feat)
            y.append(label_map[label])
        except Exception:
            continue

    if len(X) < 10:
        return None, None

    print(f"  加载真实数据: {len(X)} 条")
    for i, cls in enumerate(CLASS_NAMES):
        print(f"    {cls}: {y.count(i)} 条")
    return np.array(X), np.array(y)


def generate_synthetic_data():
    """合成数据（当真实数据不足时使用）"""
    print("  使用合成数据生成训练集...")

    def gen(cls_name, n):
        data = []
        for _ in range(n):
            if cls_name == 'video':
                rx_pkts = int(np.random.normal(400, 80))
                avg_sz = np.random.normal(1200, 80)
                pkt_rate = np.random.normal(180, 30)
                tx_pkts = int(np.random.poisson(3))
                tx_pkt_rate = tx_pkts / 2.0
                rx_tx = rx_pkts / max(tx_pkts, 1)
            elif cls_name == 'web':
                rx_pkts = int(np.random.normal(60, 30))
                avg_sz = np.random.normal(550, 200)
                pkt_rate = np.random.normal(30, 15)
                tx_pkts = int(np.random.normal(40, 15))
                tx_pkt_rate = tx_pkts / 2.0
                rx_tx = rx_pkts / max(tx_pkts, 1)
            else:  # download
                rx_pkts = int(np.random.normal(150, 50))
                avg_sz = 64  # ACK 小包
                pkt_rate = np.random.normal(80, 30)
                tx_pkts = int(np.random.normal(800, 200))
                tx_pkt_rate = np.random.normal(400, 100)
                rx_tx = rx_pkts / max(tx_pkts, 1)

            rx_bytes = int(rx_pkts * avg_sz)
            tx_bytes = int(tx_pkts * 64)
            interval = np.random.uniform(1800, 2500)

            data.append([
                rx_pkts, rx_bytes, tx_pkts, tx_bytes,
                pkt_rate, rx_bytes / max(interval / 1000, 0.1), avg_sz,
                tx_pkt_rate, interval, min(rx_tx, 100)
            ])
        return np.array(data)

    X_v = gen('video', 300)
    X_w = gen('web', 300)
    X_d = gen('download', 300)
    X = np.vstack([X_v, X_w, X_d])
    y = np.hstack([np.zeros(300, dtype=int),
                   np.ones(300, dtype=int),
                   np.full(300, 2, dtype=int)])
    return X, y


def main():
    print("=" * 55)
    print("  AI 流量分类模型训练")
    print("=" * 55)

    # 1. 加载数据
    print("\n[1/5] 加载训练数据...")
    X, y = load_real_data()
    if X is None:
        X, y = generate_synthetic_data()

    print(f"  总样本: {len(X)}")
    for i, cls in enumerate(CLASS_NAMES):
        cnt = np.sum(y == i)
        if cnt > 0:
            print(f"    {cls}: {cnt} 条")

    # 2. 划分 + 标准化
    print("\n[2/5] 数据预处理...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # 3. 训练
    print("\n[3/5] 训练 Random Forest...")
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=15, min_samples_split=5,
        class_weight='balanced', random_state=42, n_jobs=-1
    )
    rf.fit(X_train_s, y_train)
    rf_pred = rf.predict(X_test_s)
    rf_acc = accuracy_score(y_test, rf_pred)
    print(f"  准确率: {rf_acc*100:.2f}%")

    # 4. 评估
    print("\n[4/5] 评估报告...")
    print("\n" + classification_report(y_test, rf_pred, target_names=CLASS_NAMES, digits=3))

    cm = confusion_matrix(y_test, rf_pred)
    print("混淆矩阵:")
    print(f"{'':>12}{CLASS_NAMES[0]:>10}{CLASS_NAMES[1]:>10}{CLASS_NAMES[2]:>10}")
    for i, cls in enumerate(CLASS_NAMES):
        print(f"  {cls:>10}{cm[i][0]:>10}{cm[i][1]:>10}{cm[i][2]:>10}")

    cv = cross_val_score(rf, X_train_s, y_train, cv=5)
    print(f"\n  5-fold CV: {cv.mean():.4f} (+/- {cv.std()*2:.4f})")

    print("\n  特征重要性:")
    for i in np.argsort(rf.feature_importances_)[::-1]:
        print(f"    {FEATURE_NAMES[i]:>20s}: {rf.feature_importances_[i]:.4f}")

    # 5. 保存
    print("\n[5/5] 导出模型...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(os.path.join(MODEL_DIR, 'rf_model.pkl'), 'wb') as f:
        pickle.dump(rf, f)
    with open(os.path.join(MODEL_DIR, 'scaler.pkl'), 'wb') as f:
        pickle.dump(scaler, f)
    with open(os.path.join(MODEL_DIR, 'model_meta.pkl'), 'wb') as f:
        pickle.dump({
            'feature_names': FEATURE_NAMES,
            'class_names': CLASS_NAMES,
            'n_features': len(FEATURE_NAMES),
            'rf_accuracy': rf_acc,
            'cv_mean': cv.mean(),
            'data_source': 'real' if X is not None else 'synthetic',
        }, f)

    print(f"  模型已保存到 {MODEL_DIR}/")
    print(f"    rf_model.pkl      Random Forest {rf_acc*100:.1f}%")
    print(f"    scaler.pkl        标准化器")
    print(f"    model_meta.pkl    元数据")
    print(f"\n  数据来源: {'真实采集' if os.path.exists(DATA_FILE) else '合成数据'}")
    print("\n训练完成！")


if __name__ == '__main__':
    main()
