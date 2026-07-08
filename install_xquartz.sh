#!/bin/bash
# Install XQuartz X11 server for macOS
# This enables GUI apps (Wireshark, xterm) from Docker to display on your Mac

echo "Installing XQuartz..."
sudo installer -pkg /tmp/XQuartz.pkg -target /

echo ""
echo "After installation:"
echo "1. Log out and log back in (or reboot)"
echo "2. Open XQuartz from Applications/Utilities"
echo "3. In XQuartz Preferences > Security, enable 'Allow connections from network clients'"
echo "4. Then run:  cd ~/Desktop/ff1/sdn-lab && ./run.sh gui"
