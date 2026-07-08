#!/bin/bash
# OVS 初始化脚本 — 在 Docker 容器内运行
# 解决 Docker 环境无内核模块问题：使用 netdev 用户态数据路径

# 设置 netdev 为默认数据路径
ovs-vsctl set Open_vSwitch . other_config:datapath-type=netdev 2>/dev/null

# 杀掉旧进程
pkill ovs-vswitchd 2>/dev/null
sleep 1

# 启动 ovs-vswitchd（后台）
/usr/sbin/ovs-vswitchd \
    --pidfile=/var/run/openvswitch/ovs-vswitchd.pid \
    --detach \
    -vconsole:emer -vsyslog:err -vfile:info 2>&1

sleep 2

# 验证
echo "OVS Ready: $(ovs-vsctl get Open_vSwitch . other_config 2>&1)"
echo "vswitchd: $(pgrep ovs-vswitchd || echo 'NOT RUNNING')"
