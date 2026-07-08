#!/bin/bash
# Run in Mininet: source /tmp/fwtest.sh
echo "=== Test 1: h1 --> h2 (internal, should PASS) ==="
echo "Starting server on h2..."
h2 timeout 5 python3 /tmp/tcpserver.py 5555 &
sleep 0.5
h1 timeout 3 python3 /tmp/tcpclient.py 10.0.2.2 5555 test1
wait

echo ""
echo "=== Test 2: h3 --> h1 (external, should be BLOCKED) ==="
echo "Starting server on h1..."
h1 timeout 5 python3 /tmp/tcpserver.py 5556 &
sleep 0.5
h3 timeout 3 python3 /tmp/tcpclient.py 10.0.1.1 5556 test2
wait

echo ""
echo "=== Done ==="
