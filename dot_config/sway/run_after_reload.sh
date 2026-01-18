#!/bin/bash
# Läuft nach JEDEM apply - aber nur wenn Sway läuft
if swaymsg -t get_version &> /dev/null; then
    swaymsg reload
fi
