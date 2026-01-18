#!/bin/bash

# Hole alle tmux sessions
sessions=$(tmux list-sessions -F "#S" 2>/dev/null)

if [ -z "$sessions" ]; then
    exit 0
fi

# Zeige rofi menu mit Alt+d zum Löschen
selected=$(echo "$sessions" | rofi -dmenu -p "tmux sessions" \
    -kb-custom-1 "Alt+d" \
    -theme ~/.config/sway/scripts/launcher.rasi)
exit_code=$?

if [ $exit_code -eq 10 ]; then
    # Alt+d gedrückt - Session löschen
    if [ -n "$selected" ]; then
        tmux kill-session -t "$selected"
    fi
    # Menu erneut anzeigen
    exec "$0"
elif [ $exit_code -eq 0 ] && [ -n "$selected" ]; then
    # Session ausgewählt - attachen
    foot -e tmux attach-session -t "$selected"
fi
