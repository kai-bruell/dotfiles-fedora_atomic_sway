#!/bin/bash
# workspace-per-monitor.sh - Dynamische unabhängige Workspaces pro Monitor
#
# Jeder Monitor bekommt eigene Workspaces 1-9:
#   Monitor Index 0: Workspaces 1-9
#   Monitor Index 1: Workspaces 11-19
#   Monitor Index 2: Workspaces 21-29
#   ...
#
# Formel: workspace = (monitor_index * 10) + taste
#
# Monitor-Reihenfolge wird aus Config gelesen:
#   ~/.config/sway/workspace-monitors.conf
#
# Usage:
#   workspace-per-monitor.sh switch <1-9>   # Wechselt zum Workspace
#   workspace-per-monitor.sh move <1-9>     # Verschiebt Fenster zum Workspace
#   workspace-per-monitor.sh list           # Zeigt aktuelle Monitor-Reihenfolge

set -euo pipefail

CONFIG_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/sway/workspace-monitors.conf"
LOCK_FILE="/tmp/workspace-monitors.lock"

# Liest Config mit Shared Lock (erlaubt parallele Leser)
# Gibt nur Monitor-Namen zurück (erstes Feld vor Komma)
# Config-Format: name,x,y,is_primary
read_config_with_lock() {
    local config_content=""
    if [[ -f "$CONFIG_FILE" ]]; then
        exec 200>"$LOCK_FILE"
        flock -s 200  # Shared lock für Lesen
        # Extrahiere nur den Monitor-Namen (erstes Feld)
        config_content=$(grep -v '^#' "$CONFIG_FILE" 2>/dev/null | grep -v '^$' | cut -d',' -f1 || true)
        exec 200>&-
    fi
    echo "$config_content"
}

# Alle aktiven Outputs von Sway
get_active_outputs() {
    swaymsg -t get_outputs -r | jq -r '.[] | select(.active == true) | .name'
}

# Sortierte Output-Liste basierend auf Config
# Monitore aus Config zuerst (in Config-Reihenfolge), dann Rest alphabetisch
get_sorted_outputs() {
    local config_monitors
    local active_outputs
    local result=()

    config_monitors=$(read_config_with_lock)
    active_outputs=$(get_active_outputs)

    # Erst Monitore aus Config (falls aktiv)
    if [[ -n "$config_monitors" ]]; then
        while IFS= read -r monitor; do
            if echo "$active_outputs" | grep -qx "$monitor"; then
                result+=("$monitor")
            fi
        done <<< "$config_monitors"
    fi

    # Dann restliche aktive Monitore alphabetisch
    while IFS= read -r output; do
        local found=false
        for m in "${result[@]:-}"; do
            if [[ "$m" == "$output" ]]; then
                found=true
                break
            fi
        done
        if [[ "$found" == "false" ]]; then
            result+=("$output")
        fi
    done < <(echo "$active_outputs" | sort)

    printf '%s\n' "${result[@]}"
}

# Aktuell fokussierter Output
get_focused_output() {
    swaymsg -t get_outputs -r | jq -r '.[] | select(.focused == true) | .name'
}

# Index des Outputs in der sortierten Liste (0-basiert)
get_monitor_index() {
    local focused_output="$1"
    local index=0

    while IFS= read -r output; do
        if [[ "$output" == "$focused_output" ]]; then
            echo "$index"
            return 0
        fi
        ((index++))
    done < <(get_sorted_outputs)

    # Fallback: Index 0 wenn nicht gefunden
    echo "0"
}

# Berechnet den echten Workspace-Namen basierend auf Monitor-Index
calculate_workspace() {
    local monitor_index="$1"
    local local_workspace="$2"

    if [[ "$monitor_index" -eq 0 ]]; then
        # Erster Monitor: Workspaces 1-9
        echo "$local_workspace"
    else
        # Weitere Monitore: 11-19, 21-29, ...
        echo "$(( (monitor_index * 10) + local_workspace ))"
    fi
}

# Wechselt zum Workspace auf dem aktuellen Monitor
switch_workspace() {
    local local_workspace="$1"
    local focused_output
    local monitor_index
    local target_workspace

    focused_output=$(get_focused_output)
    monitor_index=$(get_monitor_index "$focused_output")
    target_workspace=$(calculate_workspace "$monitor_index" "$local_workspace")

    swaymsg "workspace $target_workspace"
}

# Verschiebt das fokussierte Fenster zum Workspace auf dem aktuellen Monitor
move_to_workspace() {
    local local_workspace="$1"
    local focused_output
    local monitor_index
    local target_workspace

    focused_output=$(get_focused_output)
    monitor_index=$(get_monitor_index "$focused_output")
    target_workspace=$(calculate_workspace "$monitor_index" "$local_workspace")

    swaymsg "move container to workspace $target_workspace"
}

# Verschiebt Fenster UND folgt zum Workspace
move_and_follow() {
    local local_workspace="$1"
    local focused_output
    local monitor_index
    local target_workspace

    focused_output=$(get_focused_output)
    monitor_index=$(get_monitor_index "$focused_output")
    target_workspace=$(calculate_workspace "$monitor_index" "$local_workspace")

    swaymsg "move container to workspace $target_workspace; workspace $target_workspace"
}

# Zeigt aktuelle Monitor-Reihenfolge mit Workspace-Ranges
list_monitors() {
    local index=0
    echo "Monitor-Reihenfolge (Config: $CONFIG_FILE):"
    echo ""
    while IFS= read -r output; do
        local ws_start ws_end
        if [[ "$index" -eq 0 ]]; then
            ws_start=1
            ws_end=9
        else
            ws_start=$(( (index * 10) + 1 ))
            ws_end=$(( (index * 10) + 9 ))
        fi
        printf "  [%d] %-20s → Workspaces %d-%d\n" "$index" "$output" "$ws_start" "$ws_end"
        ((index++))
    done < <(get_sorted_outputs)
}

# Hauptlogik
main() {
    local action="${1:-}"
    local workspace="${2:-}"

    case "$action" in
        list)
            list_monitors
            exit 0
            ;;
        switch|move|move-follow)
            if [[ -z "$workspace" ]]; then
                echo "Usage: $0 $action <1-9>" >&2
                exit 1
            fi
            # Validiere Workspace-Nummer
            if ! [[ "$workspace" =~ ^[1-9]$ ]]; then
                echo "Error: Workspace must be 1-9" >&2
                exit 1
            fi
            ;;
        *)
            echo "Usage: $0 <switch|move|move-follow> <1-9>" >&2
            echo "       $0 list" >&2
            exit 1
            ;;
    esac

    case "$action" in
        switch)
            switch_workspace "$workspace"
            ;;
        move)
            move_to_workspace "$workspace"
            ;;
        move-follow)
            move_and_follow "$workspace"
            ;;
    esac
}

main "$@"
