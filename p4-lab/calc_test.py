#!/usr/bin/env python3
"""Non-interactive test script for P4 calculator."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calc import P4calc
from scapy.all import Ether, srp1

tests = [
    ("1+1", '+', 1, 1, 2),
    ("2+3", '+', 2, 3, 5),
    ("5-3", '-', 5, 3, 2),
    ("7&3", '&', 7, 3, 3),
    ("15|8", '|', 15, 8, 15),
    ("7^4", '^', 7, 4, 3),
]

iface = 'eth0'
passed = 0
failed = 0

for label, op, a, b, expected in tests:
    pkt = Ether(dst='00:04:00:00:00:00', type=0x1234) / P4calc(op=op, operand_a=a, operand_b=b)
    pkt = pkt / ' '
    resp = srp1(pkt, iface=iface, timeout=2, verbose=False)
    if resp and P4calc in resp:
        actual = resp[P4calc].result
        status = "PASS" if actual == expected else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1
        print(f"{label} = {actual} (expected {expected}) [{status}]")
    else:
        failed += 1
        print(f"{label} = NO RESPONSE [FAIL]")

print(f"\n=== {passed}/{passed+failed} tests passed ===")
sys.exit(0 if failed == 0 else 1)
