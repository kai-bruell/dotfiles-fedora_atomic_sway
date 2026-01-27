#!/usr/bin/env python3
"""
GTK GUI zum Konfigurieren der Monitor-Anordnung für Sway.

Features:
- Koordinaten-basierte Positionierung (X, Y)
- Visuelle Vorschau mit proportionaler Größe
- Relative Positionierung zu beliebigem Monitor
- Generiert Sway output Config
"""

import gi
import subprocess
import json
import os
import fcntl
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, Graphene

CONFIG_DIR = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'sway'
CONFIG_FILE = CONFIG_DIR / 'workspace-monitors.conf'
LOCK_FILE = Path('/tmp/workspace-monitors.lock')


@dataclass
class MonitorInfo:
    name: str
    width: int
    height: int
    scale: float
    active: bool
    make: str = ""
    model: str = ""

    @property
    def scaled_width(self) -> int:
        return int(self.width / self.scale)

    @property
    def scaled_height(self) -> int:
        return int(self.height / self.scale)

    @property
    def display_name(self) -> str:
        """Menschenlesbarer Name (Hersteller + Modell)."""
        if self.make and self.model:
            make_short = self.make.split()[0]
            return f"{make_short} {self.model}"
        return self.name


@dataclass
class MonitorConfig:
    name: str
    x: int = 0
    y: int = 0
    is_primary: bool = False


def get_sway_outputs() -> list[MonitorInfo]:
    """Holt alle aktiven Outputs von Sway mit Details."""
    try:
        result = subprocess.run(
            ['swaymsg', '-t', 'get_outputs', '-r'],
            capture_output=True, text=True, check=True
        )
        outputs = json.loads(result.stdout)
        monitors = []
        for o in outputs:
            if o.get('active', False):
                mode = o.get('current_mode', {})
                monitors.append(MonitorInfo(
                    name=o['name'],
                    width=mode.get('width', 1920),
                    height=mode.get('height', 1080),
                    scale=o.get('scale', 1.0),
                    active=True,
                    make=o.get('make', ''),
                    model=o.get('model', '')
                ))
        return monitors
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return []


