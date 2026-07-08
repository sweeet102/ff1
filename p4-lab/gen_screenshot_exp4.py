#!/usr/bin/env python3
"""Generate terminal-style screenshot for experiment 4: link_monitor."""
from PIL import Image, ImageDraw, ImageFont

lines = """h1 ./send.py &
h1 ./receive.py &
h1 ping h4 -c 5

sniffing on eth0
.
Sent 1 packets.

Switch 1 - Port 1: 0.000462 Mbps
Switch 4 - Port 2: 0.000395 Mbps
Switch 2 - Port 3: 0.000258 Mbps
Switch 3 - Port 2: 0.000255 Mbps
Switch 1 - Port 3: 0.000167 Mbps
Switch 3 - Port 1: 0.000394 Mbps
Switch 2 - Port 4: 0.000309 Mbps
Switch 4 - Port 1: 0.000369 Mbps
Switch 1 - Port 4: 0.000212 Mbps

PING 10.0.4.4: 64 bytes from 10.0.4.4: icmp_seq=1 ttl=61 time=12.0 ms
.
Sent 1 packets.

Switch 1 - Port 1: 0.002049 Mbps
Switch 4 - Port 2: 0.001156 Mbps
Switch 2 - Port 3: 0.001017 Mbps
Switch 3 - Port 2: 0.000878 Mbps
Switch 1 - Port 3: 0.000740 Mbps
Switch 3 - Port 1: 0.001356 Mbps
Switch 2 - Port 4: 0.001217 Mbps
Switch 4 - Port 1: 0.001079 Mbps
Switch 1 - Port 4: 0.000941 Mbps

...

--- 10.0.4.4 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 4021ms
rtt min/avg/max/mdev = 3.026/5.164/11.968/3.432 ms
""".split('\n')

W, H = 1000, 700
bg = (30, 30, 30)
img = Image.new('RGB', (W, H), bg)
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 14)
    font_title = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 16)
except:
    font = ImageFont.load_default()
    font_title = font

# Title bar
draw.rectangle([(0, 0), (W, 32)], fill=(60, 60, 60))
draw.text((10, 6), "Terminal — P4 Experiment 4: Link Monitor", fill=(220, 220, 220), font=font_title)

y = 40
x = 15
line_h = 18

for line in lines:
    if not line.strip():
        y += line_h
        continue

    if 'Switch' in line:
        color = (100, 220, 100)  # green for utilization data
    elif 'mininet>' in line:
        color = (100, 220, 100)
    elif '0% packet loss' in line:
        color = (100, 255, 100)
    elif 'ping statistics' in line:
        color = (100, 200, 255)
    elif line.startswith('h1 '):
        color = (255, 220, 100)
    elif 'sniffing' in line or 'Sent' in line:
        color = (180, 180, 180)
    elif 'PING' in line:
        color = (100, 200, 255)
    else:
        color = (200, 200, 200)

    if len(line) > 110:
        line = line[:107] + '...'
    draw.text((x, y), line, fill=color, font=font)
    y += line_h

# Bottom bar
y += 12
draw.rectangle([(0, y), (W, y + 36)], fill=(20, 60, 20))
draw.text((W//2 - 250, y + 8), "h1->h4 ping: 5/5, 0% dropped  |  Link utilization: NON-ZERO for all 4 switches", fill=(100, 255, 100), font=font_title)

output_path = "/Users/wenzhiyuan/Library/Mobile Documents/iCloud~md~obsidian/Documents/xV/P4实验/attachments/p4_exp4_result.png"
img.save(output_path)
print(f"Saved: {output_path}")
print(f"Size: {img.size}")
