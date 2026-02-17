#!/bin/bash
# tablet-follow-focus.sh - Mappt UGEE S640 Tablet auf den fokussierten Monitor
#
# Als Daemon: Reagiert auf Sway Focus-Events und remappt das Tablet automatisch.
# Als einmaliger Befehl (z.B. Keybinding): tablet-follow-focus.sh remap
#
# Usage:
#   tablet-follow-focus.sh          # Daemon starten (via exec_always in Sway)
#   tablet-follow-focus.sh remap    # Einmalig remappen

set -euo pipefail

readonly TABLET_PEN="10429:2359:UGTABLET_UGEE_S640_Pen"
readonly TABLET_MOUSE="10429:2359:UGTABLET_UGEE_S640_Mouse"
readonly PIDFILE="/tmp/tablet-follow-focus.pid"

remap_to_focused_output() {
    local output
    output=$(swaymsg -t get_outputs -r | jq -r '.[] | select(.focused == true) | .name')

    if [[ -z "$output" ]]; then
        return 0
    fi

    swaymsg input "$TABLET_PEN" map_to_output "$output" 2>/dev/null || true
    swaymsg input "$TABLET_MOUSE" map_to_output "$output" 2>/dev/null || true
}

# Einmaliger Remap (für Keybinding)
if [[ "${1:-}" == "remap" ]]; then
    remap_to_focused_output
    exit 0
fi

# Daemon-Modus: Alte Instanz beenden (z.B. nach sway reload)
if [[ -f "$PIDFILE" ]]; then
    old_pid=$(cat "$PIDFILE")
    kill "$old_pid" 2>/dev/null || true
fi
echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT

# Initial mappen
remap_to_focused_output

# Auf Focus-Events subscriben und Tablet bei jedem Wechsel remappen
swaymsg -t subscribe '["workspace", "window"]' \
    | while IFS= read -r event; do
        change=$(jq -r '.change // empty' <<< "$event" 2>/dev/null)
        if [[ "$change" == "focus" ]]; then
            remap_to_focused_output
        fi
    done
