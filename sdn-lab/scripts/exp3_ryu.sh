#!/bin/bash
cd /root/lab
echo ""
echo "root@$(hostname):~/lab# ryu-manager --verbose app/multiple_tables.py"
echo ""
ryu-manager --verbose app/multiple_tables.py
