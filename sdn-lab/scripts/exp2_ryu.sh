#!/bin/bash
cd /root/lab
APP="$1"
echo ""
echo "root@$(hostname):~/lab# ryu-manager --verbose app/${APP}.py"
echo ""
ryu-manager --verbose app/${APP}.py
