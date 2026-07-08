#!/bin/bash
# 未来网络技术课程实践：一键运行完整演示
# 在 Docker 容器内运行: bash /root/future-net-project/run_demo.sh
# 用法（从主机）: docker exec future-net-lab bash /root/future-net-project/run_demo.sh [full|normal|attack]

set -e

PROJECT_DIR="/root/future-net-project"
RESULTS_DIR="$PROJECT_DIR/results"
MODE="${1:-full}"

echo "============================================"
echo "  未来网络技术课程实践"
echo "  SDN + P4 + AI 智能异常检测与防御系统"
echo "============================================"
echo ""

# 初始化 OVS
service openvswitch-switch start 2>/dev/null || true
echo "[OK] OVS 服务已启动"

# 创建结果目录
mkdir -p "$RESULTS_DIR" /tmp/shared

# 检查模型文件
if [ ! -f "$PROJECT_DIR/ai/models/rf_model.pkl" ]; then
    echo "[WARN] AI 模型文件不存在，开始训练..."
    python3 "$PROJECT_DIR/ai/train_model.py"
fi

echo ""
echo "================================================"
echo "  启动 3 个终端窗口分别运行："
echo "================================================"
echo ""
echo "  窗口1 (Ryu SDN 控制器):"
echo "    ryu-manager $PROJECT_DIR/controller/ryu_anomaly_detector.py"
echo ""
echo "  窗口2 (Mininet 拓扑 + 流量):"
echo "    python3 $PROJECT_DIR/topology/net_topo.py $MODE"
echo ""
echo "  窗口3 (REST API 监控):"
echo "    watch -n 2 'curl -s http://127.0.0.1:8080/stats | python3 -m json.tool'"
echo ""
echo "================================================"
echo ""

# 自动运行模式（当用户选择直接执行时）
if [ "$MODE" = "auto" ]; then
    echo "[自动模式] 启动 Ryu 控制器 + Mininet 拓扑..."

    # 启动 Ryu 控制器（后台）
    echo "  启动 Ryu SDN 控制器..."
    ryu-manager --verbose "$PROJECT_DIR/controller/ryu_anomaly_detector.py" &
    RYU_PID=$!
    sleep 5

    # 检查 Ryu 是否启动
    if kill -0 $RYU_PID 2>/dev/null; then
        echo "  Ryu 控制器已启动 (PID: $RYU_PID)"
    else
        echo "  [ERROR] Ryu 控制器启动失败"
        exit 1
    fi

    # 运行 Mininet 拓扑
    echo "  运行 Mininet 拓扑..."
    python3 "$PROJECT_DIR/topology/net_topo.py" full

    # 清理
    kill $RYU_PID 2>/dev/null || true
    echo "  演示完成"
fi

# 导出结果到共享目录
if [ -d "$RESULTS_DIR" ]; then
    cp -r "$RESULTS_DIR"/* /tmp/shared/ 2>/dev/null || true
    echo "[OK] 结果已导出到 /tmp/shared/"
fi

echo ""
echo "结果文件位置:"
echo "  容器内: $RESULTS_DIR/"
echo "  主机: $(dirname "$PROJECT_DIR")/results/ (通过 volume 挂载)"
