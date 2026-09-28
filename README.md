# deskflow-stuck-watchdog

Automatically releases keys and mouse buttons that [Deskflow](https://github.com/deskflow/deskflow) leaves stuck on a Linux/X11 client — the stuck Shift or dead left-click you get when the link drops mid-keystroke and the key-up never arrives.

## How it works

Deskflow injects input through the X server's XTEST devices (`Virtual core XTEST keyboard` / `Virtual core XTEST pointer`), which X tracks separately from your physical keyboard and mouse. The watchdog polls those devices once a second. Any key held there for 10s, or button for 20s, is treated as an orphaned key-down and released individually — keys you hold on local hardware are never touched.

After releasing, if there isn't exactly one `deskflow-core client` process or no established connection to the server port, it also restarts the Deskflow Flatpak. Every action is logged to the journal and shown as a desktop notification.

Restarting Deskflow alone doesn't fix a stuck key: the latched state lives in the X server, not the client.

## Requirements

- X11 session (not Wayland)
- Python 3, `xinput`, `libX11`, `libXtst`, `ss`, `pgrep`
- `notify-send` (optional)
- Deskflow as a Flatpak (only needed for the auto-restart)

## Install

```sh
git clone https://github.com/lukaszzalewski/deskflow-stuck-watchdog.git
cd deskflow-stuck-watchdog
./install.sh
```

This installs a systemd user service that starts at login.

```sh
journalctl --user -u deskflow-stuck-watchdog -f          # logs
systemctl --user disable --now deskflow-stuck-watchdog   # uninstall
```

## Configuration

Set with `Environment=` in the unit (`systemctl --user edit deskflow-stuck-watchdog`):

| Variable | Default | |
|---|---|---|
| `KEY_STUCK_SECS` | `10` | Seconds a key may be held before release |
| `BUTTON_STUCK_SECS` | `20` | Seconds a mouse button may be held before release |
| `POLL_SECS` | `1` | Poll interval |
| `DRY_RUN` | `0` | `1` = only log what would be released |
| `AUTO_RESTART` | `1` | `0` = never restart Deskflow |
| `DESKFLOW_PORT` | `24800` | Server port used for the link check |
| `FLATPAK_APP` | `org.deskflow.deskflow` | Flatpak app ID to restart |
| `DISPLAY` | `:0` | X display |

Trade-off: a genuine hold through Deskflow longer than the threshold (a very long drag, holding an arrow key) will be cut short.

## License

MIT
