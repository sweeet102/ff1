#!/bin/bash
# 未来网络技术课程实践：环境搭建脚本
# 复用现有 sdn-lab 镜像，仅安装 sklearn/numpy 即可
# 用法：bash setup_env.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
IMAGE_NAME="sdn-lab:latest"
CONTAINER_NAME="future-net-lab"

echo "============================================"
echo "  未来网络技术课程实践 - 环境搭建"
echo "  复用现有镜像: ${IMAGE_NAME}"
echo "============================================"

if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker 未运行，请先启动 Docker Desktop"
    exit 1
fi

# 验证镜像存在
if ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${IMAGE_NAME}$"; then
    echo "[ERROR] 镜像 ${IMAGE_NAME} 不存在"
    echo "  可用镜像:"
    docker images --format '  {{.Repository}}:{{.Tag}} ({{.Size}})'
    exit 1
fi

echo ""
echo "  镜像: ${IMAGE_NAME} $(docker images --format '{{.Size}}' ${IMAGE_NAME})"
echo ""

# 启动容器
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

docker run -d \
    --name "$CONTAINER_NAME" \
    --privileged \
    -p 6653:6653 \
    -p 8080:8080 \
    -v "$PROJECT_DIR":/root/future-net-project \
    "$IMAGE_NAME" \
    sleep infinity

echo "  容器已启动: $CONTAINER_NAME"
sleep 2

# 初始化 OVS 并安装缺失的 Python 包
echo ""
echo "  初始化 OVS 并安装 Python ML 包..."
docker exec "$CONTAINER_NAME" bash -c '
    service openvswitch-switch start 2>/dev/null || true

    # 只安装缺失的包
    pip3 install --no-cache-dir scikit-learn numpy pandas joblib 2>&1 | tail -3

    echo ""
    echo "--- 环境验证 ---"
    echo -n "Mininet:  "; mn --version 2>&1 | head -1
    echo -n "Ryu:      "; python3 -c "import ryu; print(ryu.__version__)" 2>&1 | tail -1
    echo -n "sklearn:  "; python3 -c "import sklearn; print(sklearn.__version__)" 2>&1
    echo -n "numpy:    "; python3 -c "import numpy; print(numpy.__version__)" 2>&1
    echo -n "P4:       "; which simple_switch 2>&1
    echo -n "hping3:   "; which hping3 2>&1 || echo "N/A"
'

echo ""
echo "============================================"
echo "  环境就绪！"
echo "============================================"
echo ""
echo "运行实验（3个终端窗口）："
echo ""
echo "  窗口1 - Ryu 控制器："
echo "    docker exec -it $CONTAINER_NAME ryu-manager /root/future-net-project/controller/ryu_anomaly_detector.py"
echo ""
echo "  窗口2 - Mininet 拓扑 + 流量："
echo "    docker exec -it $CONTAINER_NAME python3 /root/future-net-project/topology/net_topo.py full"
echo ""
echo "  窗口3 - REST API 监控："
echo "    docker exec -it $CONTAINER_NAME watch -n 2 '\''curl -s http://127.0.0.1:8080/stats'\'''
echo ""
