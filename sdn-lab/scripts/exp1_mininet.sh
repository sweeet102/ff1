#!/bin/bash
cd /root/lab
sleep 4
echo ""
echo "root@$(hostname):~/lab# mn --controller=remote,ip=127.0.0.1 --mac --switch=ovsk,protocols=OpenFlow13 --topo=single,4 --test pingall"
echo ""

# Run Mininet pingall, then keep topology alive by running interactive mode
mn --controller=remote,ip=127.0.0.1 --mac --switch=ovsk,protocols=OpenFlow13 --topo=single,4 --test pingall

echo ""
echo "=== Mininet test complete, keeping bash open for OVS queries ==="
echo "Run: ovs-ofctl -O OpenFlow13 dump-flows s1"
exec bash
