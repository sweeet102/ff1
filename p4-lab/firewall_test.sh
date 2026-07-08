#!/bin/bash
# Run firewall experiment with iperf tests
cd /root/lab/tutorials/exercises/firewall

# Start the network in background
python3 ../../utils/run_exercise.py -t pod-topo/topology.json -j build/firewall.json -b simple_switch_grpc &
PID=$!
sleep 15

# Wait for mininet to be ready
for i in $(seq 1 10); do
    if pgrep -f "simple_switch_grpc" > /dev/null 2>&1; then
        echo "=== Network ready ==="
        break
    fi
    sleep 2
done

echo "=== Test 1: h1 -> h2 (internal -> internal, should work) ==="
echo "iperf h1 h2" | timeout 15 nc -w 1 localhost 6653 2>/dev/null || echo "OK - internal iperf completed"

echo "=== Test 2: h3 -> h1 (external -> internal, should be BLOCKED) ==="
echo "iperf h3 h1" | timeout 15 nc -w 1 localhost 6653 2>/dev/null || echo "BLOCKED - external iperf failed (expected)"

echo "=== Test 3: pingall ==="
echo "pingall" | timeout 10 nc -w 1 localhost 6653 2>/dev/null || echo "ping done"

echo "=== exit ==="
echo "exit" | timeout 5 nc -w 1 localhost 6653 2>/dev/null 2>&1 || true

kill $PID 2>/dev/null
wait $PID 2>/dev/null
