#!/bin/bash

# Screenshot tool with area selection for Arch Linux
# Supports both X11 and Wayland

# Output directory and filename
SCREENSHOT_DIR="$HOME/Pictures/Screenshots"
mkdir -p "$SCREENSHOT_DIR"
FILENAME="$SCREENSHOT_DIR/screenshot_$(date +%Y%m%d_%H%M%S).png"

# Function to send notification
send_notification() {
    if command -v notify-send &> /dev/null; then
        notify-send -i "$FILENAME" "Screenshot gespeichert" "$FILENAME"
    fi
}

# Check if running Wayland or X11
if [ -n "$WAYLAND_DISPLAY" ]; then
    # Wayland: use grim + slurp
    if command -v grim &> /dev/null && command -v slurp &> /dev/null; then
        if grim -g "$(slurp)" "$FILENAME" && [ -f "$FILENAME" ]; then
            echo "Screenshot saved to: $FILENAME"
            send_notification
        else
            echo "Screenshot cancelled"
            exit 1
        fi
    else
        echo "Error: grim and slurp are required for Wayland"
        echo "Install with: sudo pacman -S grim slurp"
        exit 1
    fi
elif [ -n "$DISPLAY" ]; then
    # X11: prefer maim + slop, fallback to scrot or import
    if command -v maim &> /dev/null && command -v slop &> /dev/null; then
        if maim -s "$FILENAME" && [ -f "$FILENAME" ]; then
            echo "Screenshot saved to: $FILENAME"
            send_notification
        else
            echo "Screenshot cancelled"
            exit 1
        fi
    elif command -v scrot &> /dev/null; then
        if scrot -s "$FILENAME" && [ -f "$FILENAME" ]; then
            echo "Screenshot saved to: $FILENAME"
            send_notification
        else
            echo "Screenshot cancelled"
            exit 1
        fi
    elif command -v import &> /dev/null; then
        if import "$FILENAME" && [ -f "$FILENAME" ]; then
            echo "Screenshot saved to: $FILENAME"
            send_notification
        else
            echo "Screenshot cancelled"
            exit 1
        fi
    else
        echo "Error: No screenshot tool found"
        echo "Install one of:"
        echo "  sudo pacman -S maim slop  (recommended)"
        echo "  sudo pacman -S scrot"
        echo "  sudo pacman -S imagemagick"
        exit 1
    fi
else
    echo "Error: No display server detected"
    exit 1
fi
