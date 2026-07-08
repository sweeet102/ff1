#!/bin/bash
cd /root/lab

# Wait for Mininet to create bridges
for i in $(seq 1 30); do
    ovs-ofctl -O OpenFlow13 dump-flows s1 &>/dev/null && break
    sleep 1
done

echo ""
echo "root@$(hostname):~/lab# ovs-ofctl -O OpenFlow13 dump-flows s1"
echo ""
ovs-ofctl -O OpenFlow13 dump-flows s1

echo ""
echo "root@$(hostname):~/lab# ovs-vsctl show"
echo ""
ovs-vsctl show

echo ""
echo "=== Flow tables and switch info captured ==="
exec bash
