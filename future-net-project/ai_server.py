#!/usr/bin/env python3
"""
AI 推理微服务 — 独立 Flask API
Ryu 控制器通过 HTTP POST 调用此服务进行流量分类

启动: python3 /root/future-net-project/ai_server.py
端口: 5001
"""
import pickle
import os
import sys
import numpy as np
from flask import Flask, request, jsonify

MODEL_DIR = '/root/future-net-project/ai/models'

app = Flask(__name__)

# 启动时加载模型
try:
    with open(os.path.join(MODEL_DIR, 'rf_model.pkl'), 'rb') as f:
        model = pickle.load(f)
    with open(os.path.join(MODEL_DIR, 'scaler.pkl'), 'rb') as f:
        scaler = pickle.load(f)
    with open(os.path.join(MODEL_DIR, 'model_meta.pkl'), 'rb') as f:
        meta = pickle.load(f)
    class_names = meta['class_names']
    print(f"[AI Server] 模型已加载: RF {meta['rf_accuracy']*100:.0f}%")
    print(f"[AI Server] 分类: {class_names}")
    print(f"[AI Server] 数据来源: {meta.get('data_source', 'synthetic')}")
except Exception as e:
    print(f"[AI Server] 模型加载失败: {e}")
    print(f"[AI Server] 请先运行: python3 train_model.py")
    sys.exit(1)

request_count = 0


@app.route('/')
def index():
    return jsonify({
        'service': 'SDN Traffic Classification AI',
        'model': 'Random Forest',
        'accuracy': float(meta['rf_accuracy']),
        'classes': class_names,
        'features': meta['n_features'],
        'requests_served': request_count,
    })


@app.route('/predict', methods=['POST'])
def predict():
    """接收 10 维特征向量，返回分类结果"""
    global request_count
    try:
        data = request.get_json()
        if not data or 'features' not in data:
            return jsonify({'error': '缺少 features 字段'}), 400

        features = np.array(data['features']).reshape(1, -1)
        if features.shape[1] != meta['n_features']:
            return jsonify({'error': f'需要 {meta["n_features"]} 维特征，收到 {features.shape[1]} 维'}), 400

        # 标准化 + 推理
        scaled = scaler.transform(features)
        pred = int(model.predict(scaled)[0])
        proba = model.predict_proba(scaled)[0]
        confidence = float(proba.max())

        request_count += 1
        result = {
            'class': class_names[pred],
            'class_id': pred,
            'confidence': round(confidence, 4),
            'probabilities': {
                class_names[i]: round(float(proba[i]), 4)
                for i in range(len(class_names))
            },
            'request_id': request_count,
        }
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'model_loaded': True})


if __name__ == '__main__':
    print(f"[AI Server] 启动在 http://0.0.0.0:5001")
    print(f"[AI Server] API: POST /predict  GET /health  GET /")
    app.run(host='0.0.0.0', port=5001, debug=False)