def read_config() -> list[MonitorConfig]:
    """Liest die Config-Datei."""
    configs = []
    if CONFIG_FILE.exists():
        try:
            with open(LOCK_FILE, 'w') as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_SH)
                with open(CONFIG_FILE, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split(',')
                            if len(parts) >= 4:
                                # Neues Format: name,x,y,is_primary
                                configs.append(MonitorConfig(
                                    name=parts[0],
                                    x=int(parts[1]) if parts[1] else 0,
                                    y=int(parts[2]) if parts[2] else 0,
                                    is_primary=parts[3].lower() == 'true' if len(parts) > 3 else False
                                ))
                            elif len(parts) == 1:
                                # Altes Format: nur name
                                configs.append(MonitorConfig(name=parts[0]))
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        except (IOError, ValueError):
            pass
    return configs


def write_config(configs: list[MonitorConfig]) -> bool:
    """Schreibt die Config-Datei."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(LOCK_FILE, 'w') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            with open(CONFIG_FILE, 'w') as f:
                f.write("# Monitor-Konfiguration für workspace-per-monitor.sh\n")
                f.write("# Format: name,x,y,is_primary\n")
                f.write("# Reihenfolge bestimmt Workspace-Zuordnung (Index 0 = WS 1-9, etc.)\n\n")
                for cfg in configs:
                    f.write(f"{cfg.name},{cfg.x},{cfg.y},{cfg.is_primary}\n")
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        return True
    except IOError as e:
        print(f"Fehler beim Schreiben: {e}")
        return False


def write_sway_output_config(configs: list[MonitorConfig]):
    """Schreibt eine Sway-Config-Datei für die Monitor-Positionen."""
    config_path = CONFIG_DIR / 'config.d' / '20-monitor-positions.conf'
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, 'w') as f:
        f.write("# Auto-generiert von workspace-monitor-gui.py\n")
        f.write("# Nicht manuell bearbeiten!\n\n")
        for cfg in configs:
            f.write(f"output {cfg.name} pos {cfg.x} {cfg.y}\n")


class MonitorPreview(Gtk.DrawingArea):
    """Visuelle Vorschau der Monitor-Anordnung."""

    def __init__(self):
        super().__init__()
        self.monitors: dict[str, MonitorInfo] = {}
        self.configs: list[MonitorConfig] = []
        self.set_draw_func(self._draw)
        self.set_content_height(300)
        self.set_content_width(500)

    def update(self, monitors: dict[str, MonitorInfo], configs: list[MonitorConfig]):
        self.monitors = monitors
        self.configs = configs
        self.queue_draw()

    def _draw(self, area, cr, width, height):
        if not self.configs or not self.monitors:
            # Keine Monitore
            cr.set_source_rgb(0.3, 0.3, 0.3)
            cr.select_font_face("Sans")
            cr.set_font_size(14)
            cr.move_to(width/2 - 80, height/2)
            cr.show_text("Keine Monitore gefunden")
            return

        # Berechne Bounds
        min_x = min(c.x for c in self.configs)
        min_y = min(c.y for c in self.configs)
        max_x = max(c.x + self.monitors[c.name].scaled_width for c in self.configs if c.name in self.monitors)
        max_y = max(c.y + self.monitors[c.name].scaled_height for c in self.configs if c.name in self.monitors)

        total_width = max_x - min_x
        total_height = max_y - min_y

        if total_width == 0 or total_height == 0:
            return

        # Skalierung berechnen (mit Padding)
        padding = 40
        available_width = width - 2 * padding
        available_height = height - 2 * padding
        scale = min(available_width / total_width, available_height / total_height)

        # Offset für Zentrierung
        offset_x = padding + (available_width - total_width * scale) / 2 - min_x * scale
        offset_y = padding + (available_height - total_height * scale) / 2 - min_y * scale

        # Zeichne Monitore
        for i, cfg in enumerate(self.configs):
            if cfg.name not in self.monitors:
                continue

            mon = self.monitors[cfg.name]
            x = cfg.x * scale + offset_x
            y = cfg.y * scale + offset_y
            w = mon.scaled_width * scale
            h = mon.scaled_height * scale

            # Hintergrund
            if cfg.is_primary:
                cr.set_source_rgb(0.2, 0.4, 0.6)  # Blau für Primary
            else:
                cr.set_source_rgb(0.25, 0.25, 0.25)  # Grau

            cr.rectangle(x, y, w, h)
            cr.fill()

            # Rand
            cr.set_source_rgb(0.6, 0.6, 0.6)
            cr.set_line_width(2)
            cr.rectangle(x, y, w, h)
            cr.stroke()

            # Text
            cr.set_source_rgb(1, 1, 1)
            cr.select_font_face("Sans", 0, 0)

            # Connector Name oben am Rand (eDP-1, HDMI-A-2, etc.)
            cr.set_font_size(9)
            cr.set_source_rgb(0.8, 0.8, 0.8)
            extents = cr.text_extents(cfg.name)
            cr.move_to(x + w/2 - extents.width/2, y + 12)
            cr.show_text(cfg.name)

            # Monitor Name (Make + Model) in der Mitte
            cr.set_source_rgb(1, 1, 1)
            cr.set_font_size(11)
            text = mon.display_name
            extents = cr.text_extents(text)
            cr.move_to(x + w/2 - extents.width/2, y + h/2 - 12)
            cr.show_text(text)

            # Auflösung
            cr.set_font_size(10)
            res_text = f"{mon.width}x{mon.height}"
            extents = cr.text_extents(res_text)
            cr.move_to(x + w/2 - extents.width/2, y + h/2 + 3)
            cr.show_text(res_text)

            # Koordinaten
            cr.set_font_size(9)
            cr.set_source_rgb(0.7, 0.7, 0.7)
            coord_text = f"({cfg.x}, {cfg.y})"
            extents = cr.text_extents(coord_text)
            cr.move_to(x + w/2 - extents.width/2, y + h/2 + 18)
            cr.show_text(coord_text)

            # Workspace-Index
            cr.set_font_size(9)
            if i == 0:
                ws_text = f"[{i}] WS 1-9"
            else:
                ws_text = f"[{i}] WS {i*10+1}-{i*10+9}"
            extents = cr.text_extents(ws_text)
            cr.move_to(x + w/2 - extents.width/2, y + h - 8)
            cr.show_text(ws_text)


class MonitorRow(Gtk.ListBoxRow):
    """Eine Zeile für Monitor-Konfiguration."""

    def __init__(self, config: MonitorConfig, monitor: MonitorInfo, index: int, total: int,
                 all_monitors: list[str], on_change, on_move):
        super().__init__()
        self.config = config
        self.monitor = monitor
        self.on_change = on_change
        self.on_move = on_move
        self.all_monitors = all_monitors
        self._updating = False

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        # Obere Zeile: Primary, Name, Auflösung, Move-Buttons
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.append(top_row)

        # Primary Checkbox
        self.primary_check = Gtk.CheckButton()
        self.primary_check.set_active(config.is_primary)
        self.primary_check.set_tooltip_text("Primary (Referenz)")
        self.primary_check.connect('toggled', self._on_primary_toggled)
        top_row.append(self.primary_check)

        # Index
        index_label = Gtk.Label(label=f"[{index}]")
        index_label.add_css_class('dim-label')
        top_row.append(index_label)

        # Monitor Name (Make + Model)
        name_label = Gtk.Label(label=monitor.display_name)
        name_label.set_xalign(0)
        top_row.append(name_label)

        # Connector (eDP-1, HDMI-A-2)
        connector_label = Gtk.Label(label=f"({config.name})")
        connector_label.add_css_class('dim-label')
        top_row.append(connector_label)

        # Auflösung
        res_label = Gtk.Label(label=f"{monitor.width}x{monitor.height}")
        res_label.add_css_class('dim-label')
        top_row.append(res_label)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        top_row.append(spacer)

        # Move buttons
        up_btn = Gtk.Button(icon_name="go-up-symbolic")
        up_btn.set_sensitive(index > 0)
        up_btn.set_tooltip_text("Nach oben (Workspace-Reihenfolge)")
        up_btn.connect('clicked', lambda _: self.on_move(config.name, -1))
        top_row.append(up_btn)

        down_btn = Gtk.Button(icon_name="go-down-symbolic")
        down_btn.set_sensitive(index < total - 1)
        down_btn.set_tooltip_text("Nach unten (Workspace-Reihenfolge)")
        down_btn.connect('clicked', lambda _: self.on_move(config.name, 1))
        top_row.append(down_btn)

        # Untere Zeile: Koordinaten oder Relativ-Positionierung
        bottom_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.append(bottom_row)

        # X Koordinate
        x_label = Gtk.Label(label="X:")
        x_label.add_css_class('dim-label')
        bottom_row.append(x_label)

        self.x_spin = Gtk.SpinButton()
        self.x_spin.set_range(-10000, 10000)
        self.x_spin.set_increments(10, 100)
        self.x_spin.set_value(config.x)
        self.x_spin.set_width_chars(7)
        self.x_spin.connect('value-changed', self._on_coord_changed)
        bottom_row.append(self.x_spin)

        # Y Koordinate
        y_label = Gtk.Label(label="Y:")
        y_label.add_css_class('dim-label')
        bottom_row.append(y_label)

        self.y_spin = Gtk.SpinButton()
        self.y_spin.set_range(-10000, 10000)
        self.y_spin.set_increments(10, 100)
        self.y_spin.set_value(config.y)
        self.y_spin.set_width_chars(7)
        self.y_spin.connect('value-changed', self._on_coord_changed)
        bottom_row.append(self.y_spin)

        # Spacer
        spacer2 = Gtk.Box()
        spacer2.set_hexpand(True)
        bottom_row.append(spacer2)

        # Schnell-Positionierungs-Buttons (relativ zum Primary)
        for direction, icon, tooltip in [
            ('west', 'go-previous-symbolic', 'Links vom Primary'),
            ('north', 'go-up-symbolic', 'Über dem Primary'),
            ('south', 'go-down-symbolic', 'Unter dem Primary'),
            ('east', 'go-next-symbolic', 'Rechts vom Primary'),
        ]:
            btn = Gtk.Button(icon_name=icon)
            btn.set_tooltip_text(tooltip)
            btn.connect('clicked', self._on_quick_position, direction)
            bottom_row.append(btn)

        self.set_child(box)

    def _on_quick_position(self, btn, direction):
        """Positioniert diesen Monitor relativ zum Primary."""
        self.on_change('position', (self.config.name, direction))

    def _on_primary_toggled(self, checkbox):
        if checkbox.get_active():
            self.on_change('primary', self.config.name)

    def _on_coord_changed(self, spin):
        if self._updating:
            return
        self.config.x = int(self.x_spin.get_value())
        self.config.y = int(self.y_spin.get_value())
        self.on_change('coords', None)

    def update_coords(self, x: int, y: int):
        """Aktualisiert die Koordinaten-Anzeige."""
        self._updating = True
        self.x_spin.set_value(x)
        self.y_spin.set_value(y)
        self._updating = False


class MonitorConfigWindow(Adw.ApplicationWindow):
    """Hauptfenster für Monitor-Konfiguration."""

    def __init__(self, app):
        super().__init__(application=app, title="Monitor-Anordnung")
        self.set_default_size(750, 600)

        # Load data
        self.monitors = {m.name: m for m in get_sway_outputs()}
        self.configs = read_config()

        # Sync configs with active monitors
        self._sync_configs()

        # Toast Overlay
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(main_box)

        # Header
        header = Adw.HeaderBar()
        main_box.append(header)

        save_btn = Gtk.Button(label="Speichern")
        save_btn.add_css_class('suggested-action')
        save_btn.connect('clicked', self.on_save)
        header.pack_end(save_btn)

        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Monitore neu laden")
        refresh_btn.connect('clicked', self.on_refresh)
        header.pack_start(refresh_btn)

        # Content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        main_box.append(content)

        # Preview
        preview_frame = Gtk.Frame()
        preview_frame.set_label("Vorschau (Maßstabsgetreu)")
        content.append(preview_frame)

        self.preview = MonitorPreview()
        preview_frame.set_child(self.preview)

        # Monitor list
        list_frame = Gtk.Frame()
        list_frame.set_label("Monitor-Konfiguration")
        list_frame.set_vexpand(True)
        content.append(list_frame)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        list_frame.set_child(scrolled)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class('boxed-list')
        scrolled.set_child(self.list_box)

        self._refresh_ui()

    def _sync_configs(self):
        """Synchronisiert Configs mit aktiven Monitoren."""
        active_names = set(self.monitors.keys())
        config_names = {c.name for c in self.configs}

        # Remove configs for disconnected monitors
        self.configs = [c for c in self.configs if c.name in active_names]

        # Add new monitors
        for name in sorted(active_names - config_names):
            # Neuer Monitor rechts vom letzten
            x = 0
            if self.configs:
                last = self.configs[-1]
                if last.name in self.monitors:
                    x = last.x + self.monitors[last.name].scaled_width
            self.configs.append(MonitorConfig(name=name, x=x, y=0))

        # Ensure exactly one primary
        has_primary = any(c.is_primary for c in self.configs)
        if not has_primary and self.configs:
            # Erster alphabetisch = primary
            sorted_by_name = sorted(self.configs, key=lambda c: c.name)
            sorted_by_name[0].is_primary = True

    def _refresh_ui(self):
        """Aktualisiert die komplette UI."""
        self._refresh_list()
        self._refresh_preview()

    def _refresh_preview(self):
        """Aktualisiert die Vorschau."""
        self.preview.update(self.monitors, self.configs)

    def _refresh_list(self):
        """Aktualisiert die Liste."""
        while row := self.list_box.get_row_at_index(0):
            self.list_box.remove(row)

        all_names = [c.name for c in self.configs]
        for i, cfg in enumerate(self.configs):
            if cfg.name not in self.monitors:
                continue
            row = MonitorRow(cfg, self.monitors[cfg.name], i, len(self.configs),
                           all_names, self._on_change, self._move_monitor)
            self.list_box.append(row)

    def _on_change(self, change_type: str, data):
        """Callback bei Änderungen."""
        if change_type == 'primary':
            # Nur ein Primary
            new_primary = data
            for c in self.configs:
                c.is_primary = (c.name == new_primary)
            self._refresh_ui()

        elif change_type == 'coords':
            self._refresh_preview()

        elif change_type == 'position':
            # Schnell-Positionierung relativ zum Primary
            name, direction = data
            self._position_relative_to_primary(name, direction)

    def _position_relative_to_primary(self, name: str, direction: str):
        """Positioniert Monitor relativ zum Primary."""
        print(f"Position: {name} -> {direction}")
        cfg = next((c for c in self.configs if c.name == name), None)
        primary_cfg = next((c for c in self.configs if c.is_primary), None)

        print(f"cfg={cfg}, primary={primary_cfg}")
        if not cfg or not primary_cfg or cfg.name == primary_cfg.name:
            print("Early return!")
            return

        mon = self.monitors.get(name)
        primary_mon = self.monitors.get(primary_cfg.name)

        if not mon or not primary_mon:
            return

        if direction == 'east':
            cfg.x = primary_cfg.x + primary_mon.scaled_width
            cfg.y = primary_cfg.y
        elif direction == 'west':
            cfg.x = primary_cfg.x - mon.scaled_width
            cfg.y = primary_cfg.y
        elif direction == 'north':
            cfg.x = primary_cfg.x
            cfg.y = primary_cfg.y - mon.scaled_height
        elif direction == 'south':
            cfg.x = primary_cfg.x
            cfg.y = primary_cfg.y + primary_mon.scaled_height

        self._refresh_ui()

    def _move_monitor(self, name: str, direction: int):
        """Verschiebt Monitor in der Workspace-Reihenfolge."""
        for i, cfg in enumerate(self.configs):
            if cfg.name == name:
                new_idx = i + direction
                if 0 <= new_idx < len(self.configs):
                    self.configs.pop(i)
                    self.configs.insert(new_idx, cfg)
                    self._refresh_ui()
                break

    def on_save(self, _):
        """Speichert und wendet an."""
        if write_config(self.configs):
            write_sway_output_config(self.configs)
            subprocess.run(['swaymsg', 'reload'], capture_output=True)
            self.close()
        else:
            toast = Adw.Toast(title="Fehler beim Speichern!")
            toast.set_timeout(3)
            self.toast_overlay.add_toast(toast)

    def on_refresh(self, _):
        """Lädt Monitore neu."""
        self.monitors = {m.name: m for m in get_sway_outputs()}
        self.configs = read_config()
        self._sync_configs()
        self._refresh_ui()
        toast = Adw.Toast(title="Aktualisiert")
        toast.set_timeout(1)
        self.toast_overlay.add_toast(toast)


class MonitorConfigApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='de.sway.monitor-config')

    def do_activate(self):
        win = MonitorConfigWindow(self)
        win.present()


def main():
    app = MonitorConfigApp()
    app.run(None)


if __name__ == '__main__':
    main()
