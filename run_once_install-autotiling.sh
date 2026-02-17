#!/bin/bash
# Install autotiling for Hyprland-like dwindle tiling in Sway
if ! command -v autotiling &>/dev/null && [ ! -f "$HOME/.local/bin/autotiling" ]; then
    echo "Installing autotiling..."
    pip3 install --user autotiling
fi
