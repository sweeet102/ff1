#!/bin/bash
# 初始化 OVS（每次容器重启后运行一次即可）
echo "初始化 OVS..."
ovs-vsctl --no-wait init 2>/dev/null
ovs-vswitchd --pidfile --detach --log-file 2>/dev/null
sleep 2
echo "OVS 就绪"
