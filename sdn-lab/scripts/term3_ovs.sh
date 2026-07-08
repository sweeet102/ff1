#!/bin/bash
cd /root/lab
sleep 15
echo ""
echo "root@$(hostname):~/lab# ovs-ofctl -O OpenFlow13 dump-flows s1"
echo ""
ovs-ofctl -O OpenFlow13 dump-flows s1
echo ""
echo "root@$(hostname):~/lab# ovs-vsctl show"
echo ""
ovs-vsctl show
echo ""
echo "=== Flow tables captured ==="
exec bash
