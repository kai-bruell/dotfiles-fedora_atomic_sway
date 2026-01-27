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
# Usage:
#   workspace-per-monitor.sh switch <1-9>   # Wechselt zum Workspace
#   workspace-per-monitor.sh move <1-9>     # Verschiebt Fenster zum Workspace

set -euo pipefail

# Alle aktiven Outputs alphabetisch sortiert (für stabilen Index)
get_sorted_outputs() {
    swaymsg -t get_outputs -r | jq -r '[.[] | select(.active == true) | .name] | sort | .[]'
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

# Hauptlogik
main() {
    local action="${1:-}"
    local workspace="${2:-}"

    if [[ -z "$action" || -z "$workspace" ]]; then
        echo "Usage: $0 <switch|move|move-follow> <1-9>" >&2
        exit 1
    fi

    # Validiere Workspace-Nummer
    if ! [[ "$workspace" =~ ^[1-9]$ ]]; then
        echo "Error: Workspace must be 1-9" >&2
        exit 1
    fi

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
        *)
            echo "Error: Unknown action '$action'. Use: switch, move, move-follow" >&2
            exit 1
            ;;
    esac
}

main "$@"
