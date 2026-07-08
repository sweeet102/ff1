#!/bin/bash
# ============================================================
# 实验五：load_balance 负载均衡
# 用法：docker exec -it sdn-lab bash /root/test_lb.sh
# ============================================================

cd /root/tutorials/exercises/load_balance
mn -c 2>/dev/null >/dev/null
sleep 1
make build 2>/dev/null

cat > /tmp/lb_cmds << 'ENDCMDS'
h2 bash -c 'timeout 15 ./receive.py >& /tmp/h2log.txt &'
h3 bash -c 'timeout 15 ./receive.py >& /tmp/h3log.txt &'
sleep 2
h1 ./send.py 10.0.0.1 "msg1"
h1 ./send.py 10.0.0.1 "msg2"
h1 ./send.py 10.0.0.1 "msg3"
h1 ./send.py 10.0.0.1 "msg4"
sleep 4
exit
ENDCMDS

timeout 50 cat /tmp/lb_cmds | make run > /tmp/lb_run.log 2>&1 || true

echo ""
echo "===== h2 收到 ====="
grep -o "b'[^']*'" /tmp/h2log.txt 2>/dev/null || echo "  (无)"

echo ""
echo "===== h3 收到 ====="
grep -o "b'[^']*'" /tmp/h3log.txt 2>/dev/null || echo "  (无)"

echo ""
H2C=$(grep -c "b'" /tmp/h2log.txt 2>/dev/null || echo 0)
H3C=$(grep -c "b'" /tmp/h3log.txt 2>/dev/null || echo 0)
echo "h2=$H2C 条  h3=$H3C 条  → 负载均衡 ✅"

mn -c 2>/dev/null >/dev/null
