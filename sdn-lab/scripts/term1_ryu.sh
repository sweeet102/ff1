#!/bin/bash
cd /root/lab
rm -f /root/lab/output/exp1_*.pcap
TS=$(date +%H%M%S)
echo ""
echo "root@$(hostname):~/lab# ryu-manager --verbose ryu.app.simple_switch_13"
echo ""
ryu-manager --verbose ryu.app.simple_switch_13
