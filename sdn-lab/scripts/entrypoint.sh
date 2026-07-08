#!/bin/bash
# SDN Lab entrypoint — OVS startup + optional X11 GUI

# Create OVS database directory
mkdir -p /var/run/openvswitch /var/log/openvswitch

# Initialize OVS DB if needed
if [ ! -f /etc/openvswitch/conf.db ]; then
    ovsdb-tool create /etc/openvswitch/conf.db /usr/share/openvswitch/vswitch.ovsschema
fi

# Start ovsdb-server
ovsdb-server --remote=punix:/var/run/openvswitch/db.sock \
    --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
    --pidfile --detach --log-file 2>/dev/null

ovs-vsctl --no-wait init

# Start ovs-vswitchd
ovs-vswitchd --pidfile --detach --log-file 2>/dev/null
sleep 1

echo "============================================"
echo "  SDN Lab Environment Ready"
echo "  OVS:      $(ovs-vsctl --version 2>&1 | head -1)"
echo "  Mininet:  $(mn --version 2>&1 | head -1)"
echo "  Ryu:      $(ryu-manager --version 2>&1 | head -1)"
echo "  iperf:    $(iperf -v 2>&1 | head -1)"
echo "============================================"

# X11 GUI setup
if [ -n "$DISPLAY" ]; then
    echo "  DISPLAY=$DISPLAY — GUI apps (wireshark, xterm) available"
    xhost + 2>/dev/null || true
else
    echo "  No DISPLAY set — CLI mode only (tshark for capture)"
fi
echo ""
echo "Quick start:"
echo "  1: ryu-manager ryu.app.simple_switch_13"
echo "  2: mn --controller=remote,ip=127.0.0.1:6633 --mac --switch=ovsk,protocols=OpenFlow13 --topo=single,4"
if [ -n "$DISPLAY" ]; then
    echo "  3: wireshark &    # GUI packet capture"
    echo "  4: xterm &        # extra terminals"
fi
echo ""

exec "$@"
