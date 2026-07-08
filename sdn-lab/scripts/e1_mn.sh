#!/bin/bash
cd /root/lab
sleep 3
echo ""
echo "root@$(hostname):~/lab# mn --controller=remote,ip=127.0.0.1 --mac --switch=ovsk,protocols=OpenFlow13 --topo=single,4 --test pingall"
echo ""
mn --controller=remote,ip=127.0.0.1 --mac --switch=ovsk,protocols=OpenFlow13 --topo=single,4 --test pingall
echo ""
exec bash
