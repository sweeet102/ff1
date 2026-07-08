#!/bin/bash
cd "$(dirname "$0")"
pip3 install -q fastapi uvicorn python-multipart 2>/dev/null
python3 server.py
