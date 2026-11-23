#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the catalog + Proxmark wrapper · pruebas del catálogo y el envoltorio.
Run · Ejecutar:  python3 tests/test_pm3.py
"""
import os
import sys
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "files"))
import catalog  # noqa: E402
from pm3 import PM3  # noqa: E402

fails = 0


def check(name, cond):
    global fails
    print(("  ok  " if cond else "FAIL  ") + name)
    if not cond:
        fails += 1


def raises(fn):
    try:
        fn(); return False
    except Exception:
        return True


# ---- catalog ---------------------------------------------------------------
check("catalog has >= 25 types", len(catalog.CATALOG) >= 25)
check("every entry has notes", all(c.get("notes_en") and c.get("notes_es") for c in catalog.CATALOG))

e, f = catalog.classify("[+] HID H10301 26-bit; FC: 123 CN: 45678 (raw: 2004d1a35b)", "lf")
check("classify HID", e and e["key"] == "hid_prox" and f["fc"] == "123")
check("HID sim cmd", catalog.build_cmd("sim", e, f) == "lf hid sim -w H10301 --fc 123 --cn 45678")
check("HID clone cmd", catalog.build_cmd("clone", e, f) == "lf hid clone -w H10301 --fc 123 --cn 45678")

e, f = catalog.classify("[+] MIFARE Classic 1K\n[=] UID: 04 A3 2B 9C", "hf")
check("classify MIFARE", e and e["key"] == "mifare_classic")
caps = catalog.capabilities(e, f)
check("MIFARE is secure + needs decode", caps["secure"] and caps["decode"] == "mf_autopwn")

e, f = catalog.classify("[+] MIFARE DESFire EV2\n[=] UID: 04 7A", "hf")
check("DESFire not clonable", catalog.capabilities(e, f)["clonable"] is False)

# ---- wrapper (demo) --------------------------------------------------------
pm = PM3(demo=True, state_dir="/tmp/proxlafy-test-pm3")
shutil.rmtree("/tmp/proxlafy-test-pm3", ignore_errors=True)
pm = PM3(demo=True, state_dir="/tmp/proxlafy-test-pm3")
st = pm.status()
check("demo status connected", st["connected"] and st["demo"])

card = None
for _ in range(9):
    c = pm.read("lf")
    if c and c["key"] == "hid_prox":
        card = c; break
check("read detects HID", card is not None and card["caps"]["emulable"])
card["id"] = "t1"; card["name"] = "Test"

# ---- persistent emulation --------------------------------------------------
pm.start_sim(card)
check("is simulating", pm.status()["simulating"] is not None)
check("active_sim persisted", os.path.exists(os.path.join("/tmp/proxlafy-test-pm3", "active_sim.json")))
check("read blocked while simulating", raises(lambda: pm.read("lf")))

pm2 = PM3(demo=True, state_dir="/tmp/proxlafy-test-pm3")   # simulate power cycle
check("pending after restart", pm2.status()["pending_sim"] is not None)
pm2.resume_if_needed()
check("resumed after power cycle", pm2.status()["simulating"] is not None)
pm2.stop_sim()
check("cleared after cancel", pm2.status()["simulating"] is None)
check("active_sim removed", not os.path.exists(os.path.join("/tmp/proxlafy-test-pm3", "active_sim.json")))

# ---- decode (pm2 is stopped, so the device is free) ------------------------
mf = None
for _ in range(9):
    c = pm2.read("hf")
    if c and c["key"] == "mifare_classic":
        mf = c; break
check("read detects MIFARE", mf is not None)
if mf:
    mf, res = pm2.decode(mf)
    check("decode MIFARE ok", res["ok"] and mf.get("decoded"))

print()
if fails:
    print("%d test(s) failed" % fails); sys.exit(1)
print("all tests passed")
