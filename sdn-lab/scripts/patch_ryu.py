#!/usr/bin/env python3
"""Patch Ryu wsgi.py — replace removed ALREADY_HANDLED import"""
import re

wsgi_path = '/usr/local/lib/python3.10/dist-packages/ryu/app/wsgi.py'
with open(wsgi_path) as f:
    lines = f.readlines()

fixed = []
for line in lines:
    if 'from eventlet.wsgi import ALREADY_HANDLED' in line:
        indent = line[:len(line) - len(line.lstrip())]
        fixed.append(f'{indent}ALREADY_HANDLED = None\n')
        print(f'  Patched: {line.strip()} -> ALREADY_HANDLED = None')
    else:
        fixed.append(line)

with open(wsgi_path, 'w') as f:
    f.writelines(fixed)
print("Ryu wsgi.py patched successfully")
