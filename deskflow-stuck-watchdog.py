#!/usr/bin/env python3
"""Auto-release keys/buttons that Deskflow has left latched in the X server.

Deskflow injects input through the XTEST slave devices, which X tracks separately
from the laptop's own keyboard/mouse. A key or button held on those devices for
longer than a human plausibly holds one is an orphaned key-down from a dropped
link; release exactly that code, leaving physical input untouched.
"""

import ctypes
import os
import re
import subprocess
import sys
import time

XTEST_KEYBOARD = "Virtual core XTEST keyboard"
XTEST_POINTER = "Virtual core XTEST pointer"
POLL_SECS = float(os.environ.get("POLL_SECS", "1"))
KEY_STUCK_SECS = float(os.environ.get("KEY_STUCK_SECS", "10"))
BUTTON_STUCK_SECS = float(os.environ.get("BUTTON_STUCK_SECS", "20"))
DRY_RUN = os.environ.get("DRY_RUN") == "1"
AUTO_RESTART = os.environ.get("AUTO_RESTART", "1") == "1"
DESKFLOW_PORT = os.environ.get("DESKFLOW_PORT", "24800")
FLATPAK_APP = os.environ.get("FLATPAK_APP", "org.deskflow.deskflow")

x11 = ctypes.CDLL("libX11.so.6")
xtst = ctypes.CDLL("libXtst.so.6")
x11.XOpenDisplay.restype = ctypes.c_void_p
x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
x11.XKeycodeToKeysym.restype = ctypes.c_ulong
x11.XKeycodeToKeysym.argtypes = [ctypes.c_void_p, ctypes.c_ubyte, ctypes.c_int]
x11.XKeysymToString.restype = ctypes.c_char_p
x11.XKeysymToString.argtypes = [ctypes.c_ulong]
x11.XFlush.argtypes = [ctypes.c_void_p]
xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
xtst.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]


def log(msg):
    print(msg, flush=True)


def notify(msg):
    subprocess.run(["notify-send", "-i", "input-keyboard", "Deskflow watchdog", msg],
                   stderr=subprocess.DEVNULL, check=False)


def held(device, kind):
    out = subprocess.run(["xinput", "query-state", device],
                         capture_output=True, text=True, check=True).stdout
    return {int(n) for n in re.findall(r"%s\[(\d+)\]=down" % kind, out)}


def key_name(dpy, keycode):
    name = x11.XKeysymToString(x11.XKeycodeToKeysym(dpy, keycode, 0))
    return name.decode() if name else "keycode %d" % keycode


def deskflow_needs_restart():
    clients = subprocess.run(["pgrep", "-fc", "deskflow-core client"],
                             capture_output=True, text=True).stdout.strip()
    link = subprocess.run(["ss", "-Htn", "state", "established", "( dport = :%s )" % DESKFLOW_PORT],
                          capture_output=True, text=True).stdout.strip()
    return clients != "1" or not link


def restart_deskflow():
    subprocess.run(["flatpak", "kill", FLATPAK_APP], stderr=subprocess.DEVNULL, check=False)
    time.sleep(1)
    subprocess.Popen(["flatpak", "run", FLATPAK_APP], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    dpy = x11.XOpenDisplay(None)
    if not dpy:
        log("cannot open X display")
        return 1

    since = {}
    log("watching %s / %s (keys %.0fs, buttons %.0fs%s)"
        % (XTEST_KEYBOARD, XTEST_POINTER, KEY_STUCK_SECS, BUTTON_STUCK_SECS, ", dry run" if DRY_RUN else ""))

    while True:
        now = time.monotonic()
        down = {("key", k) for k in held(XTEST_KEYBOARD, "key")}
        down |= {("button", b) for b in held(XTEST_POINTER, "button")}
        since = {code: since.get(code, now) for code in down}

        stuck = [(kind, n) for (kind, n), t in since.items()
                 if now - t >= (KEY_STUCK_SECS if kind == "key" else BUTTON_STUCK_SECS)]
        if stuck:
            names = [key_name(dpy, n) if kind == "key" else "button%d" % n for kind, n in stuck]
            if not DRY_RUN:
                for kind, n in stuck:
                    if kind == "key":
                        xtst.XTestFakeKeyEvent(dpy, n, False, 0)
                    else:
                        xtst.XTestFakeButtonEvent(dpy, n, False, 0)
                    del since[(kind, n)]
                x11.XFlush(dpy)
            restart = AUTO_RESTART and not DRY_RUN and deskflow_needs_restart()
            if restart:
                restart_deskflow()
            msg = "%s %s%s" % ("Would release" if DRY_RUN else "Released", ", ".join(names),
                               "; Deskflow client restarted" if restart else "")
            log(msg)
            notify(msg)
            if DRY_RUN:
                since = {code: now for code in since}

        time.sleep(POLL_SECS)


if __name__ == "__main__":
    sys.exit(main())
