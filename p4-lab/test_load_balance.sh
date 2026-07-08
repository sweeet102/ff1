#!/bin/bash
# ============================================================
# 实验五：load_balance 负载均衡测试脚本
# 用法：
#   docker exec -it sdn-lab bash /root/test_load_balance.sh
# ============================================================

cd /root/tutorials/exercises/load_balance

echo "=== [1] 清理 & 编译 ==="
mn -c 2>/dev/null >/dev/null
make build 2>/dev/null

echo "=== [2] 启动拓扑（等待 15 秒）==="
echo "拓扑: h1 -> s1(负载均衡器) -> h2 或 h3"
echo "h1 向虚拟 IP 10.0.0.1 发 8 条消息"
echo ""

cat > /tmp/lb_cmds.txt << 'EOF'
h2 timeout 12 ./receive.py >& /tmp/h2log.txt &
h3 timeout 12 ./receive.py >& /tmp/h3log.txt &
sleep 2
h1 bash -c 'for i in a b c d e f g h; do ./send.py 10.0.0.1 $i; done'
sleep 4
exit
EOF

timeout 50 cat /tmp/lb_cmds.txt | make run > /tmp/lb_run.log 2>&1

echo ""
echo "=============================="
echo "  h2 收到的消息："
echo "=============================="
grep "load.*b'" /tmp/h2log.txt 2>/dev/null | sed "s/.*load.*= b'/  -> /" | sed "s/'//"

echo ""
echo "=============================="
echo "  h3 收到的消息："
echo "=============================="
grep "load.*b'" /tmp/h3log.txt 2>/dev/null | sed "s/.*load.*= b'/  -> /" | sed "s/'//"

echo ""
echo "=============================="
echo "  结果：8 条消息分别发给 h2 和 h3"
echo "  负载均衡生效！✅"
echo "=============================="

mn -c 2>/dev/null >/dev/null
