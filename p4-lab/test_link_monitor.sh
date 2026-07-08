#!/bin/bash
# ============================================================
# 实验四：link_monitor 链路监控测试脚本
# 用法（在 Mac 终端里逐条输入）：
#   docker exec -it sdn-lab bash /root/test_link_monitor.sh
# ============================================================

cd /root/tutorials/exercises/link_monitor

echo "=== [1] 清理 ==="
mn -c 2>/dev/null
pkill -9 -f simple_switch 2>/dev/null
sleep 1

echo "=== [2] 编译 ==="
make build 2>/dev/null

echo "=== [3] 启动拓扑（等待约 15 秒）==="
echo ""

cat > /tmp/cmds.txt << 'ENDOFCMDS'
h1 ./send.py &
sleep 1
h1 ./receive.py &
sleep 2
h1 ping h4 -c 5 -i 0.2
sleep 5
exit
ENDOFCMDS

timeout 60 cat /tmp/cmds.txt | make run 2>&1 | tee /tmp/lm_full.log | grep -E "(Switch|Mbps|ping statistics|received|PING|rtt|^$)" --color=never

echo ""
echo "=== [4] 清理 ==="
mn -c 2>/dev/null
echo "完成。如果上方有 'Switch X - Port Y: Z Mbps' 的输出，说明实验成功。"
echo ""
echo "完整日志: docker exec sdn-lab cat /tmp/lm_full.log"
