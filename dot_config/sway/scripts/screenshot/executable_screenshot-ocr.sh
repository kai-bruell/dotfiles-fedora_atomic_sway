#!/bin/bash

# Screenshot OCR tool for Arch Linux
# Takes a screenshot, performs OCR, and copies text to clipboard

# Temporary file for screenshot
TEMP_FILE="/tmp/screenshot_ocr_$(date +%s).png"

# Function to copy to clipboard
copy_to_clipboard() {
    local text="$1"
    if [ -n "$WAYLAND_DISPLAY" ]; then
        if command -v wl-copy &> /dev/null; then
            echo -n "$text" | wl-copy
            return 0
        else
            echo "Error: wl-clipboard required for Wayland"
            echo "Install with: sudo pacman -S wl-clipboard"
            return 1
        fi
    elif [ -n "$DISPLAY" ]; then
        if command -v xclip &> /dev/null; then
            echo -n "$text" | xclip -selection clipboard
            return 0
        elif command -v xsel &> /dev/null; then
            echo -n "$text" | xsel --clipboard
            return 0
        else
            echo "Error: xclip or xsel required for X11"
            echo "Install with: sudo pacman -S xclip"
            return 1
        fi
    fi
    return 1
}

# Function to send notification
send_notification() {
    local title="$1"
    local message="$2"
    if command -v notify-send &> /dev/null; then
        notify-send "$title" "$message"
    fi
}

# Take screenshot
echo "Select area for OCR..."
if [ -n "$WAYLAND_DISPLAY" ]; then
    if command -v grim &> /dev/null && command -v slurp &> /dev/null; then
        grim -g "$(slurp)" "$TEMP_FILE" || exit 1
    else
        echo "Error: grim and slurp required for Wayland"
        echo "Install with: sudo pacman -S grim slurp"
        exit 1
    fi
elif [ -n "$DISPLAY" ]; then
    if command -v maim &> /dev/null && command -v slop &> /dev/null; then
        maim -s "$TEMP_FILE" || exit 1
    elif command -v scrot &> /dev/null; then
        scrot -s "$TEMP_FILE" || exit 1
    else
        echo "Error: maim+slop or scrot required"
        echo "Install with: sudo pacman -S maim slop"
        exit 1
    fi
else
    echo "Error: No display server detected"
    exit 1
fi

# Check if tesseract is installed
if ! command -v tesseract &> /dev/null; then
    echo "Error: tesseract is required for OCR"
    echo "Install with: sudo pacman -S tesseract tesseract-data-deu tesseract-data-eng"
    rm -f "$TEMP_FILE"
    exit 1
fi

# Perform OCR
echo "Performing OCR..."
OCR_TEXT=$(tesseract "$TEMP_FILE" stdout -l deu+eng 2>/dev/null)

# Clean up temp file
rm -f "$TEMP_FILE"

# Check if OCR produced any text
if [ -z "$OCR_TEXT" ]; then
    echo "No text detected"
    send_notification "OCR Fehler" "Kein Text erkannt"
    exit 1
fi

# Copy to clipboard
if copy_to_clipboard "$OCR_TEXT"; then
    echo "Text copied to clipboard!"
    echo "---"
    echo "$OCR_TEXT"
    echo "---"

    # Count characters and lines
    CHAR_COUNT=$(echo -n "$OCR_TEXT" | wc -m)
    LINE_COUNT=$(echo "$OCR_TEXT" | wc -l)

    send_notification "OCR Erfolgreich" "$CHAR_COUNT Zeichen, $LINE_COUNT Zeilen in Zwischenablage kopiert"
else
    echo "Failed to copy to clipboard"
    exit 1
fi
