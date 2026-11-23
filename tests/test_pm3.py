#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Basic tests for the Proxmark wrapper · pruebas básicas del envoltorio.
Run · Ejecutar:  python3 tests/test_pm3.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "files"))
from pm3 import PM3  # noqa: E402

fails = 0


def check(name, cond):
    global fails
    print(("  ok  " if cond else "FAIL  ") + name)
    if not cond:
        fails += 1


def _raises(fn):
    try:
        fn()
        return False
    except Exception:
        return True


pm = PM3(demo=True)

# status / version
st = pm.status()
check("demo status connected", st["connected"] and st["demo"])

# LF HID parse
hid = pm._parse_lf("[+] HID H10301 26-bit; FC: 123 CN: 45678 (raw: 2004d1a35b)")
check("parse HID band=lf", hid and hid["band"] == "lf")
check("parse HID fc=123", hid["data"]["fc"] == 123)
check("parse HID cn=45678", hid["data"]["cn"] == 45678)

# EM410x parse
em = pm._parse_lf("[+] EM 410x ID 1234567890")
check("parse EM410x", em and em["type"] == "EM410x")

# HF MIFARE parse
mf = pm._parse_hf("[+] MIFARE Classic 1K\n[+]  UID: 04 A3 2B 9C")
check("parse MIFARE band=hf", mf and mf["band"] == "hf")
check("parse MIFARE uid", mf["data"]["uid"] == "04A32B9C")

# sim / clone command builders
check("sim HID command", pm._sim_command(hid) == "lf hid sim -w H10301 --fc 123 --cn 45678")
check("clone HID command", pm._clone_command(hid) == "lf hid clone -w H10301 --fc 123 --cn 45678")
check("sim EM command", pm._sim_command(em) == "lf em 410x sim --id 1234567890")

# emulate lifecycle (demo)
pm.start_sim(hid)
check("is simulating", pm.is_simulating() is not None)
check("read blocked while simulating", _raises(lambda: pm.read("lf")))
pm.stop_sim()
check("stopped", pm.is_simulating() is None)

print()
if fails:
    print("%d test(s) failed" % fails)
    sys.exit(1)
print("all tests passed")
