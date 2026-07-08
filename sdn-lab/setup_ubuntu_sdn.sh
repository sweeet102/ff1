#!/bin/bash
# ================================================
# SDN 实验环境一键安装脚本 (Ubuntu 24.04 ARM64)
# 复制此文件到 Ubuntu 虚拟机桌面，右键"Run as Program"
# 或终端运行: bash setup_ubuntu_sdn.sh
# ================================================

set -e

echo "============================================"
echo " 江苏大学 SDN 实验环境安装"
echo " 对应指导书 Section 1.1 环境搭建"
echo "============================================"
echo ""

# 1. 更新 apt 源
echo "[1/6] 更新 apt 源并安装基础依赖..."
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y git gcc python3-dev libffi-dev libssl-dev \
    libxml2-dev libxslt1-dev zlib1g-dev python3-pip curl wget gedit

# 2. 安装 OVS
echo ""
echo "[2/6] 安装 Open vSwitch..."
sudo apt-get install -y openvswitch-switch
ovs-vsctl --version

# 3. 安装 Wireshark
echo ""
echo "[3/6] 安装 Wireshark..."
echo 'wireshark-common wireshark-common/install-setuid boolean true' | sudo debconf-set-selections
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y wireshark

# 4. 安装 iperf
echo ""
echo "[4/6] 安装 iperf..."
sudo apt-get install -y iperf
iperf -v

# 5. 安装 Ryu 4.34
echo ""
echo "[5/6] 安装 Ryu 控制器..."
cd ~
if [ -d ryu ]; then rm -rf ryu; fi
git clone https://github.com/faucetsdn/ryu.git
cd ryu
pip3 install .
cd ~

# Patch Ryu for modern eventlet
WSGI_PATH=$(python3 -c "import ryu; print(ryu.__path__[0])")/app/wsgi.py
python3 -c "
with open('$WSGI_PATH') as f: c = f.read()
c = c.replace('from eventlet.wsgi import ALREADY_HANDLED', 'ALREADY_HANDLED = None')
with open('$WSGI_PATH', 'w') as f: f.write(c)
print('Ryu patched for modern eventlet')
"

ryu-manager --version

# 6. 安装 Mininet
echo ""
echo "[6/6] 安装 Mininet..."
cd ~
if [ -d mininet ]; then rm -rf mininet; fi
git clone https://github.com/mininet/mininet
cd mininet
git checkout 2.2.2
sed -i 's/iproute/iproute2/' util/install.sh
util/install.sh -nf

mn --version

echo ""
echo "============================================"
echo " 环境安装完成！"
echo "============================================"
echo ""
echo "验证命令："
echo "  ryu-manager --version"
echo "  mn --version"
echo "  ovs-vsctl --version"
echo "  iperf -v"
echo "  wireshark --version"
echo ""
echo "快速启动实验一："
echo "  终端1: ryu-manager ryu/app/simple_switch_13.py"
echo "  终端2: sudo mn --controller=remote,ip=127.0.0.1 --mac --switch=ovsk,protocols=OpenFlow13 --topo=single,4"
echo "  终端3: wireshark &"
echo "  终端4: ovs-vsctl show; ovs-ofctl -O OpenFlow13 dump-flows s1"
echo ""
