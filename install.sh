#!/bin/sh
set -e
cd "$(dirname "$0")"
install -Dm755 deskflow-stuck-watchdog.py "$HOME/.local/bin/deskflow-stuck-watchdog.py"
install -Dm644 deskflow-stuck-watchdog.service "$HOME/.config/systemd/user/deskflow-stuck-watchdog.service"
systemctl --user daemon-reload
systemctl --user enable --now deskflow-stuck-watchdog.service
systemctl --user restart deskflow-stuck-watchdog.service
echo "Installed. Logs: journalctl --user -u deskflow-stuck-watchdog -f"
