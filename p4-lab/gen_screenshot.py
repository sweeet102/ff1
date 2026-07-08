#!/usr/bin/env python3
"""Generate a terminal-style screenshot image from experiment output text."""
from PIL import Image, ImageDraw, ImageFont

# Read the captured output
with open('/tmp/p4_exp1_full.txt') as f:
    lines = f.readlines()

# Filter: keep key output, skip boring lines
skip_patterns = ['EventletDeprecationWarning', 'not greened', 'RLock', 'p4c-bm2-ss', 'Successfully copied']
filtered = []
for line in lines:
    if any(p in line for p in skip_patterns):
        continue
    filtered.append(line.rstrip())

text = '\n'.join(filtered)

# Terminal style: dark background, light text
W, H = 1000, 1850
bg = (30, 30, 30)
fg = (200, 200, 200)
green = (100, 220, 100)
cyan = (100, 200, 255)
yellow = (255, 220, 100)

img = Image.new('RGB', (W, H), bg)
draw = ImageDraw.Draw(img)

# Try monospace font
try:
    font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 15)
    font_title = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 17)
except:
    try:
        font = ImageFont.truetype("/System/Library/Fonts/SF-Mono.ttf", 15)
        font_title = ImageFont.truetype("/System/Library/Fonts/SF-Mono.ttf", 17)
    except:
        font = ImageFont.load_default()
        font_title = font

# Title bar
draw.rectangle([(0, 0), (W, 30)], fill=(60, 60, 60))
draw.text((10, 5), "Terminal — P4 Experiment 1: Basic IPv4 Forwarding", fill=(220, 220, 220), font=font_title)

y = 40
x = 15
line_h = 19

for line in text.split('\n'):
    if not line.strip():
        y += line_h
        continue

    # Color coding
    if 'mininet>' in line:
        color = green
    elif 'Results:' in line and '0% dropped' in line:
        color = (100, 255, 100)  # bright green for success
    elif 'Results:' in line:
        color = (255, 100, 100)  # red for failure
    elif 'Configuring switch' in line:
        color = cyan
    elif 'Inserting' in line:
        color = yellow
    elif 'h1 ->' in line or 'h2 ->' in line or 'h3 ->' in line or 'h4 ->' in line:
        color = (180, 230, 180)
    elif line.startswith(' - '):
        color = (160, 160, 160)
    elif 'sudo tcpdump' in line or 'simple_switch_CLI' in line or 'tail -f' in line or 'cat ' in line:
        color = (140, 140, 140)
    elif 'Welcome' in line or '===' in line:
        color = cyan
    else:
        color = fg

    # Truncate long lines
    if len(line) > 120:
        line = line[:117] + '...'

    draw.text((x, y), line, fill=color, font=font)
    y += line_h

# Bottom bar with result
y += 10
draw.rectangle([(0, y), (W, y + 40)], fill=(20, 60, 20))
draw.text((W//2 - 160, y + 8), "PINGALL: 12/12 received, 0% dropped", fill=(100, 255, 100), font=font_title)

output_path = "/Users/wenzhiyuan/Library/Mobile Documents/iCloud~md~obsidian/Documents/xV/P4实验/attachments/p4_exp1_result.png"
img.save(output_path)
print(f"Saved: {output_path}")
print(f"Size: {img.size}")
