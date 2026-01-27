#!/bin/bash
# init-workspaces.sh - Setzt initiale Workspaces pro Monitor
# Monitor 0: Workspace 1, Monitor 1: Workspace 11, Monitor 2: Workspace 21, ...

outputs=$(swaymsg -t get_outputs -r | jq -r '[.[] | select(.active == true) | .name] | sort | .[]')

index=0
while IFS= read -r output; do
    if [[ $index -eq 0 ]]; then
        workspace=1
    else
        workspace=$((index * 10 + 1))
    fi
    swaymsg "focus output $output; workspace $workspace"
    ((index++))
done <<< "$outputs"

# Fokus zurück auf Hauptmonitor
swaymsg "focus output $(echo "$outputs" | head -1)"
