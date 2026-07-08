#!/bin/bash
# Experiment 1: L2 Simple Switch with full pcap capture

pkill ryu-manager 2>/dev/null; mn -c 2>/dev/null; sleep 1
mkdir -p /root/lab/output

echo "=== Experiment 1: L2 Simple Switch ==="

# 1. Start Ryu
echo "[1] Starting Ryu controller..."
ryu-manager ryu.app.simple_switch_13 &>/root/lab/output/ryu_exp1.log &
RYU_PID=$!
sleep 3

# 2. Capture all traffic to pcap
echo "[2] Starting packet capture..."
tshark -i any -w /root/lab/output/exp1_capture.pcap &
TSHARK_PID=$!
sleep 1

# 3. Start Mininet and run tests
echo "[3] Starting Mininet topology..."
mn --controller=remote,ip=127.0.0.1:6633 --mac \
   --switch=ovsk,protocols=OpenFlow13 --topo=single,4 \
   --test pingall 2>&1 | tee /root/lab/output/mn_exp1.log
echo ""

# 4. OVS flow tables (quick run to capture)
echo "[4] Capturing flow tables..."
mn --controller=remote,ip=127.0.0.1:6633 --mac \
   --switch=ovsk,protocols=OpenFlow13 --topo=single,4 \
   -c exit 2>/dev/null || true
sleep 3

mn --controller=remote,ip=127.0.0.1:6633 --mac \
   --switch=ovsk,protocols=OpenFlow13 --topo=single,4 &
MN_PID=$!
sleep 8

echo "--- OVS Flow Table ---"
ovs-ofctl -O OpenFlow13 dump-flows s1 2>&1
echo ""
echo "--- OVS Switch Info ---"
ovs-vsctl show 2>&1
echo ""

# Kill mininet
kill $MN_PID 2>/dev/null; sleep 2; mn -c 2>/dev/null

# 5. Stop capture
sleep 1
kill $TSHARK_PID 2>/dev/null; wait $TSHARK_PID 2>/dev/null
kill $RYU_PID 2>/dev/null; wait $RYU_PID 2>/dev/null

# 6. Show pcap summary
echo ""
echo "============================================"
echo " Experiment 1 Complete"
echo "============================================"
echo "Pcap file: output/exp1_capture.pcap"
echo "  Open on Mac with: open output/exp1_capture.pcap"
echo ""
echo "Packet summary:"
tshark -r /root/lab/output/exp1_capture.pcap -T fields \
  -e frame.number -e ip.src -e ip.dst -e _ws.col.Protocol \
  -E header=y 2>/dev/null | head -30
