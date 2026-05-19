import sys
import ctypes
import os
import time
import random
import json
import threading
from ctypes import wintypes
from dataclasses import dataclass


from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QPushButton, QLabel, QScrollArea, QStackedWidget,
    QGridLayout, QLineEdit, QListWidget, QSlider, QGraphicsDropShadowEffect,
    QDialog, QTextEdit, QFileDialog, QMessageBox, QTabWidget, QDoubleSpinBox,
    QSpinBox, QComboBox, QColorDialog, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QMouseEvent, QKeyEvent, QPixmap, QPainter, QPainterPath, QRegion
from pynput import keyboard as pynput_keyboard, mouse as pynput_mouse


# =============================================================================
# THEME SYSTEM
# =============================================================================

_BASE_THEME_SURFACE = {
    "bg": "#07050d",
    "sidebar": "#0b0714",
    "card": "#171020",
    "border": "#2c2240",
    "text": "#f5f3ff",
    "subtext": "#a99ac7",
}

def _accent_theme(accent: str, accent_dim: str) -> dict:
    palette = dict(_BASE_THEME_SURFACE)
    palette.update({"accent": accent, "accent_dim": accent_dim})
    return palette

THEMES = {
    "Cyan":     _accent_theme("#00d2ff", "#008fa1"),
    "Violet":   _accent_theme("#a855f7", "#7c3aed"),
    "Emerald":  _accent_theme("#22c55e", "#16a34a"),
    "Rose":     _accent_theme("#ff4d8d", "#c0305f"),
    "Amber":    _accent_theme("#ffab00", "#c07a00"),
    "Ice":      _accent_theme("#78d8ff", "#4aa8cc"),
    "Crimson":  _accent_theme("#ff3232", "#c01818"),
    "Gold":     _accent_theme("#ffd700", "#b89c00"),
    "Neon":     _accent_theme("#39ff14", "#1ec800"),
    "Lavender": _accent_theme("#c084fc", "#8b54c4"),
    "BlackIce": _accent_theme("#00D2FF", "#007A99"),
}

_current_theme_name = "Cyan"

# =============================================================================
# CUSTOM THEME REGISTRY
# =============================================================================

CUSTOM_THEMES_FILE = "custom_themes.json"

class CustomThemeRegistry:
    """Loads/saves user-created themes from custom_themes.json."""

    def __init__(self):
        self.themes: dict[str, dict] = {}   # name -> palette dict
        self.load()

    def _validate(self, d: dict) -> bool:
        required = {"accent", "accent_dim", "bg", "sidebar", "card", "border", "text", "subtext"}
        return required.issubset(d.keys())

    def load(self, path: str = CUSTOM_THEMES_FILE):
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            self.themes = {k: v for k, v in data.items() if self._validate(v)}
        except Exception:
            pass

    def save(self, path: str = CUSTOM_THEMES_FILE):
        tmp = path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(self.themes, f, indent=4)
            if os.path.exists(path):
                os.replace(tmp, path)
            else:
                os.rename(tmp, path)
        except Exception:
            try:
                os.remove(tmp)
            except Exception:
                pass

    def add(self, name: str, palette: dict):
        self.themes[name] = palette
        self.save()
        # Also inject into global THEMES so it is immediately usable
        THEMES[name] = palette

    def remove(self, name: str):
        self.themes.pop(name, None)
        THEMES.pop(name, None)
        self.save()

custom_theme_registry = CustomThemeRegistry()
# Inject any already-saved custom themes into THEMES at startup
for _cname, _cpal in custom_theme_registry.themes.items():
    THEMES[_cname] = _cpal


def get_theme():
    return THEMES[_current_theme_name]

def _hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def _rgba(hex_color: str, alpha: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgba({r},{g},{b},{alpha:.2f})"

def _mix_hex(c1: str, c2: str, weight: float) -> str:
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    w = max(0.0, min(1.0, weight))
    return f"#{round(r1 * (1 - w) + r2 * w):02x}{round(g1 * (1 - w) + g2 * w):02x}{round(b1 * (1 - w) + b2 * w):02x}"

def slider_stylesheet(t: dict) -> str:
    a = t["accent"]
    tx = t["text"]
    return f"""
QSlider::groove:horizontal {{ height:5px; background:{_rgba(tx, 0.10)}; border-radius:3px; }}
QSlider::handle:horizontal {{ background:{a}; width:17px; height:17px; margin:-7px 0; border-radius:9px; border:3px solid {t['bg']}; }}
QSlider::handle:horizontal:hover {{ background:{_mix_hex(a, tx, 0.22)}; }}
QSlider::sub-page:horizontal {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {a}, stop:1 {_mix_hex(a, tx, 0.18)}); border-radius:3px; }}
"""

def build_stylesheet(t: dict) -> str:
    a=t["accent"]; ad=t["accent_dim"]; bg=t["bg"]; sb=t["sidebar"]
    cd=t["card"]; br=t["border"]; tx=t["text"]; st=t["subtext"]
    panel = _mix_hex(bg, cd, 0.58)
    panel2 = _mix_hex(bg, a, 0.12)
    border_accent = _mix_hex(br, a, 0.42)
    return f"""
QMainWindow, QDialog {{ background-color:{bg}; }}
QWidget {{ font-family:'Segoe UI','Helvetica Neue',sans-serif; font-size:13px; color:{tx}; background-color:transparent; selection-background-color:{_rgba(a, 0.28)}; }}
QToolTip {{ background-color:{panel}; color:{tx}; border:1px solid {border_accent}; border-radius:8px; padding:7px 10px; }}
QScrollArea {{ border:none; background-color:{bg}; }}
QScrollArea > QWidget > QWidget {{ background-color:{bg}; }}
QScrollBar:vertical {{ background:transparent; width:9px; margin:8px 3px; border-radius:5px; }}
QScrollBar::handle:vertical {{ background:{_rgba(tx, 0.17)}; border-radius:5px; min-height:34px; }}
QScrollBar::handle:vertical:hover {{ background:{_rgba(a, 0.72)}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QFrame#Sidebar {{ background-color:{sb}; border-right:1px solid {_rgba(a, 0.18)}; }}
QLabel#SidebarStatus {{ color:{st}; font-size:11px; font-weight:700; padding:2px 20px; }}
QPushButton#SidebarButton {{ background-color:transparent; color:{st}; border:none; border-radius:12px; text-align:left; padding:11px 18px; margin:3px 12px; font-size:13px; font-weight:700; }}
QPushButton#SidebarButton:hover {{ color:{tx}; background-color:{_rgba(tx, 0.07)}; border:1px solid {_rgba(tx, 0.08)}; }}
QPushButton#SidebarButton:checked {{ color:{tx}; background-color:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {_rgba(a, 0.34)}, stop:1 {_rgba(ad, 0.18)}); border-left:3px solid {a}; padding-left:15px; }}
QLabel#SidebarSection {{ color:{_rgba(st, 0.94)}; font-size:10px; font-weight:850; letter-spacing:2px; padding:16px 22px 5px 22px; }}
QFrame#Card {{ background-color:{panel}; border-radius:16px; border:1px solid {_rgba(tx, 0.09)}; }}
QFrame#Card:hover {{ border:1px solid {_rgba(a, 0.42)}; background-color:{_mix_hex(panel, tx, 0.035)}; }}
QFrame#Card[active="true"] {{ border:1px solid {_rgba(a, 0.78)}; background-color:{panel2}; }}
QLabel#CardTitle {{ font-size:14px; font-weight:800; color:{tx}; }}
QLabel#CardDesc {{ font-size:11px; color:{st}; line-height:150%; }}
QLabel#RowLabel {{ font-size:12px; color:{st}; font-weight:650; }}
QLabel#BadgeLabel {{ font-size:11px; font-weight:850; color:{a}; background-color:{_rgba(a, 0.13)}; border:1px solid {_rgba(a, 0.30)}; border-radius:12px; padding:2px 7px; }}
QLabel#TitleChip {{ color:{tx}; background-color:{_rgba(tx, 0.055)}; border:1px solid {_rgba(a, 0.22)}; border-radius:11px; padding:3px 10px; font-size:11px; font-weight:750; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background-color:{_rgba(tx, 0.055)}; border:1px solid {_rgba(tx, 0.11)}; border-radius:10px; padding:8px 12px; color:{tx}; font-size:13px; }}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{ border:1px solid {_rgba(a, 0.32)}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border:1px solid {a}; background-color:{_rgba(tx, 0.075)}; }}
QListWidget {{ background-color:{_rgba(tx, 0.035)}; border:1px solid {_rgba(tx, 0.09)}; border-radius:12px; color:{st}; padding:6px; outline:none; }}
QListWidget::item {{ padding:6px 10px; border-radius:6px; }}
QListWidget::item:selected {{ background-color:{_rgba(a, 0.18)}; color:{tx}; }}
QListWidget::item:hover {{ background-color:{_rgba(tx, 0.06)}; }}
QPushButton#ThemeDot {{ border-radius:10px; border:2px solid transparent; min-width:20px; max-width:20px; min-height:20px; max-height:20px; }}
QPushButton#ThemeDot:checked {{ border:2px solid {tx}; }}
QPushButton#SaveBtn {{ background-color:{a}; color:#050607; font-weight:850; border-radius:10px; padding:9px 18px; border:none; font-size:13px; }}
QPushButton#SaveBtn:hover {{ background-color:{ad}; }}
QPushButton#DangerBtn {{ background-color:rgba(220,50,50,0.14); color:#ff7171; font-weight:750; border-radius:10px; padding:9px 18px; border:1px solid rgba(220,50,50,0.30); font-size:13px; }}
QPushButton#DangerBtn:hover {{ background-color:rgba(220,50,50,0.3); }}
QPushButton#NeutralBtn {{ background-color:{_rgba(tx, 0.06)}; color:{tx}; font-weight:700; border-radius:10px; padding:9px 18px; border:1px solid {_rgba(tx, 0.11)}; font-size:13px; }}
QPushButton#NeutralBtn:hover {{ background-color:{_rgba(tx, 0.10)}; border-color:{_rgba(a, 0.35)}; }}
QLineEdit#DelayBox {{ background-color:{_rgba(tx, 0.055)}; border:1px solid {_rgba(tx, 0.10)}; border-radius:9px; color:{a}; font-weight:750; padding:5px 8px; }}
QLineEdit#DelayBox:focus {{ border-color:{a}; }}
QLabel#DelaySep {{ color:{st}; font-size:14px; }}
/* ── Custom title bar ── */
QFrame#TitleBar {{ background-color:{sb}; border-bottom:1px solid {_rgba(a, 0.16)}; }}
QPushButton#WinClose {{ background-color:{_rgba(tx, 0.06)}; color:{st}; border:1px solid {_rgba(tx, 0.10)}; font-size:13px; font-weight:800; min-width:28px; max-width:28px; min-height:28px; max-height:28px; border-radius:14px; margin-right:10px; }}
QPushButton#WinClose:hover {{ background-color:#c0392b; color:#fff; border-color:#c0392b; }}
QPushButton#WinMinimize {{ background-color:{_rgba(tx, 0.06)}; color:{st}; border:1px solid {_rgba(tx, 0.10)}; font-size:14px; font-weight:800; min-width:28px; max-width:28px; min-height:28px; max-height:28px; border-radius:14px; margin-right:8px; }}
QPushButton#WinMinimize:hover {{ background-color:{_rgba(tx, 0.10)}; color:{tx}; border-color:{_rgba(a, 0.34)}; }}
"""


# =============================================================================
# CONFIG
# =============================================================================

@dataclass
class CrystalSettings:
    master_enabled: bool = True
    enabled: bool = False
    obsidian_slot: str = "1"
    crystal_slot: str = "2"
    place_to_break_delay_min: int = 80
    place_to_break_delay_max: int = 110
    cps: int = 10
    hold_to_repeat: bool = True

@dataclass
class AnchorSettings:
    enabled: bool = False
    activator_key: str = "r"
    anchor_slot: str = "4"
    glowstone_slot: str = "c"
    totem_slot: str = "mouse5"
    delay_min: int = 40
    delay_max: int = 60
    anchor_count_max: int = 1
    glowstone_count_max: int = 1
    totem_count_max: int = 1
    hold_to_repeat: bool = False
    hold_to_repeat: bool = True

@dataclass
class UtilitySettings:
    xp_enabled: bool = False
    xp_key: str = "x"
    xp_slot: str = "6"
    xp_cps: int = 20
    gapple_enabled: bool = False
    gapple_key: str = "g"
    gapple_slot: str = "7"

@dataclass
class SwordSettings:
    stun_enabled: bool = False
    activator_key: str = "f"
    axe_slot: str = "3"
    delay_min: int = 40
    delay_max: int = 60

@dataclass
class ShieldBreakerSettings:
    enabled: bool = False
    activator_key: str = "g"
    axe_slot: str = "3"
    sword_slot: str = "1"
    delay_min: int = 40
    delay_max: int = 60

@dataclass
class StunSlamSettings:
    enabled: bool = False
    activator_key: str = "h"
    axe_slot: str = "3"
    mace_slot: str = "4"
    sword_slot: str = "1"
    return_to_sword: bool = True
    delay_min: int = 40
    delay_max: int = 60

@dataclass
class BreachSwapSettings:
    enabled: bool = False
    activator_key: str = "j"
    swap_slot: str = "4"
    sword_slot: str = "1"
    delay_min: int = 40
    delay_max: int = 80  # hard max 80ms

@dataclass
class CartSettings:
    enabled: bool = False
    activator_key: str = "k"
    bow_slot: str = "5"
    rail_slot: str = "6"
    cart_slot: str = "7"
    rail_delay_min: int = 10
    rail_delay_max: int = 30
    cart_delay_min: int = 10
    cart_delay_max: int = 50

@dataclass
class TrapCartSettings:
    enabled: bool = False
    activator_key: str = "l"
    rail_slot: str = "6"
    cart_slot: str = "7"
    fire_slot: str = "8"
    crossbow_slot: str = "9"
    rail_delay_min: int = 30
    rail_delay_max: int = 50
    cart_delay_min: int = 30
    cart_delay_max: int = 50
    cart_click_count: int = 3
    look_down_min: int = 8    # mouse Y pixels — tune to your sens
    look_down_max: int = 12
    look_delay_min: int = 20  # ms pause after looking down before placing fire
    look_delay_max: int = 40
    fire_delay_min: int = 20
    fire_delay_max: int = 40
    shoot_delay_min: int = 20
    shoot_delay_max: int = 40
    look_up_min: int = 120
    look_up_max: int = 130

@dataclass
class PearlCatchSettings:
    enabled: bool = False
    activator_key: str = "x"
    pearl_slot: str = "3"
    wind_slot: str = "4"
    original_slot: str = "1"
    look_up_min: int = 60
    look_up_max: int = 80
    action_delay_min: int = 30
    action_delay_max: int = 60

@dataclass
class FastClickerSettings:
    enabled: bool = False
    delay_ms: int = 50
    offset_ms: int = 10

@dataclass
class RC4Settings:
    enabled: bool = False
    strength: int = 100  # 1-100%, 100% = 18 down, 1 left
    toggle_key: str = ""

@dataclass
class SMG12Settings:
    enabled: bool = False
    strength: int = 100  # 1-100%, 100% = 11 down, 1 left, 3 right
    toggle_key: str = ""

@dataclass
class F2Settings:
    enabled: bool = False
    strength: int = 100   # 1-100%, 100% = 19 down, 1 left
    toggle_key: str = ""

@dataclass
class VectorSettings:
    enabled: bool = False
    strength: int = 100  # 100% = 8 down, 0 left, 0 right
    toggle_key: str = ""

@dataclass
class UZK50GISettings:
    enabled: bool = False
    strength: int = 100  # 100% = 4 down, 0 left, 0 right
    toggle_key: str = ""

@dataclass
class C70Settings:
    enabled: bool = False
    strength: int = 100  # 100% = 7 down, 0 left, 1 right
    toggle_key: str = ""

@dataclass
class CustomGunSettings:
    enabled: bool = False
    strength: int = 100
    toggle_key: str = ""
    name: str = "Custom Gun"
    badge: str = "CG"
    dy: float = 8.0
    dx: float = 0.0
    slot_key: int = 1   # 1 = primary (key1 arms), 2 = secondary (key2 arms)

# ---------------------------------------------------------------------------
# CUSTOM GUN REGISTRY — persisted to custom_guns.json alongside main config
# ---------------------------------------------------------------------------
CUSTOM_GUNS_FILE = "custom_guns.json"

class CustomGunRegistry:
    """Loads/saves the user's custom gun definitions from custom_guns.json."""

    def __init__(self):
        self.guns: list[CustomGunSettings] = []
        self.load()

    def load(self, path: str = CUSTOM_GUNS_FILE):
        if not os.path.exists(path):
            return
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            self.guns = []
            for g in data:
                s = CustomGunSettings()
                for k, v in g.items():
                    if hasattr(s, k):
                        setattr(s, k, v)
                self.guns.append(s)
        except Exception:
            pass

    def save(self, path: str = CUSTOM_GUNS_FILE):
        data = [g.__dict__.copy() for g in self.guns]
        tmp = path + ".tmp"
        try:
            with open(tmp, 'w') as f:
                json.dump(data, f, indent=4)
            if os.path.exists(path):
                os.replace(tmp, path)
            else:
                os.rename(tmp, path)
        except Exception:
            try:
                os.remove(tmp)
            except Exception:
                pass

    def add(self, gun: CustomGunSettings):
        self.guns.append(gun)
        self.save()

    def remove(self, index: int):
        if 0 <= index < len(self.guns):
            self.guns.pop(index)
            self.save()

    def export_json(self, path: str):
        data = [g.__dict__.copy() for g in self.guns]
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

    def import_json(self, path: str) -> int:
        """Returns number of guns imported."""
        imported = 0
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            for g in data:
                s = CustomGunSettings()
                for k, v in g.items():
                    if hasattr(s, k):
                        setattr(s, k, v)
                self.guns.append(s)
                imported += 1
            self.save()
        except Exception:
            pass
        return imported

gun_registry = CustomGunRegistry()


@dataclass
class TurnFlickSettings:
    enabled: bool = False
    activator_key: str = "v"
    direction: str = "right"   # "right" or "left"
    repeats: int = 1           # 1–10, how many 90° turns per press
    pixels: int = 100          # raw pixel distance for one 90° turn (sens-scaled)

@dataclass
class ScizoSettings:
    # Master toggle keybind
    activator_key: str = "F8"
    # Sub-feature toggles (which ones are armed when master fires)
    random_look_on:    bool = True
    thankyou_on:       bool = True
    inspect_hell_on:   bool = False
    spectator_hell_on: bool = False
    # Thank You interval (ms, snapped to nearest 10)
    thankyou_interval: int = 100   # 10–500 ms

@dataclass
class SensitivitySettings:
    horizontal: int = 13  # in-game sens, 6-100 (13 = baseline, no scaling)
    vertical: int = 13

ALL_BLOCKABLE_KEYS = [
    '1','2','3','4','5','6','7','8','9','0',
    'q','w','e','r','t','y','u','i','o','p',
    'a','s','d','f','g','h','j','k','l',
    'z','x','c','v','b','n','m',
    'space','shift','ctrl','alt','tab',
    'mouse3','mouse4','mouse5',
]

@dataclass
class BlocklistSettings:
    blocked: list = None
    def __post_init__(self):
        if self.blocked is None:
            self.blocked = ['m']

@dataclass
class OverlaySettings:
    enabled: bool = False
    click_through: bool = True
    compact_mode: bool = False
    show_slot_label: bool = True
    show_keybinds: bool = True
    glow: bool = True
    pulse_icon: bool = True
    rainbow_accent: bool = False
    opacity: int = 88
    scale: int = 100
    margin: int = 24
    primary_icon_path: str = ""
    secondary_icon_path: str = ""

@dataclass
class ClientOverlaySettings:
    enabled: bool = False
    toggle_key: str = "f7"
    compact_width: int = 1225
    compact_height: int = 620
    start_hidden: bool = False
    keep_on_top: bool = True

class ConfigManager:
    def __init__(self):
        self.crystal = CrystalSettings()
        self.anchor = AnchorSettings()
        self.util = UtilitySettings()
        self.sword = SwordSettings()
        self.shield_breaker = ShieldBreakerSettings()
        self.stun_slam = StunSlamSettings()
        self.breach_swap = BreachSwapSettings()
        self.cart = CartSettings()
        self.trap_cart = TrapCartSettings()
        self.pearl_catch = PearlCatchSettings()
        self.rc4 = RC4Settings()
        self.smg12 = SMG12Settings()
        self.f2 = F2Settings()
        self.vector = VectorSettings()
        self.uzk50gi = UZK50GISettings()
        self.c70 = C70Settings()
        self.turnflick = TurnFlickSettings()
        self.scizo = ScizoSettings()
        self.fast_clicker = FastClickerSettings()
        self.sensitivity = SensitivitySettings()
        self.blocklist = BlocklistSettings()
        self.overlay = OverlaySettings()
        self.client_overlay = ClientOverlaySettings()
        self.favorites = []
        self.profiles_dir = "profiles"
        if not os.path.exists(self.profiles_dir):
            os.makedirs(self.profiles_dir)
        self.current_profile = "default"
        self.load()

    def save(self, name=None):
        if name:
            self.current_profile = name
            # Named saves (profile saves) always write immediately
            self._do_save()
            return
        # For unnamed saves (live UI changes), defer to the debounce timer if available
        sched = getattr(self, '_schedule_save', None)
        if sched:
            sched()  # restarts the 500ms countdown; actual write happens on timeout
        else:
            self._do_save()

    def _do_save(self):
        os.makedirs(self.profiles_dir, exist_ok=True)
        data = {
            "theme": _current_theme_name,
            "crystal": self.crystal.__dict__,
            "anchor": self.anchor.__dict__,
            "util": self.util.__dict__,
            "sword": self.sword.__dict__,
            "shield_breaker": self.shield_breaker.__dict__,
            "stun_slam": self.stun_slam.__dict__,
            "breach_swap": self.breach_swap.__dict__,
            "cart": self.cart.__dict__,
            "trap_cart": self.trap_cart.__dict__,
            "pearl_catch": self.pearl_catch.__dict__,
            "rc4": self.rc4.__dict__,
            "smg12": self.smg12.__dict__,
            "f2": self.f2.__dict__,
            "vector": self.vector.__dict__,
            "uzk50gi": self.uzk50gi.__dict__,
            "c70": self.c70.__dict__,
            "turnflick": self.turnflick.__dict__,
            "scizo": self.scizo.__dict__,
            "fast_clicker": self.fast_clicker.__dict__,
            "sensitivity": self.sensitivity.__dict__,
            "blocklist": {"blocked": self.blocklist.blocked},
            "overlay": self.overlay.__dict__,
            "client_overlay": self.client_overlay.__dict__,
            "favorites": self.favorites,
        }
        self._write_atomic(os.path.join(self.profiles_dir, f"{self.current_profile}.json"), data)
        self._write_atomic("config.json", data)

    @staticmethod
    def _write_atomic(path, data):
        """Write JSON to a temp file then rename — prevents corrupt/partial writes."""
        tmp = path + ".tmp"
        try:
            with open(tmp, 'w') as f:
                json.dump(data, f, indent=4)
            if os.path.exists(path):
                os.replace(tmp, path)
            else:
                os.rename(tmp, path)
        except Exception:
            try:
                os.remove(tmp)
            except Exception:
                pass

    def load(self, name=None):
        global _current_theme_name
        if name:
            self.current_profile = name
        path = os.path.join(self.profiles_dir, f"{self.current_profile}.json")
        if not os.path.exists(path):
            path = "config.json"
            if not os.path.exists(path):
                return
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                if "theme" in data and data["theme"] in THEMES:
                    _current_theme_name = data["theme"]
                sections = [
                    ("crystal", self.crystal),
                    ("anchor", self.anchor),
                    ("util", self.util),
                    ("sword", self.sword),
                    ("shield_breaker", self.shield_breaker),
                    ("stun_slam", self.stun_slam),
                    ("breach_swap", self.breach_swap),
                    ("cart", self.cart),
                    ("trap_cart", self.trap_cart),
                    ("pearl_catch", self.pearl_catch),
                    ("rc4", self.rc4),
                    ("smg12", self.smg12),
                    ("f2", self.f2),
                    ("vector", self.vector),
                    ("uzk50gi", self.uzk50gi),
                    ("c70", self.c70),
                    ("turnflick", self.turnflick),
                    ("scizo", self.scizo),
                    ("fast_clicker", self.fast_clicker),
                    ("sensitivity", self.sensitivity),
                    ("overlay", self.overlay),
                    ("client_overlay", self.client_overlay),
                ]
                for section, settings in sections:
                    if section in data:
                        for k, v in data[section].items():
                            if hasattr(settings, k):
                                setattr(settings, k, v)
                if "blocklist" in data and "blocked" in data["blocklist"]:
                    self.blocklist.blocked = list(data["blocklist"]["blocked"])
                if "favorites" in data:
                    self.favorites = list(data["favorites"])
        except Exception:
            pass

    @staticmethod
    def _sanitize(name: str) -> str:
        import re
        return re.sub(r'[\\/:*?"<>|]', '_', name).strip() or "default"

cfg = ConfigManager()

def sens_scale(axis: str) -> float:
    """Return the multiplier for recoil pixel values based on in-game sensitivity.
    Baseline is sens 13 (multiplier = 1.0). Formula: 13 / sens.
    axis is 'horizontal' or 'vertical'.
    """
    sens = cfg.sensitivity.horizontal if axis == 'horizontal' else cfg.sensitivity.vertical
    sens = max(6, min(100, sens))
    return 13.0 / sens


# =============================================================================
# INPUT MANAGER
# =============================================================================

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

SCAN_CODES = {
    '1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05, '5': 0x06,
    '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A,
    'q': 0x10, 'w': 0x11, 'e': 0x12, 'r': 0x13, 't': 0x14,
    'a': 0x1E, 's': 0x1F, 'd': 0x20, 'f': 0x21, 'c': 0x2E
}

VK_CODES = {
    '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34, '5': 0x35,
    '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    'q': 0x51, 'w': 0x57, 'e': 0x45, 'r': 0x52, 't': 0x54,
    'a': 0x41, 's': 0x53, 'd': 0x44, 'f': 0x46, 'c': 0x43
}

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong)
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long), ("dy", ctypes.c_long),
        ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_ulonglong)
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]
    _anonymous_ = ("_input",)
    _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT)]

class InputController:
    @staticmethod
    def _send_input(inputs):
        nInputs = len(inputs)
        LPINPUT = INPUT * nInputs
        pInputs = LPINPUT(*inputs)
        ctypes.windll.user32.SendInput(nInputs, pInputs, ctypes.sizeof(INPUT))

    @staticmethod
    def _create_mouse_input(flags, dx=0, dy=0, data=0):
        return INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(dx=dx, dy=dy, mouseData=data, dwFlags=flags, time=0, dwExtraInfo=0))

    @staticmethod
    def _create_key_input(scancode, flags):
        return INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=0, wScan=scancode, dwFlags=flags | KEYEVENTF_SCANCODE, time=0, dwExtraInfo=0))

    def left_click(self):
        self._send_input([self._create_mouse_input(MOUSEEVENTF_LEFTDOWN), self._create_mouse_input(MOUSEEVENTF_LEFTUP)])

    def right_click(self):
        self._send_input([self._create_mouse_input(MOUSEEVENTF_RIGHTDOWN), self._create_mouse_input(MOUSEEVENTF_RIGHTUP)])

    # Mouse button constants for side buttons
    MOUSEEVENTF_XDOWN = 0x0080
    MOUSEEVENTF_XUP   = 0x0100
    XBUTTON1 = 0x0001
    XBUTTON2 = 0x0002

    def press_key(self, key_char):
        k = str(key_char).lower()
        if k in cfg.blocklist.blocked:
            return
            self._send_input([
                self._create_mouse_input(0x0020),  # MOUSEEVENTF_MIDDLEDOWN
                self._create_mouse_input(0x0040),  # MOUSEEVENTF_MIDDLEUP
            ])
            return
        if k == 'mouse4':
            self._send_input([
                self._create_mouse_input(self.MOUSEEVENTF_XDOWN, data=self.XBUTTON1),
                self._create_mouse_input(self.MOUSEEVENTF_XUP,   data=self.XBUTTON1),
            ])
            return
        if k == 'mouse5':
            self._send_input([
                self._create_mouse_input(self.MOUSEEVENTF_XDOWN, data=self.XBUTTON2),
                self._create_mouse_input(self.MOUSEEVENTF_XUP,   data=self.XBUTTON2),
            ])
            return
        self.key_down(key_char)
        time.sleep(0.01)
        self.key_up(key_char)

    def key_down(self, key_char):
        k = str(key_char).lower()
        if k in cfg.blocklist.blocked:
            return
        if k in ('mouse3', 'mouse4', 'mouse5'):
            if k == 'mouse3':
                self._send_input([self._create_mouse_input(0x0020)])
            else:
                data = self.XBUTTON1 if k == 'mouse4' else self.XBUTTON2
                self._send_input([self._create_mouse_input(self.MOUSEEVENTF_XDOWN, data=data)])
            return
        special = {'shift': 0x2A, 'ctrl': 0x1D, 'alt': 0x38, 'space': 0x39, 'tab': 0x0F}
        if k in special:
            self._send_input([self._create_key_input(special[k], 0)])
            return
        scan = SCAN_CODES.get(k)
        if not scan:
            vk = ctypes.windll.user32.VkKeyScanW(k[0]) & 0xFF
            scan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
        if not scan:
            return
        self._send_input([self._create_key_input(scan, 0)])

    def key_up(self, key_char):
        k = str(key_char).lower()
        if k in cfg.blocklist.blocked:
            return
        if k in ('mouse3', 'mouse4', 'mouse5'):
            if k == 'mouse3':
                self._send_input([self._create_mouse_input(0x0040)])
            else:
                data = self.XBUTTON1 if k == 'mouse4' else self.XBUTTON2
                self._send_input([self._create_mouse_input(self.MOUSEEVENTF_XUP, data=data)])
            return
        special = {'shift': 0x2A, 'ctrl': 0x1D, 'alt': 0x38, 'space': 0x39, 'tab': 0x0F}
        if k in special:
            self._send_input([self._create_key_input(special[k], KEYEVENTF_KEYUP)])
            return
        scan = SCAN_CODES.get(k)
        if not scan:
            vk = ctypes.windll.user32.VkKeyScanW(k[0]) & 0xFF
            scan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
        if not scan:
            return
        self._send_input([self._create_key_input(scan, KEYEVENTF_KEYUP)])

    def move_mouse_relative(self, dx, dy):
        self._send_input([self._create_mouse_input(MOUSEEVENTF_MOVE, dx=dx, dy=dy)])

    def human_delay(self, min_ms, max_ms):
        time.sleep(random.uniform(min_ms, max_ms) / 1000.0)

    @staticmethod
    def is_key_pressed(key_code):
        k = str(key_code).lower()
        if len(k) == 1:
            vk = VK_CODES.get(k) or (ctypes.windll.user32.VkKeyScanW(k) & 0xFF)
        else:
            special = {
                'shift': 0x10, 'ctrl': 0x11, 'alt': 0x12, 'space': 0x20, 'tab': 0x09,
                'mouse3': 0x04, 'mouse4': 0x05, 'mouse5': 0x06,
                'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
                'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
                'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
            }
            vk = special.get(k, 0)
        return (ctypes.windll.user32.GetAsyncKeyState(int(vk)) & 0x8000) != 0

    @staticmethod
    def is_mouse_pressed(button="left"):
        vk = 0x01 if button == "left" else 0x02
        return (ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000) != 0


# =============================================================================
# KEY LOGGER
# Tracks the last non-movement key pressed to verify active hotbar slot.
# =============================================================================

class _SlotTracker:
    """
    Tracks which hotbar slot the player currently has selected.
    Listens for key presses via pynput and latches the active slot key.
    Clears when a different hotbar/slot key is pressed.
    Only slot keys update the active slot — movement and other keys are ignored.
    """
    # Keys considered hotbar / slot selectors — anything else is ignored
    SLOT_KEYS = set('1234567890')

    # Movement + UI keys that should never update the active slot
    _IGNORED = {'w', 'a', 's', 'd', 'q', 'e', 'r', 'f', 'g', 'c', 'v', 'x', 'z',
                'left', 'right', 'middle', 'tab', 'shift', 'ctrl', 'alt',
                'space', 'enter', 'escape', 'backspace', 'caps_lock',
                'button.left', 'button.right', 'button.middle',
                'button.x1', 'button.x2', 'mouse3', 'mouse4', 'mouse5'}

    def __init__(self):
        self._lock = threading.Lock()
        self._active_slot = None
        self._mb1_down = False
        self._mb2_down = False
        
        # Listen for keyboard slots
        self.keyboard_listener = pynput_keyboard.Listener(on_press=self._on_press)
        self.keyboard_listener.start()
        
        # Listen for physical mouse buttons (avoids SendInput loop)
        self.mouse_listener = pynput_mouse.Listener(on_click=self._on_click)
        self.mouse_listener.start()

    def _on_press(self, key):
        try:
            k = key.char.lower()
        except AttributeError:
            k = str(key).replace('Key.', '').lower()

        if k in self._IGNORED or k.startswith('button'):
            return

        # Only recognize numeric keys as slot selectors
        if k not in self.SLOT_KEYS:
            return

        with self._lock:
            self._active_slot = k

    def _on_click(self, x, y, button, pressed):
        with self._lock:
            if button == pynput_mouse.Button.left:
                self._mb1_down = pressed
            elif button == pynput_mouse.Button.right:
                self._mb2_down = pressed

    def get_active_slot(self):
        with self._lock:
            return self._active_slot
            
    def is_mb1_down(self):
        with self._lock:
            return self._mb1_down
            
    def is_mb2_down(self):
        with self._lock:
            return self._mb2_down

    def clear(self):
        with self._lock:
            self._active_slot = None

_slot_tracker = _SlotTracker()

def get_active_item():
    return _slot_tracker.get_active_slot()

def is_mb1_physical_down():
    return _slot_tracker.is_mb1_down()

def is_mb2_physical_down():
    return _slot_tracker.is_mb2_down()


# =============================================================================
# GAME OVERLAY
# =============================================================================

OVERLAY_ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "overlay")
DEFAULT_PRIMARY_ICON = os.path.join(OVERLAY_ASSET_DIR, "primary_assault.svg")
DEFAULT_SECONDARY_ICON = os.path.join(OVERLAY_ASSET_DIR, "secondary_pistol.svg")

def _overlay_icon_path(slot: str) -> str:
    custom = cfg.overlay.primary_icon_path if slot == "primary" else cfg.overlay.secondary_icon_path
    fallback = DEFAULT_PRIMARY_ICON if slot == "primary" else DEFAULT_SECONDARY_ICON
    return custom if custom and os.path.exists(custom) else fallback

def _all_recoil_guns():
    guns = [
        ("RC-4", cfg.rc4, None),
        ("SMG12", cfg.smg12, None),
        ("F2", cfg.f2, None),
        ("Vector .45", cfg.vector, None),
        ("UZK50GI", cfg.uzk50gi, None),
        ("C70", cfg.c70, None),
    ]
    for idx, gun in enumerate(gun_registry.guns):
        guns.append((gun.name, gun, idx))
    return guns

def _format_keybind(key: str) -> str:
    key = str(key or "").strip()
    return key.upper() if key else "Not bound"

def _enabled_overlay_rows():
    rows = []
    for name, settings, _registry_index in _all_recoil_guns():
        if getattr(settings, "enabled", False):
            value = f"{getattr(settings, 'strength', 100)}%"
            if cfg.overlay.show_keybinds and getattr(settings, "toggle_key", ""):
                value = f"{value}  [{_format_keybind(getattr(settings, 'toggle_key', ''))}]"
            rows.append((name, value))

    feature_rows = [
        ("Crystal", cfg.crystal.enabled, f"{cfg.crystal.cps} cps"),
        ("Anchor", cfg.anchor.enabled, f"{cfg.anchor.delay_min}-{cfg.anchor.delay_max} ms"),
        ("XP", cfg.util.xp_enabled, f"{cfg.util.xp_cps} cps"),
        ("Gapple", cfg.util.gapple_enabled, "on"),
        ("Stun", cfg.sword.stun_enabled, f"{cfg.sword.delay_min}-{cfg.sword.delay_max} ms"),
        ("Shield Breaker", cfg.shield_breaker.enabled, f"{cfg.shield_breaker.delay_min}-{cfg.shield_breaker.delay_max} ms"),
        ("Stun Slam", cfg.stun_slam.enabled, f"{cfg.stun_slam.delay_min}-{cfg.stun_slam.delay_max} ms"),
        ("Breach Swap", cfg.breach_swap.enabled, f"{cfg.breach_swap.delay_min}-{cfg.breach_swap.delay_max} ms"),
        ("Cart", cfg.cart.enabled, f"{cfg.cart.rail_delay_min}-{cfg.cart.cart_delay_max} ms"),
        ("Trap Cart", cfg.trap_cart.enabled, f"{cfg.trap_cart.cart_click_count} carts"),
        ("Pearl Catch", cfg.pearl_catch.enabled, f"{cfg.pearl_catch.action_delay_min}-{cfg.pearl_catch.action_delay_max} ms"),
        ("Silly Spinnny", cfg.turnflick.enabled, f"{cfg.turnflick.repeats}x"),
        ("Auto Shoot", cfg.fast_clicker.enabled, f"{cfg.fast_clicker.delay_ms} ms"),
    ]
    for name, enabled, value in feature_rows:
        if enabled:
            rows.append((name, value))
    if cfg.scizo.random_look_on:
        rows.append(("Random Look", "on"))
    if cfg.scizo.thankyou_on:
        rows.append(("Thank You", f"{cfg.scizo.thankyou_interval} ms"))
    return rows[:12]

class OverlayWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(None)
        self._hue = 0
        self._last_slot = None
        self._base_icon_size = 96
        self.setWindowTitle("Obsidian Overlay")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.left_panel = QFrame(self)
        self.left_panel.setObjectName("OverlayPanel")
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(12, 10, 12, 10)
        self.left_layout.setSpacing(6)
        self.title_lbl = QLabel("ACTIVE")
        self.rows_widget = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_widget)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(4)
        self.left_layout.addWidget(self.title_lbl)
        self.left_layout.addWidget(self.rows_widget)

        self.icon_panel = QFrame(self)
        self.icon_panel.setObjectName("OverlayIconPanel")
        self.icon_layout = QVBoxLayout(self.icon_panel)
        self.icon_layout.setContentsMargins(12, 10, 12, 10)
        self.icon_layout.setSpacing(2)
        self.icon_lbl = QLabel()
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slot_lbl = QLabel()
        self.slot_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_layout.addWidget(self.icon_lbl)
        self.icon_layout.addWidget(self.slot_lbl)
        self.icon_glow = QGraphicsDropShadowEffect(self.icon_panel)
        self.icon_glow.setOffset(0, 0)
        self.icon_glow.setBlurRadius(0)
        self.icon_glow.setColor(QColor(0, 0, 0, 0))
        self.icon_panel.setGraphicsEffect(self.icon_glow)
        self.icon_pulse = QPropertyAnimation(self.icon_glow, b"blurRadius", self)
        self.icon_pulse.setDuration(180)
        self.icon_pulse.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(100)
        self.refresh()

    def apply_settings(self):
        visible = bool(cfg.overlay.enabled)
        self.setVisible(visible)
        self.setWindowOpacity(max(15, min(100, cfg.overlay.opacity)) / 100.0)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, bool(cfg.overlay.click_through))
        if visible:
            self._apply_click_through()
            self._position_to_screen()

    def _apply_click_through(self):
        try:
            hwnd = int(self.winId())
            exstyle = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            if cfg.overlay.click_through:
                exstyle |= 0x00000020 | 0x00080000
            else:
                exstyle &= ~0x00000020
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, exstyle)
        except Exception:
            pass

    def _position_to_screen(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        self.setGeometry(geo)
        margin = cfg.overlay.margin
        scale = max(70, min(150, cfg.overlay.scale)) / 100.0
        icon_size = int(self._base_icon_size * scale)
        panel_width = int((280 if not cfg.overlay.compact_mode else 210) * scale)
        row_count = max(1, len(_enabled_overlay_rows()))
        row_height = int((18 if cfg.overlay.compact_mode else 22) * scale)
        panel_height = int(35 * scale) + (row_count * row_height) + 18
        self.left_panel.setFixedWidth(panel_width)
        self.left_panel.setGeometry(margin, margin, panel_width, panel_height)
        self.icon_lbl.setFixedSize(icon_size, int(icon_size * 0.55))
        self.icon_panel.adjustSize()
        self.icon_panel.move(geo.width() - self.icon_panel.width() - margin, margin)

    def _accent(self):
        if not cfg.overlay.rainbow_accent:
            return get_theme()["accent"]
        color = QColor()
        color.setHsv(self._hue % 360, 230, 255)
        self._hue += 4
        return color.name()

    def refresh(self):
        if not cfg.overlay.enabled:
            if self.isVisible():
                self.hide()
            return
        if not self.isVisible():
            self.show()
            self._apply_click_through()

        accent = self._accent()
        t = get_theme()
        panel_bg = f"rgba(8,10,14,{0.30 if cfg.overlay.compact_mode else 0.45})"
        border = _rgba(accent, 0.38 if cfg.overlay.glow else 0.16)
        self.setStyleSheet(f"""
            QFrame#OverlayPanel, QFrame#OverlayIconPanel {{
                background-color: {panel_bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QLabel {{
                color: {t['text']};
                background: transparent;
                font-family: 'Segoe UI','Helvetica Neue',sans-serif;
            }}
        """)
        self.title_lbl.setStyleSheet(f"color:{accent}; font-size:10px; font-weight:900; letter-spacing:2px;")
        self.slot_lbl.setStyleSheet(f"color:{accent}; font-size:10px; font-weight:900; letter-spacing:1px;")

        self._refresh_rows(accent)
        active_slot = get_active_item()
        slot_kind = "secondary" if active_slot == "2" else "primary"
        if slot_kind != self._last_slot and cfg.overlay.pulse_icon:
            pulse_color = QColor(accent)
            pulse_color.setAlpha(150)
            self.icon_glow.setColor(pulse_color)
            self.icon_pulse.stop()
            self.icon_pulse.setStartValue(4)
            self.icon_pulse.setEndValue(28)
            self.icon_pulse.start()
        elif not cfg.overlay.glow:
            self.icon_glow.setColor(QColor(0, 0, 0, 0))
            self.icon_glow.setBlurRadius(0)
        self._last_slot = slot_kind
        self._refresh_icon(slot_kind)
        self._position_to_screen()

    def _refresh_rows(self, accent):
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        rows = _enabled_overlay_rows()
        if not rows:
            empty = QLabel("Nothing armed")
            empty.setStyleSheet("color:rgba(255,255,255,0.55); font-size:12px; font-weight:650;")
            self.rows_layout.addWidget(empty)
            return
        for name, value in rows:
            row = QWidget()
            row.setFixedHeight(18 if cfg.overlay.compact_mode else 22)
            lay = QHBoxLayout(row)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(10)
            name_lbl = QLabel(name)
            val_lbl = QLabel(value)
            name_lbl.setMinimumWidth(0)
            name_lbl.setStyleSheet("color:rgba(255,255,255,0.90); font-size:12px; font-weight:750;")
            val_lbl.setStyleSheet(f"color:{accent}; font-size:12px; font-weight:900;")
            lay.addWidget(name_lbl)
            lay.addStretch()
            lay.addWidget(val_lbl)
            self.rows_layout.addWidget(row)

    def _refresh_icon(self, slot_kind):
        icon_path = _overlay_icon_path(slot_kind)
        pix = QPixmap(icon_path)
        if not pix.isNull():
            pix = pix.scaled(
                self.icon_lbl.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            tinted = QPixmap(pix.size())
            tinted.fill(Qt.GlobalColor.transparent)
            painter = QPainter(tinted)
            painter.drawPixmap(0, 0, pix)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(tinted.rect(), QColor("#f1fbff"))
            painter.end()
            pix = tinted
            self.icon_lbl.setPixmap(pix)
        label = "PRIMARY" if slot_kind == "primary" else "SECONDARY"
        if cfg.overlay.show_slot_label:
            self.slot_lbl.setText(label)
            self.slot_lbl.show()
        else:
            self.slot_lbl.hide()


# =============================================================================
# MACROS
# =============================================================================

class MacroThread(QThread):
    def __init__(self):
        super().__init__()
        self.running = False
        self.input = InputController()

    def run(self):
        self.running = True
        while self.running:
            self.loop()
            time.sleep(0.001)

    def stop(self):
        self.running = False
        self.wait()


class CrystalMacro(MacroThread):
    def loop(self):
        if not cfg.crystal.master_enabled or not cfg.crystal.enabled:
            time.sleep(0.1)
            return

        # Check active slot matches crystal slot
        if get_active_item() != cfg.crystal.crystal_slot.lower():
            time.sleep(0.02)
            return

        if not self.input.is_mouse_pressed("right"):
            time.sleep(0.02)
            return

        # Inner loop — spam both left and right click while on crystal slot
        while (get_active_item() == cfg.crystal.crystal_slot.lower()
               and self.input.is_mouse_pressed("right")):
            delay = random.uniform(cfg.crystal.place_to_break_delay_min, cfg.crystal.place_to_break_delay_max)
            time.sleep(delay / 1000.0)
            # Send right click (place) and left click (break) together
            self.input._send_input([
                self.input._create_mouse_input(MOUSEEVENTF_RIGHTDOWN),
                self.input._create_mouse_input(MOUSEEVENTF_RIGHTUP),
                self.input._create_mouse_input(MOUSEEVENTF_LEFTDOWN),
                self.input._create_mouse_input(MOUSEEVENTF_LEFTUP),
            ])
            cps = max(1, min(20, cfg.crystal.cps))
            budget = 1.0 / cps
            time.sleep(max(0.0, budget - delay / 1000.0))

            if not cfg.crystal.hold_to_repeat:
                break

        if not cfg.crystal.hold_to_repeat:
            while self.input.is_mouse_pressed("right"):
                time.sleep(0.05)


class AnchorMacro(MacroThread):
    def __init__(self):
        super().__init__()
        self.last_run = 0

    def _delay(self):
        time.sleep(random.uniform(cfg.anchor.delay_min, cfg.anchor.delay_max) / 1000.0)

    def _run_sequence(self):
        self.input.press_key(cfg.anchor.anchor_slot)
        self._delay()
        for _ in range(cfg.anchor.anchor_count_max):
            self.input.right_click()
            self._delay()
        self.input.press_key(cfg.anchor.glowstone_slot)
        self._delay()
        glow_count = random.randint(1, max(1, cfg.anchor.glowstone_count_max))
        for _ in range(glow_count):
            self.input.right_click()
            self._delay()
        self.input.press_key(cfg.anchor.totem_slot)
        self._delay()
        for _ in range(cfg.anchor.totem_count_max):
            self.input.right_click()
            self._delay()

    def loop(self):
        if not cfg.anchor.enabled:
            time.sleep(0.1)
            return
        if self.input.is_key_pressed(cfg.anchor.activator_key):
            if time.time() - self.last_run < 0.3:
                return
            self.last_run = time.time()
            self._run_sequence()
            if cfg.anchor.hold_to_repeat:
                while self.input.is_key_pressed(cfg.anchor.activator_key):
                    cooldown = random.uniform(cfg.anchor.delay_min, cfg.anchor.delay_max) / 2 / 1000.0
                    time.sleep(cooldown)
                    if not self.input.is_key_pressed(cfg.anchor.activator_key):
                        break
                    self._run_sequence()
            else:
                while self.input.is_key_pressed(cfg.anchor.activator_key):
                    time.sleep(0.05)


class UtilityMacro(MacroThread):
    def loop(self):
        if cfg.util.xp_enabled and self.input.is_key_pressed(cfg.util.xp_key):
            self.input.press_key(cfg.util.xp_slot)
            time.sleep(0.01)
            self.input.right_click()
            time.sleep(1.0 / max(1, cfg.util.xp_cps))
        if cfg.util.gapple_enabled and self.input.is_key_pressed(cfg.util.gapple_key):
            self.input.press_key(cfg.util.gapple_slot)
            time.sleep(0.02)
            self.input.right_click()
            time.sleep(0.01)


class StunMacro(MacroThread):
    def _do_stun(self):
        self.input.press_key(cfg.sword.axe_slot)
        delay = random.uniform(cfg.sword.delay_min, cfg.sword.delay_max) / 1000.0
        time.sleep(delay)
        self.input.left_click()
        time.sleep(delay)
        self.input.left_click()

    def loop(self):
        if not cfg.sword.stun_enabled:
            time.sleep(0.1)
            return
        if self.input.is_key_pressed(cfg.sword.activator_key):
            self._do_stun()
            while self.input.is_key_pressed(cfg.sword.activator_key):
                time.sleep(0.05)


class ShieldBreakerMacro(MacroThread):
    def loop(self):
        if not cfg.shield_breaker.enabled:
            time.sleep(0.1)
            return
        if self.input.is_key_pressed(cfg.shield_breaker.activator_key):
            delay = random.uniform(cfg.shield_breaker.delay_min, cfg.shield_breaker.delay_max) / 1000.0
            self.input.press_key(cfg.shield_breaker.axe_slot)
            time.sleep(delay)
            self.input.left_click()
            time.sleep(delay)
            self.input.press_key(cfg.shield_breaker.sword_slot)
            while self.input.is_key_pressed(cfg.shield_breaker.activator_key):
                time.sleep(0.05)


class StunSlamMacro(MacroThread):
    def loop(self):
        if not cfg.stun_slam.enabled:
            time.sleep(0.1)
            return
        if self.input.is_key_pressed(cfg.stun_slam.activator_key):
            delay = random.uniform(cfg.stun_slam.delay_min, cfg.stun_slam.delay_max) / 1000.0
            self.input.press_key(cfg.stun_slam.axe_slot)
            time.sleep(delay)
            self.input.left_click()
            time.sleep(delay)
            self.input.press_key(cfg.stun_slam.mace_slot)
            time.sleep(delay)
            self.input.left_click()
            time.sleep(delay)
            if cfg.stun_slam.return_to_sword:
                self.input.press_key(cfg.stun_slam.sword_slot)
            while self.input.is_key_pressed(cfg.stun_slam.activator_key):
                time.sleep(0.05)


class BreachSwapMacro(MacroThread):
    def loop(self):
        if not cfg.breach_swap.enabled:
            time.sleep(0.1)
            return
        if self.input.is_key_pressed(cfg.breach_swap.activator_key):
            # Sequence: left click → delay → swap slot → delay → sword slot
            delay = random.uniform(cfg.breach_swap.delay_min, min(cfg.breach_swap.delay_max, 80)) / 1000.0
            self.input.left_click()
            time.sleep(delay)
            self.input.press_key(cfg.breach_swap.swap_slot)
            time.sleep(delay)
            self.input.press_key(cfg.breach_swap.sword_slot)
            while self.input.is_key_pressed(cfg.breach_swap.activator_key):
                time.sleep(0.05)


class CartMacro(MacroThread):
    def loop(self):
        if not cfg.cart.enabled:
            time.sleep(0.1)
            return
        if self.input.is_key_pressed(cfg.cart.activator_key):
            # Switch to bow and hold right click for as long as activator is held
            self.input.press_key(cfg.cart.bow_slot)
            time.sleep(0.01)
            self.input._send_input([self.input._create_mouse_input(MOUSEEVENTF_RIGHTDOWN)])
            while self.input.is_key_pressed(cfg.cart.activator_key):
                time.sleep(0.005)
            self.input._send_input([self.input._create_mouse_input(MOUSEEVENTF_RIGHTUP)])
            time.sleep(0.010)  # wait for arrow to actually release/fire
            # Rail slot + right click
            rail_delay = random.uniform(cfg.cart.rail_delay_min, cfg.cart.rail_delay_max) / 1000.0
            time.sleep(rail_delay)
            self.input.press_key(cfg.cart.rail_slot)
            time.sleep(rail_delay)
            self.input.right_click()
            # Cart slot + right click
            cart_delay = random.uniform(cfg.cart.cart_delay_min, cfg.cart.cart_delay_max) / 1000.0
            time.sleep(cart_delay)
            self.input.press_key(cfg.cart.cart_slot)
            time.sleep(cart_delay)
            self.input.right_click()


class TrapCartMacro(MacroThread):
    def loop(self):
        if not cfg.trap_cart.enabled:
            time.sleep(0.1)
            return
        if self.input.is_key_pressed(cfg.trap_cart.activator_key):
            # 1. Rail slot → right click (place rail)
            rail_delay = random.uniform(cfg.trap_cart.rail_delay_min, cfg.trap_cart.rail_delay_max) / 1000.0
            self.input.press_key(cfg.trap_cart.rail_slot)
            time.sleep(rail_delay)
            self.input.right_click()
            # 2. Cart slot → right click multiple times (place cart)
            cart_delay = random.uniform(cfg.trap_cart.cart_delay_min, cfg.trap_cart.cart_delay_max) / 1000.0
            time.sleep(cart_delay)
            self.input.press_key(cfg.trap_cart.cart_slot)
            time.sleep(cart_delay)
            for _ in range(max(1, cfg.trap_cart.cart_click_count)):
                self.input.right_click()
                time.sleep(cart_delay)
            # 3. Look down smoothly (split into small steps for human feel)
            look_dy = random.randint(cfg.trap_cart.look_down_min, cfg.trap_cart.look_down_max)
            steps_down = random.randint(3, 6)
            moved_down = 0
            for i in range(steps_down):
                step = look_dy // steps_down if i < steps_down - 1 else look_dy - moved_down
                self.input.move_mouse_relative(0, step)
                moved_down += step
                time.sleep(random.uniform(0.006, 0.014))
            look_delay = random.uniform(cfg.trap_cart.look_delay_min, cfg.trap_cart.look_delay_max) / 1000.0
            time.sleep(look_delay)
            # 4. Fire slot → right click (place fire charge)
            fire_delay = random.uniform(cfg.trap_cart.fire_delay_min, cfg.trap_cart.fire_delay_max) / 1000.0
            self.input.press_key(cfg.trap_cart.fire_slot)
            time.sleep(fire_delay)
            self.input.right_click()
            # 5. Look back up fully before shooting
            look_up_pct = random.uniform(cfg.trap_cart.look_up_min, cfg.trap_cart.look_up_max) / 100.0
            look_up_total = int(round(look_dy * look_up_pct))
            steps_up = random.randint(3, 6)
            moved_up = 0
            for i in range(steps_up):
                step = look_up_total // steps_up if i < steps_up - 1 else look_up_total - moved_up
                self.input.move_mouse_relative(0, -step)
                moved_up += step
                time.sleep(random.uniform(0.006, 0.014))
            # 6. Crossbow slot → right click (shoot)
            shoot_delay = random.uniform(cfg.trap_cart.shoot_delay_min, cfg.trap_cart.shoot_delay_max) / 1000.0
            time.sleep(shoot_delay)
            self.input.press_key(cfg.trap_cart.crossbow_slot)
            time.sleep(shoot_delay)
            self.input.right_click()
            while self.input.is_key_pressed(cfg.trap_cart.activator_key):
                time.sleep(0.05)


class PearlCatchMacro(MacroThread):
    @staticmethod
    def _smooth_up(ctrl, pixels):
        steps = random.randint(4, 7)
        moved = 0
        for i in range(steps):
            step = pixels // steps if i < steps - 1 else pixels - moved
            ctrl.move_mouse_relative(0, -step)
            moved += step
            time.sleep(random.uniform(0.007, 0.015))

    def loop(self):
        if not cfg.pearl_catch.enabled:
            time.sleep(0.1)
            return
        if self.input.is_key_pressed(cfg.pearl_catch.activator_key):
            delay = random.uniform(cfg.pearl_catch.action_delay_min, cfg.pearl_catch.action_delay_max) / 1000.0
            look_px = random.randint(cfg.pearl_catch.look_up_min, cfg.pearl_catch.look_up_max)
            self._smooth_up(self.input, look_px)
            time.sleep(delay)
            self.input.press_key(cfg.pearl_catch.pearl_slot)
            time.sleep(delay)
            self.input.right_click()
            time.sleep(delay)
            self.input.press_key(cfg.pearl_catch.wind_slot)
            time.sleep(delay)
            self.input.right_click()
            time.sleep(delay)
            self.input.press_key(cfg.pearl_catch.original_slot)
            self._smooth_up(self.input, -look_px)
            while self.input.is_key_pressed(cfg.pearl_catch.activator_key):
                time.sleep(0.05)


class FastClickerMacro(MacroThread):
    """Auto Shoot - spams left click when BOTH MB1 and MB2 are held, IF no gun is selected."""
    def loop(self):
        s = cfg.fast_clicker
        if not s.enabled:
            time.sleep(0.1)
            return

        # Check physical button states from our SlotTracker hook
        mb1 = is_mb1_physical_down()
        mb2 = is_mb2_physical_down()

        # While both are physically held, keep clicking
        while mb1 and mb2 and self.running and s.enabled:
            active_slot = get_active_item()
            
            is_gun = False
            # 1. Check built-in gun slots (default 1 and 2)
            if active_slot == '1' and (cfg.rc4.enabled or cfg.f2.enabled or cfg.vector.enabled or cfg.uzk50gi.enabled):
                is_gun = True
            elif active_slot == '2' and (cfg.smg12.enabled or cfg.c70.enabled):
                is_gun = True
                
            # 2. Check custom gun slots
            if not is_gun:
                for gun in gun_registry.guns:
                    if gun.enabled and active_slot == str(gun.slot_key):
                        is_gun = True
                        break

            if is_gun:
                break # Stop clicking if we switched to a gun

            # Force a click by releasing and re-pressing MB1
            # We send UP, sleep a tiny bit (10ms), then send DOWN
            self.input._send_input([self.input._create_mouse_input(MOUSEEVENTF_LEFTUP)])
            time.sleep(0.01) # 10ms release time
            self.input._send_input([self.input._create_mouse_input(MOUSEEVENTF_LEFTDOWN)])
            
            # Base delay + random offset
            # We subtract 10ms from the user-defined base delay to keep the overall frequency accurate
            base = max(0, s.delay_ms - 10)
            off = s.offset_ms
            delay = base + random.uniform(-off, off)
            time.sleep(max(0.001, delay / 1000.0))

            # Refresh physical button states for next iteration
            mb1 = is_mb1_physical_down()
            mb2 = is_mb2_physical_down()
        
        time.sleep(0.01)

class RC4Macro(MacroThread):
    """
    RC-4: activates when keyboard '1' was the last gun key pressed and MB1+MB2 held.
    MB3 clears the latch (ability key, disables recoil).
    100% = 18 down, 1 left.
    """
    def __init__(self):
        super().__init__()
        self._key1_seen = False
        self._active = False

    def run(self):
        self.running = True
        while self.running:
            if not cfg.rc4.enabled:
                self._key1_seen = False
                self._active = False
                time.sleep(0.1)
                continue

            mb1 = self.input.is_mouse_pressed("left")
            mb2 = self.input.is_mouse_pressed("right")
            mb3 = (ctypes.windll.user32.GetAsyncKeyState(0x04) & 0x8000) != 0
            key1 = (ctypes.windll.user32.GetAsyncKeyState(0x31) & 0x8000) != 0
            key2 = (ctypes.windll.user32.GetAsyncKeyState(0x32) & 0x8000) != 0

            if mb3:
                self._key1_seen = False
            elif key1:
                self._key1_seen = True
            elif key2:
                self._key1_seen = False

            self._active = mb1 and mb2 and self._key1_seen

            if self._active:
                pct = cfg.rc4.strength / 100.0
                dy = 17 * pct * sens_scale('vertical')
                dx = -1 * pct * sens_scale('horizontal')
                jitter_max = 1.0 + (1 - pct) * 1.5
                dx += random.uniform(-jitter_max, jitter_max)
                dy += random.uniform(-jitter_max, jitter_max)
                dx = round(dx)
                dy = round(dy)
                if dx != 0 or dy != 0:
                    self.input.move_mouse_relative(dx, dy)
                time.sleep(0.016)
            else:
                time.sleep(0.008)


class SMG12Macro(MacroThread):
    """
    SMG12: activates when keyboard '2' was the last gun key pressed and MB1+MB2 held.
    MB3 clears the latch (ability key, disables recoil).
    100% = 11 down, net 2 right.
    """
    def __init__(self):
        super().__init__()
        self._key2_seen = False
        self._active = False

    def run(self):
        self.running = True
        while self.running:
            if not cfg.smg12.enabled:
                self._key2_seen = False
                self._active = False
                time.sleep(0.1)
                continue

            mb1 = self.input.is_mouse_pressed("left")
            mb2 = self.input.is_mouse_pressed("right")
            mb3 = (ctypes.windll.user32.GetAsyncKeyState(0x04) & 0x8000) != 0
            key1 = (ctypes.windll.user32.GetAsyncKeyState(0x31) & 0x8000) != 0
            key2 = (ctypes.windll.user32.GetAsyncKeyState(0x32) & 0x8000) != 0

            if mb3:
                self._key2_seen = False
            elif key2:
                self._key2_seen = True
            elif key1:
                self._key2_seen = False

            self._active = mb1 and mb2 and self._key2_seen

            if self._active:
                pct = cfg.smg12.strength / 100.0
                dy = 11 * pct * sens_scale('vertical')
                dx = 2 * pct * sens_scale('horizontal')
                jitter_max = 1.0 + (1 - pct) * 1.5
                dx += random.uniform(-jitter_max, jitter_max)
                dy += random.uniform(-jitter_max, jitter_max)
                dx = round(dx)
                dy = round(dy)
                if dx != 0 or dy != 0:
                    self.input.move_mouse_relative(dx, dy)
                time.sleep(0.016)
            else:
                time.sleep(0.008)


class F2Macro(MacroThread):
    """
    F2: activates when keyboard '1' was the last gun key pressed and MB1+MB2 held.
    RC-4 style latch — key1 arms it, key2/key3/MB3 clear it.
    Down and right pixel values are user-configurable (temporary).
    Jitter scales from ±1px at 100% strength down to ±2.5px at 0%.
    """
    def __init__(self):
        super().__init__()
        self._key1_seen = False
        self._active = False

    def run(self):
        self.running = True
        while self.running:
            if not cfg.f2.enabled:
                self._key1_seen = False
                self._active = False
                time.sleep(0.1)
                continue

            mb1 = self.input.is_mouse_pressed("left")
            mb2 = self.input.is_mouse_pressed("right")
            mb3 = (ctypes.windll.user32.GetAsyncKeyState(0x04) & 0x8000) != 0
            key1 = (ctypes.windll.user32.GetAsyncKeyState(0x31) & 0x8000) != 0
            key2 = (ctypes.windll.user32.GetAsyncKeyState(0x32) & 0x8000) != 0
            key3 = (ctypes.windll.user32.GetAsyncKeyState(0x33) & 0x8000) != 0

            if mb3:
                self._key1_seen = False
            elif key1:
                self._key1_seen = True
            elif key2 or key3:
                self._key1_seen = False

            self._active = mb1 and mb2 and self._key1_seen

            if self._active:
                pct = cfg.f2.strength / 100.0
                dy = 19 * pct * sens_scale('vertical')
                dx = -1 * pct * sens_scale('horizontal')
                jitter_max = 1.0 + (1 - pct) * 1.5
                dx += random.uniform(-jitter_max, jitter_max)
                dy += random.uniform(-jitter_max, jitter_max)
                dx = round(dx)
                dy = round(dy)
                if dx != 0 or dy != 0:
                    self.input.move_mouse_relative(dx, dy)
                time.sleep(0.016)
            else:
                time.sleep(0.008)


class VectorMacro(MacroThread):
    """
    Vector .45 ACP — PRIMARY.
    key1 arms, key2/MB3 clear (same latch logic as RC-4).
    100% = 8 down, 0 left, 0 right. Jitter ±1px at 100%, ±2.5px at 0%.
    """
    def __init__(self):
        super().__init__()
        self._key1_seen = False

    def run(self):
        self.running = True
        while self.running:
            if not cfg.vector.enabled:
                self._key1_seen = False
                time.sleep(0.1)
                continue

            mb1 = self.input.is_mouse_pressed("left")
            mb2 = self.input.is_mouse_pressed("right")
            mb3 = (ctypes.windll.user32.GetAsyncKeyState(0x04) & 0x8000) != 0
            key1 = (ctypes.windll.user32.GetAsyncKeyState(0x31) & 0x8000) != 0
            key2 = (ctypes.windll.user32.GetAsyncKeyState(0x32) & 0x8000) != 0

            if mb3:
                self._key1_seen = False
            elif key1:
                self._key1_seen = True
            elif key2:
                self._key1_seen = False

            if mb1 and mb2 and self._key1_seen:
                pct = cfg.vector.strength / 100.0
                dy = 8 * pct * sens_scale('vertical')
                dx = 0 * sens_scale('horizontal')
                jitter_max = 1.0 + (1 - pct) * 1.5
                dx += random.uniform(-jitter_max, jitter_max)
                dy += random.uniform(-jitter_max, jitter_max)
                dx = round(dx)
                dy = round(dy)
                if dx != 0 or dy != 0:
                    self.input.move_mouse_relative(dx, dy)
                time.sleep(0.016)
            else:
                time.sleep(0.008)


class UZK50GIMacro(MacroThread):
    """
    UZK50GI — PRIMARY.
    key1 arms, key2/MB3 clear (same latch logic as RC-4).
    100% = 4 down, 0 left, 0 right. Jitter ±1px at 100%, ±2.5px at 0%.
    """
    def __init__(self):
        super().__init__()
        self._key1_seen = False

    def run(self):
        self.running = True
        while self.running:
            if not cfg.uzk50gi.enabled:
                self._key1_seen = False
                time.sleep(0.1)
                continue

            mb1 = self.input.is_mouse_pressed("left")
            mb2 = self.input.is_mouse_pressed("right")
            mb3 = (ctypes.windll.user32.GetAsyncKeyState(0x04) & 0x8000) != 0
            key1 = (ctypes.windll.user32.GetAsyncKeyState(0x31) & 0x8000) != 0
            key2 = (ctypes.windll.user32.GetAsyncKeyState(0x32) & 0x8000) != 0

            if mb3:
                self._key1_seen = False
            elif key1:
                self._key1_seen = True
            elif key2:
                self._key1_seen = False

            if mb1 and mb2 and self._key1_seen:
                pct = cfg.uzk50gi.strength / 100.0
                dy = 4 * pct * sens_scale('vertical')
                dx = 0 * sens_scale('horizontal')
                jitter_max = 1.0 + (1 - pct) * 1.5
                dx += random.uniform(-jitter_max, jitter_max)
                dy += random.uniform(-jitter_max, jitter_max)
                dx = round(dx)
                dy = round(dy)
                if dx != 0 or dy != 0:
                    self.input.move_mouse_relative(dx, dy)
                time.sleep(0.016)
            else:
                time.sleep(0.008)


class C70Macro(MacroThread):
    """
    C70 — SECONDARY.
    key2 arms, key1/MB3 clear (same latch logic as SMG12).
    100% = 7 down, 0 left, 1 right. Jitter ±1px at 100%, ±2.5px at 0%.
    """
    def __init__(self):
        super().__init__()
        self._key2_seen = False

    def run(self):
        self.running = True
        while self.running:
            if not cfg.c70.enabled:
                self._key2_seen = False
                time.sleep(0.1)
                continue

            mb1 = self.input.is_mouse_pressed("left")
            mb2 = self.input.is_mouse_pressed("right")
            mb3 = (ctypes.windll.user32.GetAsyncKeyState(0x04) & 0x8000) != 0
            key1 = (ctypes.windll.user32.GetAsyncKeyState(0x31) & 0x8000) != 0
            key2 = (ctypes.windll.user32.GetAsyncKeyState(0x32) & 0x8000) != 0

            if mb3:
                self._key2_seen = False
            elif key2:
                self._key2_seen = True
            elif key1:
                self._key2_seen = False

            if mb1 and mb2 and self._key2_seen:
                pct = cfg.c70.strength / 100.0
                dy = 7 * pct * sens_scale('vertical')
                dx = 1 * pct * sens_scale('horizontal')
                jitter_max = 1.0 + (1 - pct) * 1.5
                dx += random.uniform(-jitter_max, jitter_max)
                dy += random.uniform(-jitter_max, jitter_max)
                dx = round(dx)
                dy = round(dy)
                if dx != 0 or dy != 0:
                    self.input.move_mouse_relative(dx, dy)
                time.sleep(0.016)
            else:
                time.sleep(0.008)


# =============================================================================

class TurnFlickMacro(MacroThread):
    """
    Silly Spinnny: while the activator key is held, repeatedly runs one full
    configured turn sequence. It waits for a sequence to end before beginning
    the next one, but release checks happen before every movement so letting go
    stops immediately.
    """
    def __init__(self):
        super().__init__()

    def loop(self):
        if not cfg.turnflick.enabled:
            time.sleep(0.05)
            return

        if self.input.is_key_pressed(cfg.turnflick.activator_key):
            while self.running and cfg.turnflick.enabled and self.input.is_key_pressed(cfg.turnflick.activator_key):
                completed = self._do_flick_sequence()
                if not completed:
                    break
        else:
            time.sleep(0.005)

    def _do_flick_sequence(self):
        s = cfg.turnflick
        base_px = max(1, round(s.pixels * sens_scale('horizontal')))
        sign = 1 if s.direction == "right" else -1
        repeats = max(1, min(100, s.repeats))
        for i in range(repeats):
            if not self.input.is_key_pressed(s.activator_key):
                return False
            variance = random.uniform(0.10, 0.40)
            if random.random() < 0.5:
                px = round(base_px * (1.0 + variance))
            else:
                px = round(base_px * (1.0 - variance))
            px = max(1, px)
            moved = 0
            steps = max(3, min(12, px // 12))
            for step_index in range(steps):
                if not self.input.is_key_pressed(s.activator_key):
                    return False
                step_px = px // steps if step_index < steps - 1 else px - moved
                moved += step_px
                self.input.move_mouse_relative(sign * step_px, 0)
                time.sleep(0.001)
            if i < repeats - 1:
                end = time.time() + 0.008
                while time.time() < end:
                    if not self.input.is_key_pressed(s.activator_key):
                        return False
                    time.sleep(0.001)
        return True


# =============================================================================

class ScizoMacro(MacroThread):
    """
    Scizo Mode — a single toggle keybind arms all enabled sub-features at once.
    Sub-features run concurrently in their own daemon threads while active.

    1. Random Look   — every ~300–600 ms nudges the mouse 70-250 px in a random
                       direction, then snaps back 50 ms later.
    2. Thank You     — spams 'c' (crouch/wave) on a user-defined interval.
    """

    def __init__(self):
        super().__init__()
        self._key_was_down = False
        self._active = False          # master running state for sub-threads
        self._sub_threads: list[threading.Thread] = []

    # ── Main polling loop ────────────────────────────────────────────────────
    def loop(self):
        s = cfg.scizo
        down = self.input.is_key_pressed(s.activator_key)

        if down and not self._key_was_down:
            self._key_was_down = True
            if self._active:
                self._stop_subs()
            else:
                self._start_subs()
        elif not down:
            self._key_was_down = False

        time.sleep(0.02)

    # ── Sub-thread management ────────────────────────────────────────────────
    def _start_subs(self):
        self._active = True
        s = cfg.scizo
        pairs = [
            (s.random_look_on,    self._run_random_look),
            (s.thankyou_on,       self._run_thankyou),
        ]
        for armed, fn in pairs:
            if armed:
                t = threading.Thread(target=fn, daemon=True)
                t.start()
                self._sub_threads.append(t)

    def _stop_subs(self):
        self._active = False
        self._sub_threads.clear()   # daemon threads die on their own next check

    # ── Sub-feature 1: Random Look ───────────────────────────────────────────
    def _run_random_look(self):
        while self._active:
            # random wait between moves
            time.sleep(random.uniform(0.3, 0.6))
            if not self._active:
                break
            # pick a random direction and distance
            angle = random.uniform(0, 2 * 3.14159)
            dist  = random.randint(70, 250)
            dx = round(dist * (dist ** 0 * (1 if random.random() > 0.5 else -1)))
            dy = round(dist * (1 if random.random() > 0.5 else -1))
            # simpler: just random x and y independently in ±70..250 range
            dx = random.choice([-1, 1]) * random.randint(70, 250)
            dy = random.choice([-1, 1]) * random.randint(70, 250)
            self.input.move_mouse_relative(dx, dy)
            time.sleep(0.05)
            if not self._active:
                break
            # snap back
            self.input.move_mouse_relative(-dx, -dy)

    # ── Sub-feature 2: Thank You (spam C) ────────────────────────────────────
    def _run_thankyou(self):
        while self._active:
            self.input.press_key('c')
            interval_ms = cfg.scizo.thankyou_interval
            time.sleep(interval_ms / 1000.0)

    # ── Clean shutdown ───────────────────────────────────────────────────────
    def stop(self):
        self._stop_subs()
        super().stop()


# =============================================================================

class CustomGunMacro(MacroThread):
    """Drives a single user-defined gun from the registry."""

    def __init__(self, gun: CustomGunSettings):
        super().__init__()
        self.gun = gun
        self._key_seen = False

    def run(self):
        self.running = True
        while self.running:
            g = self.gun
            if not g.enabled:
                self._key_seen = False
                time.sleep(0.1)
                continue

            mb1 = self.input.is_mouse_pressed("left")
            mb2 = self.input.is_mouse_pressed("right")
            mb3 = (ctypes.windll.user32.GetAsyncKeyState(0x04) & 0x8000) != 0
            key1 = (ctypes.windll.user32.GetAsyncKeyState(0x31) & 0x8000) != 0
            key2 = (ctypes.windll.user32.GetAsyncKeyState(0x32) & 0x8000) != 0

            arm_key  = key1 if g.slot_key == 1 else key2
            clear_key = key2 if g.slot_key == 1 else key1

            if mb3:
                self._key_seen = False
            elif arm_key:
                self._key_seen = True
            elif clear_key:
                self._key_seen = False

            if mb1 and mb2 and self._key_seen:
                pct = g.strength / 100.0
                dy = g.dy * pct * sens_scale('vertical')
                dx = g.dx * pct * sens_scale('horizontal')
                jitter_max = 1.0 + (1 - pct) * 1.5
                dx += random.uniform(-jitter_max, jitter_max)
                dy += random.uniform(-jitter_max, jitter_max)
                dx = round(dx)
                dy = round(dy)
                if dx != 0 or dy != 0:
                    self.input.move_mouse_relative(dx, dy)
                time.sleep(0.016)
            else:
                time.sleep(0.008)


class ToggleButton(QPushButton):
    toggled_state = pyqtSignal(bool)

    def __init__(self, text="OFF", checked=False, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(58)
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setOffset(0, 0)
        self._shadow.setBlurRadius(0)
        self._shadow.setColor(QColor(0, 0, 0, 0))
        self.setGraphicsEffect(self._shadow)
        self._pulse_anim = QPropertyAnimation(self._shadow, b"blurRadius", self)
        self._pulse_anim.setDuration(180)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.update_style()
        self.clicked.connect(self.on_click)

    def on_click(self):
        self.update_style()
        self._pulse_anim.stop()
        self._pulse_anim.setStartValue(4)
        self._pulse_anim.setEndValue(18 if self.isChecked() else 8)
        self._pulse_anim.start()
        self.toggled_state.emit(self.isChecked())

    def update_style(self):
        t = get_theme()
        if self.isChecked():
            r, g, b = _hex_to_rgb(t['accent'])
            self._shadow.setColor(QColor(r, g, b, 90))
        else:
            self._shadow.setColor(QColor(0, 0, 0, 0))
        if self.isChecked():
            self.setText("ON")
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t['accent']};
                    color: #000;
                    font-weight: 700;
                    border-radius: 7px;
                    padding: 5px 14px;
                    border: none;
                    font-size: 12px;
                }}
            """)
        else:
            self.setText("OFF")
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(255,255,255,0.055);
                    color: {t['subtext']};
                    font-weight: 700;
                    border-radius: 7px;
                    padding: 5px 14px;
                    border: 1px solid {t['border']};
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    color: {t['text']};
                    border-color: {t['accent']};
                    background-color: rgba(255,255,255,0.085);
                }}
            """)


class KeybindButton(QPushButton):
    key_changed = pyqtSignal(str)

    def __init__(self, current_key, parent=None):
        super().__init__(_format_keybind(current_key), parent)
        self.listening = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._apply_style()

    def _apply_style(self):
        t = get_theme()
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255,255,255,0.055);
                border: 1px solid {_rgba(t['text'], 0.10)};
                border-radius: 7px;
                color: {t['text']};
                padding: 6px 11px;
                min-width: 72px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{ border-color: {t['accent']}; color: {t['accent']}; background-color: {_rgba(t['accent'], 0.10)}; }}
        """)

    def mousePressEvent(self, event: QMouseEvent):
        if not self.listening:
            self.listening = True
            self.setText("...")
            self.setFocus()
            return
        else:
            key_name = None
            if event.button() == Qt.MouseButton.MiddleButton:
                key_name = "mouse3"
            elif event.button() == Qt.MouseButton.XButton1:
                key_name = "mouse4"
            elif event.button() == Qt.MouseButton.XButton2:
                key_name = "mouse5"
            if key_name:
                self.finish_input(key_name)
                return
        super().mousePressEvent(event)

    def event(self, event):
        # Intercept Tab key before Qt's focus-traversal system consumes it
        if self.listening and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Tab:
                self.finish_input("tab")
                return True
        return super().event(event)

    def keyPressEvent(self, event: QKeyEvent):
        if self.listening:
            key = event.key()
            if key >= Qt.Key.Key_0 and key <= Qt.Key.Key_9:
                kn = chr(key)
            elif key >= Qt.Key.Key_A and key <= Qt.Key.Key_Z:
                kn = chr(key).lower()
            elif key >= Qt.Key.Key_F1 and key <= Qt.Key.Key_F12:
                kn = f"f{key - Qt.Key.Key_F1 + 1}"
            else:
                special = {Qt.Key.Key_Shift: "shift", Qt.Key.Key_Control: "ctrl", Qt.Key.Key_Space: "space", Qt.Key.Key_Tab: "tab"}
                kn = special.get(key, event.text().lower() or "unknown")
            self.finish_input(kn)
        else:
            super().keyPressEvent(event)

    def finish_input(self, kn):
        self.listening = False
        self.setText(kn.upper())
        self.clearFocus()
        self.key_changed.emit(kn)


class DelayRangeRow(QWidget):
    """Two text boxes [min] — [max] with live validation. Styled via global QSS."""
    changed = pyqtSignal(int, int)

    def __init__(self, min_val: int, max_val: int, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._min = QLineEdit(str(min_val))
        self._max = QLineEdit(str(max_val))
        self._sep = QLabel("—")
        self._sep.setObjectName("DelaySep")

        for box in (self._min, self._max):
            box.setObjectName("DelayBox")
            box.setFixedWidth(58)

        layout.addWidget(self._min)
        layout.addWidget(self._sep)
        layout.addWidget(self._max)

        self._min.editingFinished.connect(self._on_change)
        self._max.editingFinished.connect(self._on_change)

    def _on_change(self):
        try:
            lo = max(0, int(self._min.text()))
            hi = max(lo, int(self._max.text()))
        except ValueError:
            return
        self._min.setText(str(lo))
        self._max.setText(str(hi))
        self.changed.emit(lo, hi)


class Card(QFrame):
    def __init__(self, title, desc, badge="", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setProperty("active", "false")
        self._title_str = title
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(0)

        # ── Header row: badge + title/desc + toggle ──
        header = QHBoxLayout()
        header.setSpacing(12)

        self.badge_label = None
        if badge:
            self.badge_label = QLabel(badge)
            self.badge_label.setObjectName("BadgeLabel")
            self.badge_label.setFixedSize(38, 38)
            self.badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header.addWidget(self.badge_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("CardTitle")
        self.desc_label = QLabel(desc)
        self.desc_label.setObjectName("CardDesc")
        self.desc_label.setWordWrap(True)
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.desc_label)

        self.toggle = ToggleButton()
        self.toggle.toggled_state.connect(self.update_appearance)

        header.addLayout(title_col)
        header.addStretch()
        header.addWidget(self.toggle)
        outer.addLayout(header)

        # ── Divider ──
        t = get_theme()
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"background-color: {t['border']}; max-height:1px; margin: 12px 0 10px 0;")
        outer.addWidget(div)

        # ── Content area ──
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        outer.addWidget(self.content_widget)

        self.glow = QGraphicsDropShadowEffect(self)
        self.glow.setBlurRadius(18)
        self.glow.setColor(QColor(0, 0, 0, 0))
        self.glow.setOffset(0, 4)
        self.setGraphicsEffect(self.glow)
        self._glow_anim = QPropertyAnimation(self.glow, b"blurRadius", self)
        self._glow_anim.setDuration(220)
        self._glow_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def make_click_toggle(self, hide_toggle=True):
        if hide_toggle:
            self.toggle.setVisible(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        def _toggle_from_card(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.toggle.click()
                event.accept()
                return
            super(Card, self).mousePressEvent(event)

        self.mousePressEvent = _toggle_from_card
        click_targets = [self.title_label, self.desc_label]
        if self.badge_label is not None:
            click_targets.append(self.badge_label)
        for target in click_targets:
            target.setCursor(Qt.CursorShape.PointingHandCursor)
            target.mousePressEvent = _toggle_from_card
        return self

    def update_appearance(self, active):
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        t = get_theme()
        if active:
            r, g, b = _hex_to_rgb(t['accent'])
            self.glow.setColor(QColor(r, g, b, 72))
            self._animate_glow(30)
        else:
            self.glow.setColor(QColor(0, 0, 0, 0))
            self._animate_glow(18)

    def _animate_glow(self, radius):
        self._glow_anim.stop()
        self._glow_anim.setStartValue(self.glow.blurRadius())
        self._glow_anim.setEndValue(radius)
        self._glow_anim.start()

    def enterEvent(self, event):
        if self.property("active") != "true":
            t = get_theme()
            r, g, b = _hex_to_rgb(t['accent'])
            self.glow.setColor(QColor(r, g, b, 34))
            self._animate_glow(24)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.property("active") != "true":
            self.glow.setColor(QColor(0, 0, 0, 0))
            self._animate_glow(18)
        super().leaveEvent(event)

    def add_slider(self, label, min_val, max_val, current_val, callback):
        t = get_theme()
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setObjectName("RowLabel")
        
        val_lbl = QLabel(str(current_val))
        val_lbl.setStyleSheet(f"color:{t['accent']}; font-weight:700; font-size:12px; min-width:24px;")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(current_val)
        slider.setStyleSheet(slider_stylesheet(t))

        def _on_val(v):
            val_lbl.setText(str(v))
            callback(v)

        slider.valueChanged.connect(_on_val)
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val_lbl)
        row.addSpacing(8)
        row.addWidget(slider)
        self.content_layout.addLayout(row)
        return slider

    def add_row(self, label_text, widget):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setObjectName("RowLabel")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(widget)
        self.content_layout.addLayout(row)

    def add_delay_range_row(self, label_text, min_val, max_val, callback):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setObjectName("RowLabel")
        row.addWidget(lbl)
        row.addStretch()
        w = DelayRangeRow(min_val, max_val)
        w.changed.connect(callback)
        row.addWidget(w)
        self.content_layout.addLayout(row)

    def add_slider(self, label_text, min_v, max_v, cur_v, callback):
        t = get_theme()
        row = QVBoxLayout()
        hdr = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setObjectName("RowLabel")
        val_lbl = QLabel(str(cur_v))
        val_lbl.setStyleSheet(f"color:{t['accent']}; font-weight:700; font-size:12px;")
        hdr.addWidget(lbl)
        hdr.addStretch()
        hdr.addWidget(val_lbl)
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(min_v, max_v)
        s.setValue(cur_v)
        s.setStyleSheet(slider_stylesheet(t))
        s.valueChanged.connect(lambda v: (val_lbl.setText(str(v)), callback(v)))
        row.addLayout(hdr)
        row.addWidget(s)
        self.content_layout.addLayout(row)


# =============================================================================
# THEME CREATOR DIALOG
# =============================================================================

PALETTE_KEYS_DEF = [
    ("accent",     "Accent",   "The main glow / highlight colour"),
    ("accent_dim", "Dim",      "Darker accent used on hover states"),
    ("bg",         "BG",       "Main background (darkest)"),
    ("sidebar",    "Sidebar",  "Sidebar background"),
    ("card",       "Card",     "Card / panel background"),
    ("border",     "Border",   "Dividers and card outlines"),
    ("text",       "Text",     "Primary text"),
    ("subtext",    "Subtext",  "Secondary / muted text"),
]

class ColorPickerButton(QPushButton):
    """Square button that shows a colour and opens QColorDialog on click."""
    color_changed = pyqtSignal(str)   # emits hex string

    def __init__(self, hex_color: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self._hex = hex_color
        self._refresh()
        self.clicked.connect(self._pick)

    def _refresh(self):
        self.setStyleSheet(
            f"QPushButton {{ background-color:{self._hex}; border-radius:6px; "
            f"border:2px solid rgba(255,255,255,0.15); }}"
            f"QPushButton:hover {{ border:2px solid rgba(255,255,255,0.5); }}"
        )

    def _pick(self):
        from PyQt6.QtGui import QColor as _QColor
        initial = _QColor(self._hex)
        col = QColorDialog.getColor(initial, self, "Pick colour",
                                    QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if col.isValid():
            self._hex = col.name()
            self._refresh()
            self.color_changed.emit(self._hex)

    def hex(self) -> str:
        return self._hex

    def set_hex(self, h: str):
        self._hex = h
        self._refresh()


class ThemeCreatorDialog(QDialog):
    """
    Create a custom theme: pick colours, preview live, test by applying
    temporarily, then hardcode into custom_themes.json.
    """
    theme_added = pyqtSignal()

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main_window = main_window
        self._preview_active = False   # True while live-previewing
        self._prev_theme_name = _current_theme_name  # restore on cancel/stop

        self.setWindowTitle("Theme Creator")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setMinimumWidth(560)

        t = get_theme()
        self._base_t = t
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t['bg']};
                border: 1px solid {t['border']};
                border-radius: 12px;
            }}
            QWidget {{
                font-family: 'Segoe UI','Helvetica Neue',sans-serif;
                font-size: 13px;
                color: {t['text']};
                background-color: transparent;
            }}
            QLineEdit {{
                background-color: rgba(255,255,255,0.05);
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 5px 10px;
                color: {t['text']};
            }}
            QLineEdit:focus {{ border: 1px solid {t['accent']}; }}
            QPushButton#SaveBtn {{
                background-color: {t['accent']};
                color: #000;
                font-weight: 700;
                border-radius: 7px;
                padding: 7px 18px;
                border: none;
                font-size: 13px;
            }}
            QPushButton#SaveBtn:hover {{ background-color: {t['accent_dim']}; }}
            QPushButton#NeutralBtn {{
                background-color: rgba(255,255,255,0.06);
                color: {t['text']};
                font-weight: 600;
                border-radius: 7px;
                padding: 7px 18px;
                border: 1px solid {t['border']};
                font-size: 13px;
            }}
            QPushButton#NeutralBtn:hover {{ background-color: rgba(255,255,255,0.10); }}
            QLabel#SectionLabel {{
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2px;
                color: {t['subtext']};
                margin-top: 6px;
            }}
        """)
        self._build_ui(t)

    def _build_ui(self, t):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Title bar ──
        title_bar = QFrame()
        title_bar.setFixedHeight(44)
        title_bar.setStyleSheet(
            f"background:{t['sidebar']}; border-bottom:1px solid {t['border']};"
            f"border-top-left-radius:12px; border-top-right-radius:12px;"
        )
        tb_lay = QHBoxLayout(title_bar)
        tb_lay.setContentsMargins(18, 0, 8, 0)

        icon = QLabel("\U0001f3a8")
        icon.setStyleSheet(f"color:{t['accent']}; font-size:14px;")
        tl = QLabel("Theme Creator")
        tl.setStyleSheet(f"color:{t['text']}; font-size:14px; font-weight:800; margin-left:8px;")
        close_btn = QPushButton("\u2715")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{t['subtext']};border:none;font-size:14px;"
            f"font-weight:700;border-radius:6px;}} QPushButton:hover{{background:#c0392b;color:#fff;}}"
        )
        close_btn.clicked.connect(self._cancel)

        tb_lay.addWidget(icon)
        tb_lay.addWidget(tl)
        tb_lay.addStretch()
        tb_lay.addWidget(close_btn)
        root.addWidget(title_bar)

        # Drag
        self._drag_pos = QPoint()
        title_bar.mousePressEvent  = lambda e: setattr(self, '_drag_pos', e.globalPosition().toPoint() - self.frameGeometry().topLeft()) if e.button() == Qt.MouseButton.LeftButton else None
        title_bar.mouseMoveEvent   = lambda e: self.move(e.globalPosition().toPoint() - self._drag_pos) if e.buttons() == Qt.MouseButton.LeftButton else None

        # ── Body ──
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(24, 18, 24, 18)
        body_lay.setSpacing(10)
        root.addWidget(body)

        # Step label
        self._step_lbl = QLabel("STEP 1  \u2014  BUILD YOUR PALETTE")
        self._step_lbl.setObjectName("SectionLabel")
        body_lay.addWidget(self._step_lbl)

        hint = QLabel(
            "Click any colour swatch to open the colour picker. "
            "Use \u25b6 Preview to test the theme live on the whole UI without saving. "
            "When satisfied click \ud83d\udd12 Hardcode It to save permanently."
        )
        hint.setStyleSheet(f"font-size:11px; color:{t['subtext']};")
        hint.setWordWrap(True)
        body_lay.addWidget(hint)

        # Theme name
        name_row = QHBoxLayout()
        name_lbl = QLabel("Theme Name")
        name_lbl.setStyleSheet(f"color:rgba(255,255,255,0.55); font-size:12px; min-width:110px;")
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Midnight Rose")
        name_row.addWidget(name_lbl)
        name_row.addWidget(self._name_edit)
        body_lay.addLayout(name_row)

        # ── Colour rows ──
        colours_lbl = QLabel("COLOURS")
        colours_lbl.setObjectName("SectionLabel")
        body_lay.addWidget(colours_lbl)

        self._pickers: dict[str, ColorPickerButton] = {}
        self._hex_edits: dict[str, QLineEdit] = {}

        # Sensible defaults (BlackIce as starting point)
        DEFAULTS = {
            "accent":     "#00D2FF",
            "accent_dim": "#007A99",
            "bg":         "#0B0E14",
            "sidebar":    "#11151C",
            "card":       "#1A1F26",
            "border":     "#2D3642",
            "text":       "#E0FBFF",
            "subtext":    "#8FA3AD",
        }

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnStretch(2, 1)

        for row_i, (key, label, desc) in enumerate(PALETTE_KEYS_DEF):
            hex_val = DEFAULTS[key]

            lbl = QLabel(label)
            lbl.setStyleSheet(f"font-size:12px; color:{t['text']}; font-weight:600; min-width:80px;")

            picker = ColorPickerButton(hex_val)
            self._pickers[key] = picker

            hex_edit = QLineEdit(hex_val)
            hex_edit.setFixedWidth(90)
            hex_edit.setStyleSheet(
                f"background:rgba(255,255,255,0.05); border:1px solid {t['border']};"
                f"border-radius:6px; color:{t['text']}; font-family:'Consolas','Courier New',monospace;"
                f"font-size:12px; padding:3px 8px;"
            )
            self._hex_edits[key] = hex_edit

            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"font-size:10px; color:{t['subtext']};")

            # Sync picker -> hex edit -> preview
            def _on_picker_change(h, _key=key, _edit=hex_edit):
                _edit.setText(h)
                self._on_color_change()

            def _on_edit_finished(_key=key, _picker=picker, _edit=hex_edit):
                raw = _edit.text().strip()
                if not raw.startswith("#"):
                    raw = "#" + raw
                if len(raw) in (4, 7):
                    _picker.set_hex(raw)
                    _edit.setText(raw)
                    self._on_color_change()

            picker.color_changed.connect(_on_picker_change)
            hex_edit.editingFinished.connect(_on_edit_finished)

            grid.addWidget(lbl,      row_i, 0)
            grid.addWidget(picker,   row_i, 1)
            grid.addWidget(hex_edit, row_i, 2)
            grid.addWidget(desc_lbl, row_i, 3)

        body_lay.addLayout(grid)

        # ── Mini live preview swatch strip ──
        preview_lbl = QLabel("PALETTE PREVIEW")
        preview_lbl.setObjectName("SectionLabel")
        body_lay.addWidget(preview_lbl)

        self._swatch_row = QHBoxLayout()
        self._swatch_row.setSpacing(4)
        self._swatches: dict[str, QFrame] = {}
        for key, label, _ in PALETTE_KEYS_DEF:
            col_w = QWidget()
            col_l = QVBoxLayout(col_w)
            col_l.setContentsMargins(0, 0, 0, 0)
            col_l.setSpacing(2)
            col_l.setAlignment(Qt.AlignmentFlag.AlignHCenter)

            sw = QFrame()
            sw.setFixedSize(28, 28)
            sw.setStyleSheet(
                f"background-color:{DEFAULTS[key]}; border-radius:5px; border:1px solid rgba(255,255,255,0.1);"
            )
            self._swatches[key] = sw

            sl = QLabel(label)
            sl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            sl.setStyleSheet(f"font-size:8px; color:{t['subtext']}; font-weight:600;")

            col_l.addWidget(sw)
            col_l.addWidget(sl)
            self._swatch_row.addWidget(col_w)

        self._swatch_row.addStretch()
        body_lay.addLayout(self._swatch_row)

        # ── Preview status bar ──
        self._preview_bar = QFrame()
        self._preview_bar.setStyleSheet(
            "background:rgba(57,255,20,0.07); border:1px solid rgba(57,255,20,0.3); border-radius:8px;"
        )
        pb_lay = QHBoxLayout(self._preview_bar)
        pb_lay.setContentsMargins(12, 7, 12, 7)
        QLabel("\u25cf LIVE PREVIEW ACTIVE").setParent(self._preview_bar)
        pulse = QLabel("\u25cf LIVE PREVIEW ACTIVE")
        pulse.setStyleSheet("color:#39ff14; font-weight:800; font-size:11px; background:transparent;")
        pb_info = QLabel("Theme is applied to the whole UI. Stop to revert, Hardcode to save.")
        pb_info.setStyleSheet(f"color:{t['subtext']}; font-size:10px; background:transparent;")
        pb_lay.addWidget(pulse)
        pb_lay.addWidget(pb_info, 1)
        self._preview_bar.setVisible(False)
        body_lay.addWidget(self._preview_bar)

        body_lay.addStretch()

        # ── Bottom buttons ──
        btn_row = QHBoxLayout()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("NeutralBtn")
        cancel_btn.clicked.connect(self._cancel)

        self._preview_btn = QPushButton("\u25b6  Preview")
        self._preview_btn.setObjectName("NeutralBtn")
        self._preview_btn.clicked.connect(self._toggle_preview)

        self._hardcode_btn = QPushButton("\ud83d\udd12  Hardcode It")
        self._hardcode_btn.setObjectName("SaveBtn")
        self._hardcode_btn.clicked.connect(self._do_hardcode)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._preview_btn)
        btn_row.addSpacing(6)
        btn_row.addWidget(self._hardcode_btn)
        body_lay.addLayout(btn_row)

    # ------------------------------------------------------------------
    def _current_palette(self) -> dict:
        return {key: picker.hex() for key, picker in self._pickers.items()}

    def _on_color_change(self):
        """Update swatch strip and, if preview is live, hot-reload the UI theme."""
        for key, sw in self._swatches.items():
            col = self._pickers[key].hex()
            sw.setStyleSheet(
                f"background-color:{col}; border-radius:5px; border:1px solid rgba(255,255,255,0.1);"
            )
        if self._preview_active:
            self._apply_preview()

    def _apply_preview(self):
        """Temporarily inject current palette into THEMES and apply globally."""
        pal = self._current_palette()
        THEMES["__preview__"] = pal
        self._main_window._change_theme("__preview__")

    def _toggle_preview(self):
        if not self._preview_active:
            self._start_preview()
        else:
            self._stop_preview()

    def _start_preview(self):
        name = self._name_edit.text().strip() or "__preview__"
        self._preview_active = True
        self._apply_preview()
        self._preview_btn.setText("\u25a0  Stop Preview")
        self._preview_btn.setStyleSheet(
            "QPushButton { background-color: rgba(220,50,50,0.2); color: #e06060; "
            "font-weight: 700; border-radius: 7px; padding: 7px 18px; "
            "border: 1px solid rgba(220,50,50,0.4); font-size: 13px; }"
            "QPushButton:hover { background-color: rgba(220,50,50,0.35); }"
        )
        self._preview_bar.setVisible(True)
        self._step_lbl.setText("PREVIEWING  \u2014  LIVE ON UI")

    def _stop_preview(self):
        self._preview_active = False
        THEMES.pop("__preview__", None)
        # Restore previous theme
        self._main_window._change_theme(self._prev_theme_name)
        self._preview_btn.setText("\u25b6  Preview")
        self._preview_btn.setObjectName("NeutralBtn")
        self._preview_btn.setStyleSheet("")
        self._preview_bar.setVisible(False)
        self._step_lbl.setText("STEP 1  \u2014  BUILD YOUR PALETTE")

    def _cancel(self):
        if self._preview_active:
            self._stop_preview()
        self.reject()

    def _do_hardcode(self):
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Theme name cannot be empty.")
            return
        if name in THEMES and name not in custom_theme_registry.themes:
            QMessageBox.warning(self, "Name Taken",
                f'"{name}" is a built-in theme name. Choose a different name.')
            return

        # Stop preview if running
        if self._preview_active:
            self._stop_preview()

        pal = self._current_palette()
        custom_theme_registry.add(name, pal)

        # Apply the new theme immediately
        self._main_window._change_theme(name)
        self.theme_added.emit()
        self.accept()


# =============================================================================
# ADD GUN DIALOG
# =============================================================================

class AddGunDialog(QDialog):
    """
    Modal dialog with two tabs:
      • Build — create a gun from scratch (writes directly to custom_guns.json)
      • Community — import/export community JSON gun packs
    """

    gun_added = pyqtSignal()   # emitted when the home page should refresh

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Gun")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setMinimumWidth(520)
        t = get_theme()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t['bg']};
                border: 1px solid {t['border']};
                border-radius: 12px;
            }}
            QWidget {{
                font-family: 'Segoe UI','Helvetica Neue',sans-serif;
                font-size: 13px;
                color: {t['text']};
                background-color: transparent;
            }}
            QTabWidget::pane {{
                border: 1px solid {t['border']};
                border-radius: 8px;
                background: {t['card']};
            }}
            QTabBar::tab {{
                background: rgba(255,255,255,0.04);
                color: {t['subtext']};
                border: 1px solid {t['border']};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 7px 20px;
                font-weight: 700;
                font-size: 12px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {t['card']};
                color: {t['accent']};
                border-bottom: 1px solid {t['card']};
            }}
            QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
                background-color: rgba(255,255,255,0.05);
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 5px 10px;
                color: {t['text']};
                font-size: 13px;
            }}
            QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
                border: 1px solid {t['accent']};
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 18px;
                border: none;
                background: rgba(255,255,255,0.06);
            }}
            QPushButton#SaveBtn {{
                background-color: {t['accent']};
                color: #000;
                font-weight: 700;
                border-radius: 7px;
                padding: 7px 18px;
                border: none;
                font-size: 13px;
            }}
            QPushButton#SaveBtn:hover {{ background-color: {t['accent_dim']}; }}
            QPushButton#NeutralBtn {{
                background-color: rgba(255,255,255,0.06);
                color: {t['text']};
                font-weight: 600;
                border-radius: 7px;
                padding: 7px 18px;
                border: 1px solid {t['border']};
                font-size: 13px;
            }}
            QPushButton#NeutralBtn:hover {{ background-color: rgba(255,255,255,0.10); }}
            QPushButton#DangerBtn {{
                background-color: rgba(220,50,50,0.15);
                color: #e05555;
                font-weight: 700;
                border-radius: 7px;
                padding: 7px 18px;
                border: 1px solid rgba(220,50,50,0.3);
                font-size: 13px;
            }}
            QPushButton#DangerBtn:hover {{ background-color: rgba(220,50,50,0.3); }}
            QTextEdit {{
                background-color: rgba(255,255,255,0.04);
                border: 1px solid {t['border']};
                border-radius: 8px;
                color: {t['text']};
                font-family: 'Consolas','Courier New',monospace;
                font-size: 12px;
                padding: 6px;
            }}
            QLabel#SectionLabel {{
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2px;
                color: {t['subtext']};
                margin-top: 8px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background: {t['card']};
                border: 1px solid {t['border']};
                color: {t['text']};
                selection-background-color: rgba(255,255,255,0.08);
            }}
        """)
        self._build_ui(t)

    def _build_ui(self, t):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Custom title bar ──
        title_bar = QFrame()
        title_bar.setFixedHeight(44)
        title_bar.setStyleSheet(f"background:{t['sidebar']}; border-bottom:1px solid {t['border']}; border-top-left-radius:12px; border-top-right-radius:12px;")
        tb_lay = QHBoxLayout(title_bar)
        tb_lay.setContentsMargins(18, 0, 8, 0)

        icon = QLabel("⚙")
        icon.setStyleSheet(f"color:{t['accent']}; font-size:14px; font-weight:900;")
        tl = QLabel("Add Gun")
        tl.setStyleSheet(f"color:{t['text']}; font-size:14px; font-weight:800; margin-left:8px;")
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{t['subtext']};border:none;font-size:14px;font-weight:700;border-radius:6px;}} QPushButton:hover{{background:#c0392b;color:#fff;}}")
        close_btn.clicked.connect(self.reject)

        tb_lay.addWidget(icon)
        tb_lay.addWidget(tl)
        tb_lay.addStretch()
        tb_lay.addWidget(close_btn)
        root.addWidget(title_bar)

        # Dragging the dialog
        title_bar.mousePressEvent   = lambda e: setattr(self, '_drag_pos', e.globalPosition().toPoint() - self.frameGeometry().topLeft()) if e.button() == Qt.MouseButton.LeftButton else None
        title_bar.mouseMoveEvent    = lambda e: self.move(e.globalPosition().toPoint() - self._drag_pos) if e.buttons() == Qt.MouseButton.LeftButton else None
        self._drag_pos = QPoint()

        # ── Tab widget ──
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        root.addWidget(tabs)

        tabs.addTab(self._build_tab_build(t), "🔧  Build")
        tabs.addTab(self._build_tab_community(t), "🌐  Community")

    # ------------------------------------------------------------------
    def _form_row(self, label_text, widget):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: rgba(255,255,255,0.55); font-size:12px;")
        lbl.setFixedWidth(120)
        row.addWidget(lbl)
        row.addWidget(widget)
        return row

    def _build_tab_build(self, t):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(10)

        self._test_thread = None   # holds live preview macro thread while testing

        # ── Step label ──
        self._step_lbl = QLabel("STEP 1  \u2014  CONFIGURE")
        self._step_lbl.setObjectName("SectionLabel")
        lay.addWidget(self._step_lbl)

        hint = QLabel(
            "Set dy (pixels down/tick) and dx (side drift). "
            "Click  \u25b6 Test  to fire the macro live in-game without saving anything. "
            "Adjust values freely while testing, then  \ud83d\udd12 Hardcode  when happy."
        )
        hint.setStyleSheet(f"font-size:11px; color:{t['subtext']}; margin-bottom:4px;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        # Gun name
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. AK-47")
        lay.addLayout(self._form_row("Gun Name", self._name_edit))

        # Badge
        self._badge_edit = QLineEdit()
        self._badge_edit.setPlaceholderText("e.g. AK  (2\u20133 chars)")
        self._badge_edit.setMaxLength(3)
        lay.addLayout(self._form_row("Badge", self._badge_edit))

        # Slot type
        self._slot_combo = QComboBox()
        self._slot_combo.addItems(["Primary  (key1 arms)", "Secondary  (key2 arms)"])
        lay.addLayout(self._form_row("Slot Type", self._slot_combo))

        # Recoil DY
        self._dy_spin = QDoubleSpinBox()
        self._dy_spin.setRange(-50.0, 50.0)
        self._dy_spin.setValue(8.0)
        self._dy_spin.setDecimals(1)
        self._dy_spin.setSingleStep(0.5)
        self._dy_spin.setSuffix(" px")
        lay.addLayout(self._form_row("Recoil Down (dy)", self._dy_spin))

        # Recoil DX
        self._dx_spin = QDoubleSpinBox()
        self._dx_spin.setRange(-50.0, 50.0)
        self._dx_spin.setValue(0.0)
        self._dx_spin.setDecimals(1)
        self._dx_spin.setSingleStep(0.5)
        self._dx_spin.setSuffix(" px")
        lay.addLayout(self._form_row("Recoil Side (dx)", self._dx_spin))

        # Default strength
        self._strength_spin = QSpinBox()
        self._strength_spin.setRange(1, 100)
        self._strength_spin.setValue(100)
        self._strength_spin.setSuffix("%")
        lay.addLayout(self._form_row("Default Strength", self._strength_spin))

        lay.addSpacing(6)

        # ── Live JSON preview ──
        preview_hdr = QLabel("LIVE PREVIEW")
        preview_hdr.setObjectName("SectionLabel")
        lay.addWidget(preview_hdr)

        self._preview_lbl = QLabel()
        self._preview_lbl.setStyleSheet(
            f"color:{t['accent']}; font-size:11px; font-family:'Consolas','Courier New',monospace;"
            f"background:rgba(255,255,255,0.03); border:1px solid {t['border']}; border-radius:6px; padding:6px 8px;"
        )
        self._preview_lbl.setWordWrap(True)
        lay.addWidget(self._preview_lbl)

        # ── Test status bar (hidden until testing) ──
        self._test_bar = QFrame()
        self._test_bar.setStyleSheet(
            f"background:rgba(57,255,20,0.07); border:1px solid rgba(57,255,20,0.3); border-radius:8px;"
        )
        tb_lay = QHBoxLayout(self._test_bar)
        tb_lay.setContentsMargins(12, 8, 12, 8)
        tb_lay.setSpacing(10)

        pulse_lbl = QLabel("\u25cf LIVE TEST ACTIVE")
        pulse_lbl.setStyleSheet("color:#39ff14; font-weight:800; font-size:11px; background:transparent;")
        tb_info = QLabel("Hold MB1+MB2 in-game. Adjust dy/dx freely \u2014 changes apply instantly.")
        tb_info.setStyleSheet(f"color:{t['subtext']}; font-size:10px; background:transparent;")
        tb_info.setWordWrap(True)

        tb_lay.addWidget(pulse_lbl)
        tb_lay.addWidget(tb_info, 1)
        self._test_bar.setVisible(False)
        lay.addWidget(self._test_bar)

        # Connect live preview + hot-reload while testing
        for w2 in (self._name_edit, self._badge_edit, self._slot_combo,
                   self._dy_spin, self._dx_spin, self._strength_spin):
            if hasattr(w2, 'textChanged'):
                w2.textChanged.connect(self._update_preview)
            elif hasattr(w2, 'currentIndexChanged'):
                w2.currentIndexChanged.connect(self._update_preview)
            elif hasattr(w2, 'valueChanged'):
                w2.valueChanged.connect(self._update_preview)

        # dy/dx spin updates propagate to running test thread live
        self._dy_spin.valueChanged.connect(self._sync_test_thread)
        self._dx_spin.valueChanged.connect(self._sync_test_thread)
        self._strength_spin.valueChanged.connect(self._sync_test_thread)
        self._slot_combo.currentIndexChanged.connect(self._sync_test_thread)

        self._update_preview()

        lay.addStretch()

        # ── Bottom buttons ──
        btn_row = QHBoxLayout()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("NeutralBtn")
        cancel_btn.clicked.connect(self._cancel_and_stop)

        self._test_btn = QPushButton("\u25b6  Test")
        self._test_btn.setObjectName("NeutralBtn")
        self._test_btn.clicked.connect(self._toggle_test)

        self._hardcode_btn = QPushButton("\ud83d\udd12  Hardcode It")
        self._hardcode_btn.setObjectName("SaveBtn")
        self._hardcode_btn.clicked.connect(self._do_add_gun)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._test_btn)
        btn_row.addSpacing(6)
        btn_row.addWidget(self._hardcode_btn)
        lay.addLayout(btn_row)

        return w

    # ------------------------------------------------------------------
    # TEST THREAD HELPERS
    # ------------------------------------------------------------------

    def _make_preview_gun(self):
        """Build a temporary CustomGunSettings from current form values."""
        name  = self._name_edit.text().strip() or "Preview"
        badge = self._badge_edit.text().strip().upper() or name[:2].upper()
        return CustomGunSettings(
            enabled=True,
            name=name,
            badge=badge,
            dy=self._dy_spin.value(),
            dx=self._dx_spin.value(),
            slot_key=self._slot_combo.currentIndex() + 1,
            strength=self._strength_spin.value(),
        )

    def _toggle_test(self):
        if self._test_thread is None:
            self._start_test()
        else:
            self._stop_test()

    def _start_test(self):
        """Start a temporary macro thread for live in-game testing."""
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Enter a gun name before testing.")
            return
        gun = self._make_preview_gun()
        self._test_thread = CustomGunMacro(gun)
        self._test_thread.start()

        self._test_btn.setText("\u25a0  Stop Test")
        self._test_btn.setStyleSheet(
            "QPushButton { background-color: rgba(220,50,50,0.2); color: #e06060; "
            "font-weight: 700; border-radius: 7px; padding: 7px 18px; "
            "border: 1px solid rgba(220,50,50,0.4); font-size: 13px; }"
            "QPushButton:hover { background-color: rgba(220,50,50,0.35); }"
        )
        self._test_bar.setVisible(True)
        self._step_lbl.setText("TESTING  \u2014  LIVE MACRO RUNNING")

    def _stop_test(self):
        """Stop the live test thread without saving."""
        if self._test_thread is not None:
            self._test_thread.running = False
            self._test_thread.quit()
            self._test_thread.wait(500)
            self._test_thread = None

        self._test_btn.setText("\u25b6  Test")
        self._test_btn.setObjectName("NeutralBtn")
        self._test_btn.setStyleSheet("")   # reset to QSS
        self._test_bar.setVisible(False)
        self._step_lbl.setText("STEP 1  \u2014  CONFIGURE")

    def _sync_test_thread(self, *_):
        """Push dy/dx/strength/slot changes into the running test thread live."""
        if self._test_thread is not None and self._test_thread.gun is not None:
            g = self._test_thread.gun
            g.dy       = self._dy_spin.value()
            g.dx       = self._dx_spin.value()
            g.strength = self._strength_spin.value()
            g.slot_key = self._slot_combo.currentIndex() + 1

    def _cancel_and_stop(self):
        """Cancel dialog and kill any running test thread."""
        self._stop_test()
        self.reject()

    def _update_preview(self, *_):
        name  = self._name_edit.text() or "<n>"
        badge = self._badge_edit.text() or "<badge>"
        dy    = self._dy_spin.value()
        dx    = self._dx_spin.value()
        slot  = self._slot_combo.currentIndex() + 1
        strg  = self._strength_spin.value()
        self._preview_lbl.setText(
            f'{{ "name": "{name}", "badge": "{badge}",\n'
            f'  "dy": {dy}, "dx": {dx}, "slot_key": {slot}, "strength": {strg} }}'
        )

    def _do_add_gun(self):
        """Hardcode: stop test thread, save to registry, close."""
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Gun name cannot be empty.")
            return
        self._stop_test()
        badge = self._badge_edit.text().strip().upper() or name[:2].upper()
        gun = CustomGunSettings(
            enabled=False,
            name=name,
            badge=badge,
            dy=self._dy_spin.value(),
            dx=self._dx_spin.value(),
            slot_key=self._slot_combo.currentIndex() + 1,
            strength=self._strength_spin.value(),
        )
        gun_registry.add(gun)
        self.gun_added.emit()
        self.accept()
    # ------------------------------------------------------------------
    def _build_tab_community(self, t):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        info = QLabel(
            "Share or receive gun packs with the community.\n"
            "Export your custom guns as a JSON file, or import a pack from someone else."
        )
        info.setStyleSheet(f"font-size:12px; color:{t['subtext']};")
        info.setWordWrap(True)
        lay.addWidget(info)

        # JSON preview
        sec_lbl = QLabel("PREVIEW / PASTE JSON")
        sec_lbl.setObjectName("SectionLabel")
        lay.addWidget(sec_lbl)

        self._json_edit = QTextEdit()
        self._json_edit.setPlaceholderText(
            '[\n'
            '  {\n'
            '    "name": "AK-47",\n'
            '    "badge": "AK",\n'
            '    "dy": 12.0,\n'
            '    "dx": -0.5,\n'
            '    "slot_key": 1,\n'
            '    "strength": 100\n'
            '  }\n'
            ']'
        )
        self._json_edit.setMinimumHeight(160)
        lay.addWidget(self._json_edit)

        hint2 = QLabel("Paste a community pack above and click Import, or click Export to get your current guns.")
        hint2.setStyleSheet(f"font-size:11px; color:{t['subtext']};")
        hint2.setWordWrap(True)
        lay.addWidget(hint2)

        lay.addStretch()

        btn_row = QHBoxLayout()

        export_btn = QPushButton("⬆  Export My Guns")
        export_btn.setObjectName("NeutralBtn")
        export_btn.clicked.connect(self._do_export)

        import_file_btn = QPushButton("📂  Import from File")
        import_file_btn.setObjectName("NeutralBtn")
        import_file_btn.clicked.connect(self._do_import_file)

        import_paste_btn = QPushButton("⬇  Import Pasted")
        import_paste_btn.setObjectName("SaveBtn")
        import_paste_btn.clicked.connect(self._do_import_paste)

        btn_row.addWidget(export_btn)
        btn_row.addWidget(import_file_btn)
        btn_row.addStretch()
        btn_row.addWidget(import_paste_btn)
        lay.addLayout(btn_row)

        return w

    def _do_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Gun Pack", "my_guns.json", "JSON Files (*.json)")
        if path:
            try:
                gun_registry.export_json(path)
                # Also fill the text editor so users can copy-paste easily
                with open(path) as f:
                    self._json_edit.setPlainText(f.read())
                QMessageBox.information(self, "Exported", f"Saved {len(gun_registry.guns)} gun(s) to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def _do_import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Gun Pack", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path) as f:
                    content = f.read()
                self._json_edit.setPlainText(content)
                n = gun_registry.import_json(path)
                self.gun_added.emit()
                QMessageBox.information(self, "Imported", f"Added {n} gun(s) from the pack.")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", str(e))

    def _do_import_paste(self):
        raw = self._json_edit.toPlainText().strip()
        if not raw:
            QMessageBox.warning(self, "Empty", "Nothing pasted to import.")
            return
        import tempfile
        try:
            # Validate JSON first
            data = json.loads(raw)
            if not isinstance(data, list):
                raise ValueError("Expected a JSON array of gun objects.")
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            json.dump(data, tmp, indent=4)
            tmp.close()
            n = gun_registry.import_json(tmp.name)
            os.remove(tmp.name)
            self.gun_added.emit()
            QMessageBox.information(self, "Imported", f"Added {n} gun(s) from pasted JSON.")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Invalid JSON:\n{e}")


# =============================================================================
# CUSTOM PAGE SYSTEM
# =============================================================================

CUSTOM_PAGES_FILE = "custom_pages.json"

# Button type constants
BTYPE_KEYBIND   = "keybind"
BTYPE_GUN       = "gun"
BTYPE_CODE      = "code"

class CustomPageRegistry:
    """Loads/saves user-created pages from custom_pages.json."""

    def __init__(self):
        self.pages: list[dict] = []   # [{name, badge, buttons: [...]}, ...]
        self.load()

    def load(self, path: str = CUSTOM_PAGES_FILE):
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                self.pages = data
        except Exception:
            pass

    def save(self, path: str = CUSTOM_PAGES_FILE):
        tmp = path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(self.pages, f, indent=4)
            if os.path.exists(path):
                os.replace(tmp, path)
            else:
                os.rename(tmp, path)
        except Exception:
            try:
                os.remove(tmp)
            except Exception:
                pass

    def add_page(self, name: str, badge: str) -> dict:
        page = {"name": name, "badge": badge, "buttons": []}
        self.pages.append(page)
        self.save()
        return page

    def remove_page(self, index: int):
        if 0 <= index < len(self.pages):
            self.pages.pop(index)
            self.save()

    def add_button(self, page_index: int, btn: dict):
        self.pages[page_index]["buttons"].append(btn)
        self.save()

    def remove_button(self, page_index: int, btn_index: int):
        if 0 <= page_index < len(self.pages):
            btns = self.pages[page_index]["buttons"]
            if 0 <= btn_index < len(btns):
                btns.pop(btn_index)
                self.save()

    def update_button(self, page_index: int, btn_index: int, btn: dict):
        self.pages[page_index]["buttons"][btn_index] = btn
        self.save()

custom_page_registry = CustomPageRegistry()


class ButtonEditorDialog(QDialog):
    """Dialog to create or edit a single button on a custom page."""

    def __init__(self, parent=None, existing: dict = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setFixedWidth(520)
        self._result_btn = None
        self._existing = existing or {}

        t = get_theme()
        self.setStyleSheet(f"""
            QDialog {{ background-color:{t['bg']}; border:1px solid {t['border']}; border-radius:14px; }}
            QWidget {{ font-family:'Segoe UI','Helvetica Neue',sans-serif; font-size:13px; color:{t['text']}; background:transparent; }}
            QLineEdit {{ background:rgba(255,255,255,0.05); border:1px solid {t['border']}; border-radius:7px; padding:8px 12px; color:{t['text']}; }}
            QLineEdit:focus {{ border:1px solid {t['accent']}; }}
            QTextEdit {{ background:rgba(255,255,255,0.04); border:1px solid {t['border']}; border-radius:7px; padding:8px; color:{t['text']}; font-family:'Consolas','Courier New',monospace; font-size:12px; }}
            QTextEdit:focus {{ border:1px solid {t['accent']}; }}
            QComboBox {{ background:rgba(255,255,255,0.05); border:1px solid {t['border']}; border-radius:7px; padding:6px 10px; color:{t['text']}; }}
            QComboBox::drop-down {{ border:none; }}
            QLabel#SectionLbl {{ font-size:10px; font-weight:700; letter-spacing:2px; color:{t['subtext']}; }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        tbar = QFrame()
        tbar.setFixedHeight(46)
        tbar.setStyleSheet(f"background:{t['sidebar']}; border-bottom:1px solid {t['border']}; border-top-left-radius:14px; border-top-right-radius:14px;")
        tbar_lay = QHBoxLayout(tbar)
        tbar_lay.setContentsMargins(20, 0, 10, 0)
        icon = QLabel("✦")
        icon.setStyleSheet(f"color:{t['accent']}; font-size:14px; font-weight:900;")
        ttl = QLabel("Button Editor")
        ttl.setStyleSheet(f"color:{t['text']}; font-size:13px; font-weight:800; margin-left:8px;")
        tbar_lay.addWidget(icon)
        tbar_lay.addWidget(ttl)
        tbar_lay.addStretch()
        root.addWidget(tbar)

        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(24, 20, 24, 20)
        body_lay.setSpacing(14)
        root.addWidget(body)

        # Button label
        lbl_label = QLabel("BUTTON LABEL")
        lbl_label.setObjectName("SectionLbl")
        self._label_input = QLineEdit()
        self._label_input.setPlaceholderText("e.g. Jump + Shoot")
        self._label_input.setText(self._existing.get("label", ""))
        body_lay.addWidget(lbl_label)
        body_lay.addWidget(self._label_input)

        # Button type selector
        type_lbl = QLabel("BUTTON TYPE")
        type_lbl.setObjectName("SectionLbl")
        self._type_combo = QComboBox()
        self._type_combo.addItems(["Keybind / Input", "Gun Card", "Custom Code"])
        body_lay.addWidget(type_lbl)
        body_lay.addWidget(self._type_combo)

        # ── Keybind config ──
        self._keybind_widget = QWidget()
        kb_lay = QVBoxLayout(self._keybind_widget)
        kb_lay.setContentsMargins(0, 0, 0, 0)
        kb_lay.setSpacing(8)

        kb_top = QHBoxLayout()
        kb_key_lbl = QLabel("ACTIVATE KEY")
        kb_key_lbl.setObjectName("SectionLbl")
        self._kb_key_btn = KeybindButton(self._existing.get("key", "f"))
        kb_top.addWidget(kb_key_lbl)
        kb_top.addStretch()
        kb_top.addWidget(self._kb_key_btn)
        kb_lay.addLayout(kb_top)

        kb_action_lbl = QLabel("ACTION (keys to press, comma-separated)")
        kb_action_lbl.setObjectName("SectionLbl")
        self._kb_action = QLineEdit()
        self._kb_action.setPlaceholderText("e.g.  1, space, r  or  mouse3")
        self._kb_action.setText(self._existing.get("action_keys", ""))
        kb_lay.addWidget(kb_action_lbl)
        kb_lay.addWidget(self._kb_action)

        kb_delay_lbl = QLabel("DELAY BETWEEN KEYS (ms)")
        kb_delay_lbl.setObjectName("SectionLbl")
        kb_delay_row = QHBoxLayout()
        self._kb_delay_min = QLineEdit(str(self._existing.get("delay_min", 50)))
        self._kb_delay_max = QLineEdit(str(self._existing.get("delay_max", 100)))
        sep = QLabel("—")
        sep.setStyleSheet(f"color:{t['subtext']};")
        for box in (self._kb_delay_min, self._kb_delay_max):
            box.setFixedWidth(70)
        kb_delay_row.addWidget(self._kb_delay_min)
        kb_delay_row.addWidget(sep)
        kb_delay_row.addWidget(self._kb_delay_max)
        kb_delay_row.addStretch()
        kb_lay.addWidget(kb_delay_lbl)
        kb_lay.addLayout(kb_delay_row)

        kb_repeat_lbl = QLabel("HOLD TO REPEAT")
        kb_repeat_lbl.setObjectName("SectionLbl")
        self._kb_repeat = ToggleButton(checked=self._existing.get("hold_repeat", False))
        kb_repeat_row = QHBoxLayout()
        kb_repeat_row.addWidget(kb_repeat_lbl)
        kb_repeat_row.addStretch()
        kb_repeat_row.addWidget(self._kb_repeat)
        kb_lay.addLayout(kb_repeat_row)

        body_lay.addWidget(self._keybind_widget)

        # ── Gun config ──
        self._gun_widget = QWidget()
        gun_lay = QVBoxLayout(self._gun_widget)
        gun_lay.setContentsMargins(0, 0, 0, 0)
        gun_lay.setSpacing(8)

        gun_name_lbl = QLabel("GUN NAME")
        gun_name_lbl.setObjectName("SectionLbl")
        self._gun_name = QLineEdit()
        self._gun_name.setPlaceholderText("e.g. AK-47")
        self._gun_name.setText(self._existing.get("gun_name", ""))

        gun_badge_lbl = QLabel("BADGE (2-3 chars)")
        gun_badge_lbl.setObjectName("SectionLbl")
        self._gun_badge = QLineEdit()
        self._gun_badge.setPlaceholderText("e.g. AK")
        self._gun_badge.setText(self._existing.get("gun_badge", ""))
        self._gun_badge.setMaxLength(3)

        gun_dy_lbl = QLabel("RECOIL DOWN (dy pixels at sens 13)")
        gun_dy_lbl.setObjectName("SectionLbl")
        self._gun_dy = QLineEdit(str(self._existing.get("gun_dy", 8.0)))

        gun_dx_lbl = QLabel("RECOIL SIDE (dx pixels, negative = left)")
        gun_dx_lbl.setObjectName("SectionLbl")
        self._gun_dx = QLineEdit(str(self._existing.get("gun_dx", 0.0)))

        gun_slot_lbl = QLabel("ARM KEY (1 = key 1 arms, 2 = key 2 arms)")
        gun_slot_lbl.setObjectName("SectionLbl")
        self._gun_slot = QComboBox()
        self._gun_slot.addItems(["1", "2"])
        self._gun_slot.setCurrentIndex(self._existing.get("gun_slot", 1) - 1)

        for w, l in [(gun_name_lbl, self._gun_name), (gun_badge_lbl, self._gun_badge),
                     (gun_dy_lbl, self._gun_dy), (gun_dx_lbl, self._gun_dx)]:
            gun_lay.addWidget(w)
            gun_lay.addWidget(l)
        gun_lay.addWidget(gun_slot_lbl)
        gun_lay.addWidget(self._gun_slot)

        body_lay.addWidget(self._gun_widget)

        # ── Code config ──
        self._code_widget = QWidget()
        code_lay = QVBoxLayout(self._code_widget)
        code_lay.setContentsMargins(0, 0, 0, 0)
        code_lay.setSpacing(8)

        code_lbl = QLabel("PYTHON CODE (runs in a daemon thread; use 'ic' for InputController)")
        code_lbl.setObjectName("SectionLbl")
        code_lbl.setWordWrap(True)

        self._code_edit = QTextEdit()
        self._code_edit.setMinimumHeight(140)
        self._code_edit.setPlaceholderText(
            "# ic = InputController instance\n"
            "# Example:\n"
            "import time\n"
            "ic.press_key('1')\n"
            "time.sleep(0.05)\n"
            "ic.left_click()"
        )
        self._code_edit.setPlainText(self._existing.get("code", ""))
        code_lay.addWidget(code_lbl)
        code_lay.addWidget(self._code_edit)

        body_lay.addWidget(self._code_widget)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("NeutralBtn")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Save Button")
        btn_ok.setObjectName("SaveBtn")
        btn_ok.clicked.connect(self._do_save)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addSpacing(8)
        btn_row.addWidget(btn_ok)
        body_lay.addLayout(btn_row)

        # Wire up type selector visibility
        type_map = {0: BTYPE_KEYBIND, 1: BTYPE_GUN, 2: BTYPE_CODE}
        existing_type = self._existing.get("type", BTYPE_KEYBIND)
        reverse_map = {BTYPE_KEYBIND: 0, BTYPE_GUN: 1, BTYPE_CODE: 2}
        self._type_combo.setCurrentIndex(reverse_map.get(existing_type, 0))
        self._type_combo.currentIndexChanged.connect(self._on_type_change)
        self._on_type_change(self._type_combo.currentIndex())

    def _on_type_change(self, idx):
        self._keybind_widget.setVisible(idx == 0)
        self._gun_widget.setVisible(idx == 1)
        self._code_widget.setVisible(idx == 2)
        self.adjustSize()

    def _do_save(self):
        label = self._label_input.text().strip() or "Button"
        idx = self._type_combo.currentIndex()
        type_map = {0: BTYPE_KEYBIND, 1: BTYPE_GUN, 2: BTYPE_CODE}
        btype = type_map[idx]

        btn = {"type": btype, "label": label, "enabled": self._existing.get("enabled", True)}

        if btype == BTYPE_KEYBIND:
            btn["key"] = self._kb_key_btn.text().lower()
            btn["action_keys"] = self._kb_action.text().strip()
            try:
                btn["delay_min"] = max(0, int(self._kb_delay_min.text()))
                btn["delay_max"] = max(0, int(self._kb_delay_max.text()))
            except ValueError:
                btn["delay_min"] = 50
                btn["delay_max"] = 100
            btn["hold_repeat"] = self._kb_repeat.isChecked()

        elif btype == BTYPE_GUN:
            btn["gun_name"] = self._gun_name.text().strip() or "Custom Gun"
            btn["gun_badge"] = self._gun_badge.text().strip().upper() or "GN"
            try:
                btn["gun_dy"] = float(self._gun_dy.text())
            except ValueError:
                btn["gun_dy"] = 8.0
            try:
                btn["gun_dx"] = float(self._gun_dx.text())
            except ValueError:
                btn["gun_dx"] = 0.0
            btn["gun_slot"] = int(self._gun_slot.currentText())

        elif btype == BTYPE_CODE:
            btn["code"] = self._code_edit.toPlainText()

        self._result_btn = btn
        self.accept()

    def get_button(self) -> dict:
        return self._result_btn


class PageEditorDialog(QDialog):
    """Dialog to manage buttons on a single custom page."""

    page_changed = pyqtSignal()

    def __init__(self, parent, page_index: int):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setMinimumWidth(560)
        self._page_index = page_index

        t = get_theme()
        self.setStyleSheet(f"""
            QDialog {{ background-color:{t['bg']}; border:1px solid {t['border']}; border-radius:14px; }}
            QWidget {{ font-family:'Segoe UI','Helvetica Neue',sans-serif; font-size:13px; color:{t['text']}; background:transparent; }}
            QListWidget {{ background:rgba(255,255,255,0.03); border:1px solid {t['border']}; border-radius:8px; color:{t['subtext']}; padding:4px; outline:none; }}
            QListWidget::item {{ padding:8px 12px; border-radius:6px; }}
            QListWidget::item:selected {{ background:rgba(255,255,255,0.08); color:{t['text']}; }}
            QListWidget::item:hover {{ background:rgba(255,255,255,0.04); }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        page = custom_page_registry.pages[page_index]
        tbar = QFrame()
        tbar.setFixedHeight(46)
        tbar.setStyleSheet(f"background:{t['sidebar']}; border-bottom:1px solid {t['border']}; border-top-left-radius:14px; border-top-right-radius:14px;")
        tbar_lay = QHBoxLayout(tbar)
        tbar_lay.setContentsMargins(20, 0, 10, 0)
        icon = QLabel("◈")
        icon.setStyleSheet(f"color:{t['accent']}; font-size:14px; font-weight:900;")
        ttl = QLabel(f"Edit Page — {page['name']}")
        ttl.setStyleSheet(f"color:{t['text']}; font-size:13px; font-weight:800; margin-left:8px;")
        tbar_lay.addWidget(icon)
        tbar_lay.addWidget(ttl)
        tbar_lay.addStretch()
        root.addWidget(tbar)

        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(24, 20, 24, 20)
        body_lay.setSpacing(14)
        root.addWidget(body)

        # Button list
        self._list = QListWidget()
        self._list.setMinimumHeight(200)
        body_lay.addWidget(self._list)
        self._refresh_list()

        # Action buttons
        action_row = QHBoxLayout()
        btn_add = QPushButton("+ Add Button")
        btn_add.setObjectName("SaveBtn")
        btn_add.clicked.connect(self._add_button)

        btn_edit = QPushButton("Edit")
        btn_edit.setObjectName("NeutralBtn")
        btn_edit.clicked.connect(self._edit_button)

        btn_del = QPushButton("Delete")
        btn_del.setObjectName("DangerBtn")
        btn_del.clicked.connect(self._delete_button)

        action_row.addWidget(btn_add)
        action_row.addSpacing(8)
        action_row.addWidget(btn_edit)
        action_row.addSpacing(8)
        action_row.addWidget(btn_del)
        action_row.addStretch()
        body_lay.addLayout(action_row)

        close_row = QHBoxLayout()
        btn_close = QPushButton("Done")
        btn_close.setObjectName("SaveBtn")
        btn_close.clicked.connect(self.accept)
        close_row.addStretch()
        close_row.addWidget(btn_close)
        body_lay.addLayout(close_row)

    def _refresh_list(self):
        self._list.clear()
        page = custom_page_registry.pages[self._page_index]
        type_icons = {BTYPE_KEYBIND: "⌨", BTYPE_GUN: "🔫", BTYPE_CODE: "</>"}
        for btn in page["buttons"]:
            icon = type_icons.get(btn.get("type", ""), "•")
            self._list.addItem(f"{icon}  {btn.get('label', 'Button')}  [{btn.get('type','?')}]")

    def _add_button(self):
        dlg = ButtonEditorDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            btn = dlg.get_button()
            if btn:
                custom_page_registry.add_button(self._page_index, btn)
                self._refresh_list()
                self.page_changed.emit()

    def _edit_button(self):
        row = self._list.currentRow()
        if row < 0:
            return
        existing = custom_page_registry.pages[self._page_index]["buttons"][row]
        dlg = ButtonEditorDialog(self, existing=existing)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            btn = dlg.get_button()
            if btn:
                custom_page_registry.update_button(self._page_index, row, btn)
                self._refresh_list()
                self.page_changed.emit()

    def _delete_button(self):
        row = self._list.currentRow()
        if row < 0:
            return
        custom_page_registry.remove_button(self._page_index, row)
        self._refresh_list()
        self.page_changed.emit()


class NewPageDialog(QDialog):
    """Small dialog to name a new custom page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setFixedWidth(380)
        self._name = ""
        self._badge = ""

        t = get_theme()
        self.setStyleSheet(f"""
            QDialog {{ background-color:{t['bg']}; border:1px solid {t['border']}; border-radius:14px; }}
            QWidget {{ font-family:'Segoe UI','Helvetica Neue',sans-serif; font-size:13px; color:{t['text']}; background:transparent; }}
            QLineEdit {{ background:rgba(255,255,255,0.05); border:1px solid {t['border']}; border-radius:7px; padding:8px 12px; color:{t['text']}; }}
            QLineEdit:focus {{ border:1px solid {t['accent']}; }}
            QLabel#SectionLbl {{ font-size:10px; font-weight:700; letter-spacing:2px; color:{t['subtext']}; }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        tbar = QFrame()
        tbar.setFixedHeight(46)
        tbar.setStyleSheet(f"background:{t['sidebar']}; border-bottom:1px solid {t['border']}; border-top-left-radius:14px; border-top-right-radius:14px;")
        tbar_lay = QHBoxLayout(tbar)
        tbar_lay.setContentsMargins(20, 0, 10, 0)
        icon = QLabel("✦")
        icon.setStyleSheet(f"color:{t['accent']}; font-size:14px; font-weight:900;")
        ttl = QLabel("New Page")
        ttl.setStyleSheet(f"color:{t['text']}; font-size:13px; font-weight:800; margin-left:8px;")
        tbar_lay.addWidget(icon)
        tbar_lay.addWidget(ttl)
        tbar_lay.addStretch()
        root.addWidget(tbar)

        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(24, 20, 24, 20)
        body_lay.setSpacing(12)
        root.addWidget(body)

        name_lbl = QLabel("PAGE NAME")
        name_lbl.setObjectName("SectionLbl")
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("e.g. My Macros")
        body_lay.addWidget(name_lbl)
        body_lay.addWidget(self._name_input)

        badge_lbl = QLabel("BADGE (2-3 chars shown in sidebar)")
        badge_lbl.setObjectName("SectionLbl")
        self._badge_input = QLineEdit()
        self._badge_input.setPlaceholderText("e.g. MC")
        self._badge_input.setMaxLength(3)
        body_lay.addWidget(badge_lbl)
        body_lay.addWidget(self._badge_input)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("NeutralBtn")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Create Page")
        btn_ok.setObjectName("SaveBtn")
        btn_ok.clicked.connect(self._do_create)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addSpacing(8)
        btn_row.addWidget(btn_ok)
        body_lay.addLayout(btn_row)

    def _do_create(self):
        self._name = self._name_input.text().strip() or "My Page"
        self._badge = self._badge_input.text().strip().upper() or self._name[:2].upper()
        self.accept()

    def get_result(self):
        return self._name, self._badge


# =============================================================================
# MAIN WINDOW
# =============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Obsidian Client")
        self.resize(1225, 940)
        # Remove OS chrome
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self._drag_pos = QPoint()
        self._ui_animations = []
        self.setWindowOpacity(0.0)
        self._apply_theme()

        self.threads = [CrystalMacro(), AnchorMacro(), UtilityMacro(), StunMacro(), ShieldBreakerMacro(), StunSlamMacro(), BreachSwapMacro(), CartMacro(), TrapCartMacro(), PearlCatchMacro(), RC4Macro(), SMG12Macro(), F2Macro(), VectorMacro(), UZK50GIMacro(), C70Macro(), TurnFlickMacro(), ScizoMacro(), FastClickerMacro()]
        self._custom_gun_threads: list[CustomGunMacro] = []
        for gun in gun_registry.guns:
            t2 = CustomGunMacro(gun)
            self._custom_gun_threads.append(t2)
            self.threads.append(t2)
        for t in self.threads:
            t.start()

        # Debounced save — coalesces rapid slider/input changes into one write
        # after 500 ms of inactivity. cfg.save() is rerouted through this.
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(cfg._do_save)
        cfg._schedule_save = self._save_timer.start

        # Autosave every 5 seconds as a safety net for anything that bypasses debounce
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(cfg._do_save)
        self._autosave_timer.start(5000)

        # Root vertical layout: title bar on top, then sidebar+content below
        root_widget = QWidget()
        self.setCentralWidget(root_widget)
        root_vlay = QVBoxLayout(root_widget)
        root_vlay.setContentsMargins(0, 0, 0, 0)
        root_vlay.setSpacing(0)

        self._title_bar = self._build_title_bar()
        root_vlay.addWidget(self._title_bar)

        body_widget = QWidget()
        self.layout = QHBoxLayout(body_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        root_vlay.addWidget(body_widget)

        self.setup_sidebar()
        self.content_stack = QStackedWidget()
        self.layout.addWidget(self.content_stack)

        self.home_page = self.create_home_page()
        self.theme_page = self.create_theme_page()
        self.overlay_page = self.create_overlay_page()
        self.settings_page = self.create_settings_page()

        self.content_stack.addWidget(self.home_page)           # 0
        self.content_stack.addWidget(self.theme_page)          # 1
        self.content_stack.addWidget(self.overlay_page)        # 2
        self.content_stack.addWidget(self.settings_page)       # 3

        self.overlay_window = OverlayWindow(self)
        self.overlay_window.apply_settings()
        self._normal_geometry = self.geometry()
        self._client_overlay_visible = True
        self._client_window_anims = []

        self._gun_toggle_key_down = {}
        self._client_overlay_key_down = False
        self._gun_toggle_timer = QTimer(self)
        self._gun_toggle_timer.timeout.connect(self._poll_gun_toggle_keys)
        self._gun_toggle_timer.start(10)

        # ── Custom pages (loaded from registry) ──
        self._custom_page_widgets: list[QWidget] = []
        self._custom_page_buttons: list[QPushButton] = []
        self._load_custom_pages()
        QTimer.singleShot(80, self._animate_intro)

    def _build_title_bar(self):
        t = get_theme()
        bar = QFrame()
        bar.setObjectName("TitleBar")
        bar.setFixedHeight(44)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 0, 0, 0)
        lay.setSpacing(10)

        icon_lbl = QLabel("◈")
        icon_lbl.setText("◆")
        icon_lbl.setStyleSheet(f"color:{t['accent']}; font-size:15px; font-weight:900;")
        name_lbl = QLabel("Obsidian Client")
        name_lbl.setStyleSheet(f"color:{t['text']}; font-size:13px; font-weight:800; margin-left:2px;")

        lay.addWidget(icon_lbl)
        lay.addWidget(name_lbl)
        lay.addStretch()

        btn_min = QPushButton("—")
        self._profile_chip = QLabel("Profile: Default")
        self._overlay_chip = QLabel(f"Overlay: {'On' if cfg.overlay.enabled else 'Off'}")
        self._theme_chip = QLabel(f"Theme: {_current_theme_name}")
        for chip in (self._profile_chip, self._overlay_chip, self._theme_chip):
            chip.setObjectName("TitleChip")
            lay.addWidget(chip)

        btn_min.setText("-")
        btn_min.setObjectName("WinMinimize")
        btn_min.clicked.connect(self.showMinimized)

        btn_close = QPushButton("✕")
        btn_close.setText("x")
        btn_close.setObjectName("WinClose")
        btn_close.clicked.connect(self.close)

        lay.addWidget(btn_min)
        lay.addWidget(btn_close)

        # Make bar draggable
        bar.mousePressEvent   = self._tb_mouse_press
        bar.mouseMoveEvent    = self._tb_mouse_move
        bar.mouseDoubleClickEvent = self._tb_double_click
        return bar

    def _tb_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _tb_mouse_move(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def _tb_double_click(self, event):
        pass # Disable double-click to maximize to prevent "breaking windows"

    def _apply_theme(self):
        self.setStyleSheet(build_stylesheet(get_theme()))

    def _change_theme(self, name):
        global _current_theme_name
        _current_theme_name = name
        cfg.save()
        self._apply_theme()
        if hasattr(self, "content_stack") and hasattr(self, "home_page"):
            self._rebuild_core_pages_for_theme()
        t = get_theme()
        for child in self._title_bar.findChildren(QLabel):
            if child.text() == "◆":
                child.setStyleSheet(f"color:{t['accent']}; font-size:15px; font-weight:900;")
                continue
            if child.text() == "◈":
                child.setStyleSheet(f"color:{t['accent']}; font-size:15px; font-weight:900;")
            elif "Obsidian" in child.text():
                child.setStyleSheet(f"color:{t['text']}; font-size:13px; font-weight:800; margin-left:2px;")
        if hasattr(self, '_theme_dots'):
            for n, btn in self._theme_dots.items():
                btn.setChecked(n == name)
        if hasattr(self, "_theme_chip"):
            self._theme_chip.setText(f"Theme: {name}")
        if hasattr(self, "_overlay_chip"):
            self._overlay_chip.setText(f"Overlay: {'On' if cfg.overlay.enabled else 'Off'}")
        if hasattr(self, "overlay_window"):
            self.overlay_window.refresh()

    def _rebuild_core_pages_for_theme(self):
        current_index = self.content_stack.currentIndex()
        old_pages = [self.home_page, self.theme_page, self.overlay_page, self.settings_page]
        for page in old_pages:
            self.content_stack.removeWidget(page)
            page.deleteLater()

        self.home_page = self.create_home_page()
        self.theme_page = self.create_theme_page()
        self.overlay_page = self.create_overlay_page()
        self.settings_page = self.create_settings_page()
        self.content_stack.insertWidget(0, self.home_page)
        self.content_stack.insertWidget(1, self.theme_page)
        self.content_stack.insertWidget(2, self.overlay_page)
        self.content_stack.insertWidget(3, self.settings_page)
        self.content_stack.setCurrentIndex(min(current_index, self.content_stack.count() - 1))

    def _track_animation(self, anim):
        self._ui_animations.append(anim)
        anim.finished.connect(lambda: self._ui_animations.remove(anim) if anim in self._ui_animations else None)
        anim.start()

    def _fade_widget(self, widget, duration=220):
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: widget.setGraphicsEffect(None))
        self._track_animation(anim)

    def _animate_intro(self):
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(260)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._track_animation(fade)
        self._animate_page_widgets(self.content_stack.currentWidget())

    def _animate_page_widgets(self, page):
        if page is None:
            return
        for i, card in enumerate(page.findChildren(Card)[:18]):
            start_pos = card.pos() + QPoint(0, 10)
            end_pos = card.pos()
            card.move(start_pos)
            pos_anim = QPropertyAnimation(card, b"pos", self)
            pos_anim.setDuration(260)
            pos_anim.setStartValue(start_pos)
            pos_anim.setEndValue(end_pos)
            pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            QTimer.singleShot(i * 35, lambda a=pos_anim: self._track_animation(a))

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # ── App title ──
        t = get_theme()
        title_widget = QWidget()
        title_widget.setFixedHeight(74)
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(20, 0, 20, 0)
        app_title = QLabel("OBSIDIAN")
        app_title.setStyleSheet(f"font-size:19px; font-weight:900; color:{t['accent']}; letter-spacing:3px;")
        sub_title = QLabel("v1.8.5")
        sub_title.setObjectName("BadgeLabel")
        sub_title.setStyleSheet(f"font-size:10px; color:{t['subtext']}; font-weight:600;")
        title_layout.addWidget(app_title)
        title_layout.addStretch()
        title_layout.addWidget(sub_title)
        sidebar_layout.addWidget(title_widget)

        # ── Divider ──
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{t['border']};")
        sidebar_layout.addWidget(div)

        self.btn_home = QPushButton("  Home")
        self.btn_home.setObjectName("SidebarButton")
        self.btn_home.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_home.setCheckable(True)
        self.btn_home.setChecked(True)
        self.btn_home.clicked.connect(lambda: self.switch_page(0))
        sidebar_layout.addWidget(self.btn_home)

        # ── MY PAGES section ──
        my_pages_lbl = QLabel("MY PAGES")
        my_pages_lbl.setObjectName("SidebarSection")
        self._my_pages_lbl = my_pages_lbl
        sidebar_layout.addWidget(my_pages_lbl)

        # Container for dynamic page buttons
        self._pages_btn_container = QWidget()
        self._pages_btn_layout = QVBoxLayout(self._pages_btn_container)
        self._pages_btn_layout.setContentsMargins(0, 0, 0, 0)
        self._pages_btn_layout.setSpacing(0)
        sidebar_layout.addWidget(self._pages_btn_container)

        # + New Page button
        btn_new_page = QPushButton("  + New Page")
        btn_new_page.setObjectName("SidebarButton")
        btn_new_page.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new_page.clicked.connect(self._create_new_page)
        btn_new_page.setStyleSheet(f"color:{get_theme()['accent']}; font-size:12px;")
        self._new_page_btn = btn_new_page
        sidebar_layout.addWidget(btn_new_page)

        # ── OTHER section ──
        other_lbl = QLabel("OTHER")
        other_lbl.setObjectName("SidebarSection")
        sidebar_layout.addWidget(other_lbl)

        self.btn_theme = QPushButton("  Theme")
        self.btn_theme.setObjectName("SidebarButton")
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.setCheckable(True)
        self.btn_theme.clicked.connect(lambda: self.switch_page(1))
        sidebar_layout.addWidget(self.btn_theme)

        self.btn_overlay = QPushButton("  Overlay")
        self.btn_overlay.setObjectName("SidebarButton")
        self.btn_overlay.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_overlay.setCheckable(True)
        self.btn_overlay.clicked.connect(lambda: self.switch_page(2))
        sidebar_layout.addWidget(self.btn_overlay)

        self.btn_settings = QPushButton("  Settings")
        self.btn_settings.setObjectName("SidebarButton")
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setCheckable(True)
        self.btn_settings.clicked.connect(lambda: self.switch_page(3))
        sidebar_layout.addWidget(self.btn_settings)

        sidebar_layout.addStretch()
        status_mode = QLabel("UI Mode: Full")
        status_mode.setObjectName("SidebarStatus")
        status_key = QLabel(f"Hotkey: {str(cfg.client_overlay.toggle_key or 'Not bound').upper()}")
        status_key.setObjectName("SidebarStatus")
        sidebar_layout.addWidget(status_mode)
        sidebar_layout.addWidget(status_key)
        sidebar_layout.addSpacing(16)
        self.layout.addWidget(self.sidebar)

        has_custom_pages = bool(custom_page_registry.pages)
        self._my_pages_lbl.setVisible(has_custom_pages)
        self._pages_btn_container.setVisible(has_custom_pages)

    def switch_page(self, index):
        self.content_stack.setCurrentIndex(index)
        self._fade_widget(self.content_stack.currentWidget(), 190)
        QTimer.singleShot(30, lambda: self._animate_page_widgets(self.content_stack.currentWidget()))
        self.btn_home.setChecked(index == 0)
        self.btn_theme.setChecked(index == 1)
        self.btn_overlay.setChecked(index == 2)
        self.btn_settings.setChecked(index == 3)
        for i, btn in enumerate(self._custom_page_buttons):
            btn.setChecked(index == (i + 4))

    def _poll_gun_toggle_keys(self):
        if any(getattr(btn, "listening", False) for btn in self.findChildren(KeybindButton)):
            return

        self._poll_client_overlay_key()

        active_keys = set()
        for name, settings, registry_index in _all_recoil_guns():
            key = str(getattr(settings, "toggle_key", "") or "").strip().lower()
            if not key or key == "none":
                continue
            active_keys.add(key)
            pressed = InputController.is_key_pressed(key)
            was_pressed = self._gun_toggle_key_down.get(key, False)
            if pressed and not was_pressed:
                self._toggle_gun_from_key(settings, registry_index)
            self._gun_toggle_key_down[key] = pressed

        for key in list(self._gun_toggle_key_down.keys()):
            if key not in active_keys:
                self._gun_toggle_key_down.pop(key, None)

    def _toggle_gun_from_key(self, settings, registry_index):
        settings.enabled = not bool(getattr(settings, "enabled", False))
        if registry_index is None:
            cfg.save()
        else:
            gun_registry.save()
        if hasattr(self, "overlay_window"):
            self.overlay_window.refresh()
        if hasattr(self, "_refresh_gun_grid") and self.content_stack.currentIndex() == 0:
            self._refresh_gun_grid()

    def _poll_client_overlay_key(self):
        key = str(cfg.client_overlay.toggle_key or "").strip().lower()
        if not cfg.client_overlay.enabled or not key or key == "none":
            self._client_overlay_key_down = False
            return
        pressed = InputController.is_key_pressed(key)
        if pressed and not self._client_overlay_key_down:
            self._toggle_client_overlay_window()
        self._client_overlay_key_down = pressed

    def _apply_client_overlay_flags(self, compact: bool):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(compact and cfg.client_overlay.keep_on_top))
        self.setWindowFlag(Qt.WindowType.Tool, bool(compact))

    def _apply_window_rounding(self, rounded: bool):
        if not rounded:
            self.clearMask()
            return
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _animate_client_window(self, start_pos: QPoint, end_pos: QPoint, start_opacity: float, end_opacity: float, on_done=None):
        for anim in list(self._client_window_anims):
            anim.stop()
        self._client_window_anims.clear()

        self.move(start_pos)
        self.setWindowOpacity(start_opacity)

        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(145)
        fade.setStartValue(start_opacity)
        fade.setEndValue(end_opacity)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        slide = QPropertyAnimation(self, b"pos", self)
        slide.setDuration(145)
        slide.setStartValue(start_pos)
        slide.setEndValue(end_pos)
        slide.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._client_window_anims.extend([fade, slide])
        fade.finished.connect(lambda: (
            self._client_window_anims.clear(),
            on_done() if on_done else None
        ))
        fade.start()
        slide.start()

    def _compact_client_target_pos(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return self.pos()
        geo = screen.availableGeometry()
        return QPoint(
            geo.x() + max(20, (geo.width() - self.width()) // 2),
            geo.y() + 60
        )

    def _show_client_overlay_window(self):
        if not cfg.client_overlay.enabled:
            self.show()
            return
        if not self._client_overlay_visible:
            self._client_overlay_visible = True
        self._apply_client_overlay_flags(True)
        compact_width = max(1225, min(1500, cfg.client_overlay.compact_width))
        compact_height = max(460, min(940, cfg.client_overlay.compact_height))
        if compact_width != cfg.client_overlay.compact_width or compact_height != cfg.client_overlay.compact_height:
            cfg.client_overlay.compact_width = compact_width
            cfg.client_overlay.compact_height = compact_height
            cfg.save()
        self.resize(compact_width, compact_height)
        self._apply_window_rounding(True)
        target_pos = self._compact_client_target_pos()
        start_pos = target_pos + QPoint(-34, -34)
        self.show()
        self.raise_()
        self.activateWindow()
        self._animate_client_window(start_pos, target_pos, 0.0, 1.0)

    def _hide_client_overlay_window(self):
        if self.isVisible():
            self._normal_geometry = self.geometry()
            start_pos = self.pos()
        else:
            start_pos = self.pos()
        self._client_overlay_visible = False
        end_pos = start_pos + QPoint(34, 34)

        def _finish_hide():
            self._apply_client_overlay_flags(False)
            self.hide()
            self.setWindowOpacity(1.0)

        self._animate_client_window(start_pos, end_pos, self.windowOpacity(), 0.0, _finish_hide)

    def _toggle_client_overlay_window(self):
        if self.isVisible() and self._client_overlay_visible:
            self._hide_client_overlay_window()
        else:
            self._show_client_overlay_window()

    def _leave_client_overlay_mode(self):
        self._apply_client_overlay_flags(False)
        self._apply_window_rounding(False)
        self._client_overlay_visible = True
        self.setWindowOpacity(1.0)
        self.show()
        if self._normal_geometry.isValid():
            self.setGeometry(self._normal_geometry)

    def _page_header(self, title, subtitle=""):
        t = get_theme()
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(2)
        h = QLabel(title)
        h.setStyleSheet(f"font-size:22px; font-weight:800; color:{t['text']};")
        l.addWidget(h)
        if subtitle:
            s = QLabel(subtitle)
            s.setStyleSheet(f"font-size:12px; color:{t['subtext']};")
            l.addWidget(s)
        return w

    def _build_mini_gun_card(self, title, badge, settings, registry_index=None):
        """Compact card: badge + title + toggle + strength slider.
        registry_index: if not None, this is a custom gun and gets a Remove button."""
        t = get_theme()
        frame = QFrame()
        frame.setObjectName("Card")
        frame.setProperty("active", "true" if settings.enabled else "false")
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(6)

        # ── Header: badge + title + toggle ──
        hdr = QHBoxLayout()
        hdr.setSpacing(8)

        badge_lbl = QLabel(badge)
        badge_lbl.setObjectName("BadgeLabel")
        badge_lbl.setFixedSize(30, 30)
        badge_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.addWidget(badge_lbl)

        name_lbl = QLabel(title)
        name_lbl.setObjectName("CardTitle")
        name_lbl.setStyleSheet(f"font-size:12px; font-weight:700; color:{t['text']};")
        hdr.addWidget(name_lbl)

        # ── Favorite Button (Star) ──
        is_fav = title in cfg.favorites
        fav_btn = QPushButton("★" if is_fav else "☆")
        fav_btn.setFixedSize(24, 24)
        fav_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {t['accent'] if is_fav else t['subtext']};
                font-size: 16px;
                border: none;
            }}
            QPushButton:hover {{ color: {t['accent']}; }}
        """)

        def _on_fav(_settings=settings, _title=title, _btn=fav_btn):
            if _title in cfg.favorites:
                cfg.favorites.remove(_title)
                _btn.setText("☆")
                _btn.setStyleSheet(f"QPushButton {{ background:transparent; color:{t['subtext']}; font-size:16px; border:none; }} QPushButton:hover {{ color:{t['accent']}; }}")
            else:
                cfg.favorites.append(_title)
                _btn.setText("★")
                _btn.setStyleSheet(f"QPushButton {{ background:transparent; color:{t['accent']}; font-size:16px; border:none; }} QPushButton:hover {{ color:{t['accent']}; }}")
            cfg.save()
            # Refresh grid to move favorite to top
            self._refresh_gun_grid()

        fav_btn.clicked.connect(_on_fav)
        hdr.addWidget(fav_btn)
        hdr.addStretch()

        toggle = ToggleButton(checked=settings.enabled)
        toggle.setFixedWidth(52)
        toggle.setVisible(False)

        def _on_toggle(s, _settings=settings, _frame=frame):
            setattr(_settings, 'enabled', bool(s))
            _frame.setProperty("active", "true" if s else "false")
            _frame.style().unpolish(_frame)
            _frame.style().polish(_frame)
            if isinstance(_settings, CustomGunSettings):
                gun_registry.save()
            else:
                cfg.save()

        toggle.toggled_state.connect(_on_toggle)
        hdr.addWidget(toggle)
        outer.addLayout(hdr)

        frame.setCursor(Qt.CursorShape.PointingHandCursor)

        def _toggle_from_card(event, _toggle=toggle):
            if event.button() == Qt.MouseButton.LeftButton:
                _toggle.click()
                event.accept()
                return
            QFrame.mousePressEvent(frame, event)

        frame.mousePressEvent = _toggle_from_card
        for target in (badge_lbl, name_lbl):
            target.setCursor(Qt.CursorShape.PointingHandCursor)
            target.mousePressEvent = _toggle_from_card

        # ── Thin divider ──
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"background:{t['border']}; max-height:1px; margin:2px 0;")
        outer.addWidget(div)

        # ── Mini strength slider ──
        key_row = QHBoxLayout()
        key_row.setSpacing(6)
        key_lbl = QLabel("Toggle Key")
        key_lbl.setObjectName("RowLabel")
        key_lbl.setStyleSheet(f"font-size:11px; color:{t['subtext']};")
        key_btn = KeybindButton(getattr(settings, "toggle_key", "") or "none")
        key_btn.setFixedWidth(78)
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(54)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255,255,255,0.045);
                color: {t['subtext']};
                font-size: 10px;
                font-weight: 700;
                border: 1px solid {t['border']};
                border-radius: 5px;
                padding: 3px 7px;
            }}
            QPushButton:hover {{ color:{t['accent']}; border-color:{t['accent']}; }}
        """)

        def _save_toggle_key(k, _settings=settings, _btn=key_btn):
            key = "" if str(k).lower() == "none" else str(k).lower()
            setattr(_settings, "toggle_key", key)
            _btn.setText(_format_keybind(key))
            if isinstance(_settings, CustomGunSettings):
                gun_registry.save()
            else:
                cfg.save()

        key_btn.key_changed.connect(_save_toggle_key)
        clear_btn.clicked.connect(lambda _checked=False: _save_toggle_key(""))
        key_row.addWidget(key_lbl)
        key_row.addStretch()
        key_row.addWidget(key_btn)
        key_row.addWidget(clear_btn)
        outer.addLayout(key_row)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(6)
        s_lbl = QLabel("Strength")
        s_lbl.setObjectName("RowLabel")
        s_lbl.setStyleSheet(f"font-size:11px; color:{t['subtext']};")
        val_lbl = QLabel(str(settings.strength))
        val_lbl.setStyleSheet(f"color:{t['accent']}; font-weight:700; font-size:11px; min-width:22px;")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(1, 100)
        slider.setValue(settings.strength)
        slider.setFixedWidth(120)
        slider.setStyleSheet(slider_stylesheet(t))

        def _on_strength(v, _settings=settings, _val_lbl=val_lbl):
            _val_lbl.setText(str(v))
            setattr(_settings, 'strength', v)
            if isinstance(_settings, CustomGunSettings):
                gun_registry.save()
            else:
                cfg.save()

        slider.valueChanged.connect(_on_strength)

        slider_row.addWidget(s_lbl)
        slider_row.addStretch()
        slider_row.addWidget(val_lbl)
        slider_row.addWidget(slider)
        outer.addLayout(slider_row)

        # ── Remove button — only for custom guns, shown before macro is running permanently ──
        if registry_index is not None:
            remove_row = QHBoxLayout()
            remove_row.addStretch()
            rm_btn = QPushButton("✕  Remove")
            rm_btn.setFixedHeight(22)
            rm_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(220,50,50,0.12);
                    color: #c05050;
                    font-size: 10px;
                    font-weight: 700;
                    border: 1px solid rgba(220,50,50,0.25);
                    border-radius: 5px;
                    padding: 0 10px;
                }}
                QPushButton:hover {{
                    background-color: rgba(220,50,50,0.28);
                    color: #e06060;
                }}
            """)

            def _on_remove(_checked=False, _idx=registry_index, _gun=settings):
                msg = f'Remove "{_gun.name}" permanently from custom_guns.json?\n\nThe macro will stop immediately.'
                reply = QMessageBox.question(
                    frame, "Remove Gun", msg,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    # Stop the associated macro thread
                    main_win = self._find_main_window(frame)
                    if main_win:
                        main_win._remove_custom_gun(_idx)

            rm_btn.clicked.connect(_on_remove)
            remove_row.addWidget(rm_btn)
            outer.addLayout(remove_row)

        # Glow effect
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        glow = QGraphicsDropShadowEffect(frame)
        glow.setBlurRadius(16)
        glow.setOffset(0, 0)
        if settings.enabled:
            r = int(t['accent'][1:3], 16)
            g = int(t['accent'][3:5], 16)
            b = int(t['accent'][5:7], 16)
            glow.setColor(QColor(r, g, b, 50))
        else:
            glow.setColor(QColor(0, 0, 0, 0))
        frame.setGraphicsEffect(glow)

        return frame

    @staticmethod
    def _find_main_window(widget):
        """Walk up the parent chain to find the MainWindow instance."""
        p = widget.parent()
        while p is not None:
            if isinstance(p, MainWindow):
                return p
            p = p.parent()
        return None

    def create_home_page(self):
        t = get_theme()
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        layout.addWidget(self._page_header("Home", "Quick overview and controls"))

        # ── Sensitivity card (compact) ──
        sens_card = Card("Sensitivity", "Sens 13 = baseline. Scales all recoil automatically.", badge="SN")
        sens_card.toggle.hide()

        sens_h_row = QHBoxLayout()
        sens_h_lbl = QLabel("Horizontal")
        sens_h_lbl.setObjectName("RowLabel")
        sens_h_val = QLabel(str(cfg.sensitivity.horizontal))
        sens_h_val.setStyleSheet(f"color:{t['accent']}; font-weight:700; font-size:12px; min-width:22px;")
        sens_h_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        sens_h_slider = QSlider(Qt.Orientation.Horizontal)
        sens_h_slider.setRange(6, 100)
        sens_h_slider.setValue(cfg.sensitivity.horizontal)
        sens_h_slider.setFixedWidth(140)
        sens_h_slider.setStyleSheet(slider_stylesheet(t))
        sens_h_slider.valueChanged.connect(lambda v: (
            sens_h_val.setText(str(v)),
            setattr(cfg.sensitivity, 'horizontal', v),
            cfg.save()
        ))
        sens_h_row.addWidget(sens_h_lbl)
        sens_h_row.addStretch()
        sens_h_row.addWidget(sens_h_val)
        sens_h_row.addSpacing(8)
        sens_h_row.addWidget(sens_h_slider)
        sens_card.content_layout.addLayout(sens_h_row)

        sens_v_row = QHBoxLayout()
        sens_v_lbl = QLabel("Vertical")
        sens_v_lbl.setObjectName("RowLabel")
        sens_v_val = QLabel(str(cfg.sensitivity.vertical))
        sens_v_val.setStyleSheet(f"color:{t['accent']}; font-weight:700; font-size:12px; min-width:22px;")
        sens_v_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        sens_v_slider = QSlider(Qt.Orientation.Horizontal)
        sens_v_slider.setRange(6, 100)
        sens_v_slider.setValue(cfg.sensitivity.vertical)
        sens_v_slider.setFixedWidth(140)
        sens_v_slider.setStyleSheet(slider_stylesheet(t))
        sens_v_slider.valueChanged.connect(lambda v: (
            sens_v_val.setText(str(v)),
            setattr(cfg.sensitivity, 'vertical', v),
            cfg.save()
        ))
        sens_v_row.addWidget(sens_v_lbl)
        sens_v_row.addStretch()
        sens_v_row.addWidget(sens_v_val)
        sens_v_row.addSpacing(8)
        sens_v_row.addWidget(sens_v_slider)
        sens_card.content_layout.addLayout(sens_v_row)

        layout.addWidget(sens_card)

        # ── Turn Flick card ──
        tf_section_lbl = QLabel("SILLY SPINNNY")
        tf_section_lbl.setObjectName("SidebarSection")
        tf_section_lbl.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(tf_section_lbl)

        tf_card = Card("Silly Spinnny",
                       "spins on the schizo",
                       badge="SS")
        tf_card.toggle.setChecked(cfg.turnflick.enabled)
        tf_card.make_click_toggle()
        tf_card.update_appearance(cfg.turnflick.enabled)

        def _on_tf_toggle(s):
            cfg.turnflick.enabled = bool(s)
            cfg.save()
        tf_card.toggle.toggled_state.connect(_on_tf_toggle)

        slider_style_tf = f"""
            QSlider::groove:horizontal {{ height:3px; background:rgba(255,255,255,0.08); border-radius:2px; }}
            QSlider::handle:horizontal {{ background:{t['accent']}; width:13px; height:13px; margin:-5px 0; border-radius:7px; }}
            QSlider::sub-page:horizontal {{ background:{t['accent']}; border-radius:2px; }}
        """

        # ── Key bind row ──
        key_row = QHBoxLayout()
        key_lbl = QLabel("Activate Key")
        key_lbl.setObjectName("RowLabel")
        tf_key_btn = KeybindButton(cfg.turnflick.activator_key)
        def _on_tf_key(k):
            cfg.turnflick.activator_key = k
            cfg.save()
        tf_key_btn.key_changed.connect(_on_tf_key)
        key_row.addWidget(key_lbl)
        key_row.addStretch()
        key_row.addWidget(tf_key_btn)
        tf_card.content_layout.addLayout(key_row)

        # ── Direction toggle row ──
        dir_row = QHBoxLayout()
        dir_lbl = QLabel("Direction")
        dir_lbl.setObjectName("RowLabel")

        def _dir_btn_style(active):
            if active:
                return (f"QPushButton {{ background-color:{t['accent']}; color:#000; font-weight:700; "
                        f"border-radius:6px; padding:4px 14px; border:none; font-size:12px; }}")
            return (f"QPushButton {{ background-color:rgba(255,255,255,0.06); color:{t['text']}; font-weight:600; "
                    f"border-radius:6px; padding:4px 14px; border:1px solid {t['border']}; font-size:12px; }}")

        tf_left_btn  = QPushButton("◀  Left")
        tf_right_btn = QPushButton("Right  ▶")
        tf_left_btn.setStyleSheet(_dir_btn_style(cfg.turnflick.direction == "left"))
        tf_right_btn.setStyleSheet(_dir_btn_style(cfg.turnflick.direction == "right"))

        def _set_dir(d):
            cfg.turnflick.direction = d
            tf_left_btn.setStyleSheet(_dir_btn_style(d == "left"))
            tf_right_btn.setStyleSheet(_dir_btn_style(d == "right"))
            cfg.save()

        tf_left_btn.clicked.connect(lambda: _set_dir("left"))
        tf_right_btn.clicked.connect(lambda: _set_dir("right"))

        dir_row.addWidget(dir_lbl)
        dir_row.addStretch()
        dir_row.addWidget(tf_left_btn)
        dir_row.addSpacing(6)
        dir_row.addWidget(tf_right_btn)
        tf_card.content_layout.addLayout(dir_row)

        # ── Repeats slider (1–10) ──
        rep_row = QHBoxLayout()
        rep_lbl = QLabel("Repeats")
        rep_lbl.setObjectName("RowLabel")
        rep_val_lbl = QLabel(str(cfg.turnflick.repeats))
        rep_val_lbl.setStyleSheet(f"color:{t['accent']}; font-weight:700; font-size:12px; min-width:20px;")
        rep_val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        rep_slider = QSlider(Qt.Orientation.Horizontal)
        rep_slider.setRange(1, 100)
        rep_slider.setValue(cfg.turnflick.repeats)
        rep_slider.setStyleSheet(slider_style_tf)
        def _on_rep_change(v):
            cfg.turnflick.repeats = v
            rep_val_lbl.setText(str(v))
            cfg.save()
        rep_slider.valueChanged.connect(_on_rep_change)
        rep_row.addWidget(rep_lbl)
        rep_row.addSpacing(8)
        rep_row.addWidget(rep_val_lbl)
        rep_row.addSpacing(8)
        rep_row.addWidget(rep_slider)
        tf_card.content_layout.addLayout(rep_row)

        # ── Pixels slider (10–300, displayed as 10→1000 scaled ×~3.3 for readability) ──
        # We store raw pixels (sens-unscaled). The slider maps 1–10 → 10–300 px,
        # and we show the approximate degree-equivalent label.
        # Slider position 1 = ~10 px ≈ ~8°, position 10 = ~300 px ≈ 90°+ at sens 13.
        # We keep it simple: label shows slider value × 10 for a clean "10–100" feel.
        px_row = QHBoxLayout()
        px_lbl = QLabel("Turn Distance")
        px_lbl.setObjectName("RowLabel")

        # Map stored pixels (10–300) to slider value (1–10) and back
        def _px_to_slider(px): return max(1, min(10, round(px / 30)))
        def _slider_to_px(v): return v * 30

        px_val_lbl = QLabel(f"{_px_to_slider(cfg.turnflick.pixels) * 10}%")
        px_val_lbl.setStyleSheet(f"color:{t['accent']}; font-weight:700; font-size:12px; min-width:34px;")
        px_val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        px_slider = QSlider(Qt.Orientation.Horizontal)
        px_slider.setRange(1, 10)
        px_slider.setValue(_px_to_slider(cfg.turnflick.pixels))
        px_slider.setStyleSheet(slider_style_tf)

        def _on_px_change(v):
            cfg.turnflick.pixels = _slider_to_px(v)
            px_val_lbl.setText(f"{v * 10}%")
            cfg.save()
        px_slider.valueChanged.connect(_on_px_change)

        px_row.addWidget(px_lbl)
        px_row.addSpacing(8)
        px_row.addWidget(px_val_lbl)
        px_row.addSpacing(8)
        px_row.addWidget(px_slider)
        tf_card.content_layout.addLayout(px_row)

        layout.addWidget(tf_card)

        # ── Scizo card ──
        scizo_section_lbl = QLabel("SCIZO MODE")
        scizo_section_lbl.setObjectName("SidebarSection")
        scizo_section_lbl.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(scizo_section_lbl)

        scizo_card = Card("Scizo", "", badge="SZ")
        scizo_card.desc_label.setVisible(False)

        slider_style_sz = f"""
            QSlider::groove:horizontal {{ height:3px; background:rgba(255,255,255,0.08); border-radius:2px; }}
            QSlider::handle:horizontal {{ background:{t['accent']}; width:13px; height:13px; margin:-5px 0; border-radius:7px; }}
            QSlider::sub-page:horizontal {{ background:{t['accent']}; border-radius:2px; }}
        """

        # ── Master keybind row ──
        sz_key_row = QHBoxLayout()
        sz_key_lbl = QLabel("Toggle Keybind")
        sz_key_lbl.setObjectName("RowLabel")
        sz_key_btn = KeybindButton(cfg.scizo.activator_key)
        def _on_sz_key(k):
            cfg.scizo.activator_key = k
            cfg.save()
        sz_key_btn.key_changed.connect(_on_sz_key)
        sz_key_row.addWidget(sz_key_lbl)
        sz_key_row.addStretch()
        sz_key_row.addWidget(sz_key_btn)
        scizo_card.content_layout.addLayout(sz_key_row)

        # ── Divider label ──
        feat_lbl = QLabel("FEATURES  —  toggle which are armed")
        feat_lbl.setStyleSheet(f"font-size:10px; font-weight:700; letter-spacing:2px; color:{t['subtext']}; margin-top:4px;")
        scizo_card.content_layout.addWidget(feat_lbl)

        def _sz_toggle_row(label, attr):
            """Helper: one feature row that toggles by clicking the row."""
            row_frame = QFrame()
            row_frame.setCursor(Qt.CursorShape.PointingHandCursor)
            row = QHBoxLayout(row_frame)
            row.setContentsMargins(10, 7, 10, 7)
            lbl = QLabel(label)
            lbl.setObjectName("RowLabel")
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            btn = ToggleButton(checked=getattr(cfg.scizo, attr))
            btn.setVisible(False)

            def _apply(active):
                row_frame.setStyleSheet(
                    f"QFrame {{ background-color:{_rgba(t['accent'], 0.12) if active else _rgba(t['text'], 0.035)}; "
                    f"border:1px solid {_rgba(t['accent'], 0.34) if active else _rgba(t['text'], 0.08)}; "
                    "border-radius:7px; }}"
                )
                lbl.setStyleSheet(
                    f"color:{t['accent'] if active else t['subtext']}; "
                    "font-size:12px; font-weight:700;"
                )

            def _on(s, a=attr):
                setattr(cfg.scizo, a, bool(s))
                _apply(bool(s))
                cfg.save()
            btn.toggled_state.connect(_on)

            def _toggle(event):
                if event.button() == Qt.MouseButton.LeftButton:
                    btn.click()
                    event.accept()
                    return
                QFrame.mousePressEvent(row_frame, event)

            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(btn)
            row_frame.mousePressEvent = _toggle
            lbl.mousePressEvent = _toggle
            _apply(btn.isChecked())
            scizo_card.content_layout.addWidget(row_frame)
            return btn

        _sz_toggle_row("1. Random Look",    "random_look_on")
        _sz_toggle_row("2. THANK YOU (C spam)", "thankyou_on")

        # ── Thank You interval slider ──
        ty_row = QHBoxLayout()
        ty_lbl = QLabel("Thank You Interval")
        ty_lbl.setObjectName("RowLabel")
        # snap stored value to nearest 10 for display
        def _snap10(v): return max(10, min(500, round(v / 10) * 10))
        ty_val_lbl = QLabel(f"{_snap10(cfg.scizo.thankyou_interval)} ms")
        ty_val_lbl.setStyleSheet(f"color:{t['accent']}; font-weight:700; font-size:12px; min-width:48px;")
        ty_val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        ty_slider = QSlider(Qt.Orientation.Horizontal)
        ty_slider.setRange(1, 50)   # 1=10ms, 50=500ms  (each tick = 10ms)
        ty_slider.setValue(_snap10(cfg.scizo.thankyou_interval) // 10)
        ty_slider.setStyleSheet(slider_style_sz)
        def _on_ty_change(v):
            ms = v * 10   # snap to nearest 10
            cfg.scizo.thankyou_interval = ms
            ty_val_lbl.setText(f"{ms} ms")
            cfg.save()
        ty_slider.valueChanged.connect(_on_ty_change)
        ty_row.addWidget(ty_lbl)
        ty_row.addSpacing(8)
        ty_row.addWidget(ty_val_lbl)
        ty_row.addSpacing(8)
        ty_row.addWidget(ty_slider)
        scizo_card.content_layout.addLayout(ty_row)

        # Scizo card has no master ON/OFF toggle in header — the keybind IS the toggle.
        # Hide the card's built-in toggle button so it doesn't confuse things.
        scizo_card.toggle.setVisible(False)

        layout.addWidget(scizo_card)

        # ── Auto Shoot card ──
        fc_section_lbl = QLabel("AUTO SHOOT")
        fc_section_lbl.setObjectName("SidebarSection")
        fc_section_lbl.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(fc_section_lbl)

        fc_card = Card("Auto Shoot", "make everything automatic", badge="AS")
        fc_card.toggle.setChecked(cfg.fast_clicker.enabled)
        fc_card.make_click_toggle()
        fc_card.update_appearance(cfg.fast_clicker.enabled)
        fc_card.toggle.toggled_state.connect(lambda s: (setattr(cfg.fast_clicker, 'enabled', bool(s)), cfg.save()))

        # Delay Slider (10-100ms)
        def _on_fc_delay(v):
            cfg.fast_clicker.delay_ms = v
            cfg.save()
        fc_card.add_slider("Delay (ms)", 10, 100, cfg.fast_clicker.delay_ms, _on_fc_delay)

        # Offset Slider (0-50ms)
        def _on_fc_offset(v):
            cfg.fast_clicker.offset_ms = v
            cfg.save()
        fc_card.add_slider("Random Offset (ms)", 0, 50, cfg.fast_clicker.offset_ms, _on_fc_offset)

        layout.addWidget(fc_card)

        # ── Guns search and grid ──
        guns_lbl = QLabel("ITEM PROFILES")
        guns_lbl.setObjectName("SidebarSection")
        guns_lbl.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(guns_lbl)

        # ── Search Bar ──
        self.gun_search_bar = QLineEdit()
        self.gun_search_bar.setPlaceholderText("Search profiles...")
        self.gun_search_bar.textChanged.connect(lambda: self._refresh_gun_grid())
        layout.addWidget(self.gun_search_bar)

        # ── Container that will be rebuilt when guns are added ──
        self._guns_container = QWidget()
        self._guns_layout = QVBoxLayout(self._guns_container)
        self._guns_layout.setContentsMargins(0, 0, 0, 0)
        self._guns_layout.setSpacing(12)
        layout.addWidget(self._guns_container)

        self._home_page_layout = layout   # keep reference for refresh
        self._refresh_gun_grid()

        layout.addStretch()
        return scroll

    # ------------------------------------------------------------------
    def _refresh_gun_grid(self):
        """Rebuild the gun grid (called on startup and after guns are added/removed)."""
        t = get_theme()

        # Get search filter
        filter_text = ""
        if hasattr(self, 'gun_search_bar'):
            filter_text = self.gun_search_bar.text().lower().strip()

        # Clear existing grid widgets
        while self._guns_layout.count():
            item = self._guns_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    c = item.layout().takeAt(0)
                    if c.widget():
                        c.widget().deleteLater()

        BUILT_IN_GUNS = [
            ("RC-4",         "R4", cfg.rc4,       None),
            ("SMG12",        "S1", cfg.smg12,      None),
            ("F2",           "F2", cfg.f2,         None),
            ("Vector .45",   "VC", cfg.vector,     None),
            ("UZK50GI",      "UZ", cfg.uzk50gi,    None),
            ("C70",          "C7", cfg.c70,        None),
        ]

        all_guns = list(BUILT_IN_GUNS)
        for idx, gun in enumerate(gun_registry.guns):
            all_guns.append((gun.name, gun.badge, gun, idx))

        # Filter guns
        if filter_text:
            all_guns = [g for g in all_guns if filter_text in g[0].lower() or filter_text in g[1].lower()]

        # Sort favorites to top
        all_guns.sort(key=lambda g: g[0] in cfg.favorites, reverse=True)

        cols = 3
        grid = QGridLayout()
        grid.setSpacing(12)
        
        # Ensure cards have a fixed width to prevent stretching when only one is shown
        CARD_WIDTH = 300 # Approximate width based on previous layout

        for i, (name, badge, settings, reg_idx) in enumerate(all_guns):
            card = self._build_mini_gun_card(name, badge, settings, registry_index=reg_idx)
            card.setFixedWidth(CARD_WIDTH)
            grid.addWidget(card, i // cols, i % cols)

        # ── "+ Add Gun" button in the next grid cell ──
        if not all_guns:
            empty = QLabel("No matching profiles")
            empty.setObjectName("CardDesc")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setMinimumHeight(92)
            grid.addWidget(empty, 0, 0, 1, cols)

        add_btn_cell = self._build_add_gun_cell(t)
        add_btn_cell.setFixedWidth(CARD_WIDTH)
        next_i = len(all_guns)
        grid.addWidget(add_btn_cell, next_i // cols, next_i % cols)
        
        # Add a stretch to the last column and row to keep cards to the left/top
        grid.setColumnStretch(cols, 1)
        grid.setRowStretch((next_i // cols) + 1, 1)

        grid_container = QWidget()
        # Use QHBoxLayout for grid_container to prevent vertical stretching if possible, 
        # or just stick with QVBoxLayout and addStretch.
        QVBoxLayout(grid_container).addLayout(grid)
        grid_container.layout().setContentsMargins(0, 0, 0, 0)
        grid_container.layout().addStretch()
        self._guns_layout.addWidget(grid_container)

    def _remove_custom_gun(self, registry_index: int):
        """Stop the macro thread for a custom gun, remove it from the registry, and refresh the grid."""
        if registry_index < 0 or registry_index >= len(self._custom_gun_threads):
            return

        # Stop the thread
        th = self._custom_gun_threads[registry_index]
        th.running = False
        th.quit()
        th.wait(500)

        # Remove from both thread lists
        self._custom_gun_threads.pop(registry_index)
        if th in self.threads:
            self.threads.remove(th)

        # Remove from registry (also saves custom_guns.json)
        gun_registry.remove(registry_index)

        # Refresh grid
        self._refresh_gun_grid()

    def _build_add_gun_cell(self, t):
        """A dashed-border 'add' card that opens the AddGunDialog."""
        frame = QFrame()
        frame.setObjectName("Card")
        frame.setStyleSheet(f"""
            QFrame#Card {{
                background-color: transparent;
                border: 2px dashed {t['border']};
                border-radius: 12px;
            }}
            QFrame#Card:hover {{
                border-color: {t['accent']};
            }}
        """)
        frame.setMinimumHeight(80)
        frame.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QVBoxLayout(frame)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(4)

        plus_lbl = QLabel("+")
        plus_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plus_lbl.setStyleSheet(f"font-size:24px; font-weight:300; color:{t['border']}; background:transparent;")

        txt_lbl = QLabel("Add Profile")
        txt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        txt_lbl.setStyleSheet(f"font-size:11px; font-weight:700; color:{t['subtext']}; letter-spacing:1px; background:transparent;")

        lay.addWidget(plus_lbl)
        lay.addWidget(txt_lbl)

        def _open_dialog(_event=None):
            dlg = AddGunDialog(self)
            dlg.gun_added.connect(self._on_gun_added)
            dlg.exec()

        frame.mousePressEvent = _open_dialog
        return frame

    def _on_gun_added(self):
        """Called when AddGunDialog reports a gun was added/imported — starts its macro thread and refreshes UI."""
        # Start new macro threads for any guns that don't have one yet
        existing_count = len(self._custom_gun_threads)
        for i, gun in enumerate(gun_registry.guns):
            if i >= existing_count:
                th = CustomGunMacro(gun)
                self._custom_gun_threads.append(th)
                self.threads.append(th)
                th.start()
        self._refresh_gun_grid()

    def create_home_page_dummy(self):
        pass  # placeholder so the method split is clean

    def create_settings_page(self):
        t = get_theme()
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        layout.addWidget(self._page_header("Settings", "Client window and overlay controls"))

        client_card = Card("Client Overlay Window", "Shrink the actual app into a compact always-on-top window and hide/show it with a key.", badge="CW")
        client_card.toggle.setChecked(cfg.client_overlay.enabled)
        client_card.make_click_toggle()
        client_card.update_appearance(cfg.client_overlay.enabled)

        def _on_client_overlay_enabled(s):
            cfg.client_overlay.enabled = bool(s)
            cfg.save()
            if s:
                self._show_client_overlay_window()
            else:
                self._leave_client_overlay_mode()

        client_card.toggle.toggled_state.connect(_on_client_overlay_enabled)

        key_row = QHBoxLayout()
        key_lbl = QLabel("Toggle Window Key")
        key_lbl.setObjectName("RowLabel")
        key_btn = KeybindButton(cfg.client_overlay.toggle_key or "none")
        def _on_key(k):
            cfg.client_overlay.toggle_key = "" if str(k).lower() == "none" else str(k).lower()
            key_btn.setText(_format_keybind(cfg.client_overlay.toggle_key))
            cfg.save()
        key_btn.key_changed.connect(_on_key)
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("NeutralBtn")
        clear_btn.clicked.connect(lambda: _on_key(""))
        key_row.addWidget(key_lbl)
        key_row.addStretch()
        key_row.addWidget(key_btn)
        key_row.addWidget(clear_btn)
        client_card.content_layout.addLayout(key_row)

        def _client_toggle_row(label, attr):
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setObjectName("RowLabel")
            toggle = ToggleButton(checked=getattr(cfg.client_overlay, attr))
            def _on(s, a=attr):
                setattr(cfg.client_overlay, a, bool(s))
                cfg.save()
                if cfg.client_overlay.enabled and self.isVisible():
                    self._show_client_overlay_window()
            toggle.toggled_state.connect(_on)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(toggle)
            client_card.content_layout.addLayout(row)

        _client_toggle_row("Keep On Top", "keep_on_top")

        client_card.add_slider("Compact Width", 1225, 1500, cfg.client_overlay.compact_width, lambda v: (
            setattr(cfg.client_overlay, "compact_width", v),
            cfg.save(),
            self._show_client_overlay_window() if cfg.client_overlay.enabled and self.isVisible() else None
        ))
        client_card.add_slider("Compact Height", 460, 940, cfg.client_overlay.compact_height, lambda v: (
            setattr(cfg.client_overlay, "compact_height", v),
            cfg.save(),
            self._show_client_overlay_window() if cfg.client_overlay.enabled and self.isVisible() else None
        ))

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        show_btn = QPushButton("Show Compact Window")
        show_btn.setObjectName("SaveBtn")
        show_btn.clicked.connect(lambda: (
            setattr(cfg.client_overlay, "enabled", True),
            client_card.toggle.setChecked(True),
            client_card.toggle.update_style(),
            client_card.update_appearance(True),
            cfg.save(),
            self._show_client_overlay_window()
        ))
        hide_btn = QPushButton("Hide Until Key")
        hide_btn.setObjectName("NeutralBtn")
        hide_btn.clicked.connect(lambda: (
            setattr(cfg.client_overlay, "enabled", True),
            client_card.toggle.setChecked(True),
            client_card.toggle.update_style(),
            client_card.update_appearance(True),
            cfg.save(),
            self._hide_client_overlay_window()
        ))
        normal_btn = QPushButton("Return Normal")
        normal_btn.setObjectName("NeutralBtn")
        normal_btn.clicked.connect(lambda: (
            setattr(cfg.client_overlay, "enabled", False),
            client_card.toggle.setChecked(False),
            client_card.toggle.update_style(),
            client_card.update_appearance(False),
            cfg.save(),
            self._leave_client_overlay_mode()
        ))
        btn_row.addWidget(show_btn)
        btn_row.addWidget(hide_btn)
        btn_row.addWidget(normal_btn)
        client_card.content_layout.addLayout(btn_row)
        layout.addWidget(client_card)

        hotkey_card = Card("Hotkeys", "Window controls and profile shortcuts.", badge="HK")
        hotkey_card.toggle.hide()
        hotkey_card.add_row("Window Toggle", QLabel(_format_keybind(cfg.client_overlay.toggle_key)))
        hotkey_card.add_row("Overlay Status", QLabel("Managed on the Overlay page"))
        layout.addWidget(hotkey_card)

        startup_card = Card("Startup", "Client launch preferences.", badge="ST")
        startup_card.toggle.hide()
        start_hidden = ToggleButton(checked=cfg.client_overlay.start_hidden)
        start_hidden.toggled_state.connect(lambda s: (
            setattr(cfg.client_overlay, "start_hidden", bool(s)),
            cfg.save()
        ))
        startup_card.add_row("Start Hidden", start_hidden)
        layout.addWidget(startup_card)

        data_card = Card("Data", "Settings backup and layout maintenance.", badge="DT")
        data_card.toggle.hide()
        data_btns = QHBoxLayout()
        data_btns.addStretch()
        export_btn = QPushButton("Export Settings")
        export_btn.setObjectName("NeutralBtn")
        import_btn = QPushButton("Import Settings")
        import_btn.setObjectName("NeutralBtn")
        reset_layout_btn = QPushButton("Reset UI Layout")
        reset_layout_btn.setObjectName("NeutralBtn")
        export_btn.clicked.connect(lambda: QMessageBox.information(self, "Export Settings", "Export UI is ready to connect to the existing settings file."))
        import_btn.clicked.connect(lambda: QMessageBox.information(self, "Import Settings", "Import UI is ready to connect to the existing settings file."))
        reset_layout_btn.clicked.connect(lambda: QMessageBox.information(self, "Reset UI Layout", "Layout reset is ready to connect to existing layout state."))
        for btn in (export_btn, import_btn, reset_layout_btn):
            data_btns.addWidget(btn)
        data_card.content_layout.addLayout(data_btns)
        layout.addWidget(data_card)

        danger_card = Card("Danger Zone", "Reset client settings only when you are sure.", badge="!")
        danger_card.toggle.hide()
        danger_row = QHBoxLayout()
        danger_row.addStretch()
        reset_all_btn = QPushButton("Reset All Settings")
        reset_all_btn.setObjectName("DangerBtn")
        reset_all_btn.clicked.connect(lambda: QMessageBox.warning(self, "Reset All Settings", "Reset action is intentionally left as a UI stub."))
        danger_row.addWidget(reset_all_btn)
        danger_card.content_layout.addLayout(danger_row)
        layout.addWidget(danger_card)

        layout.addStretch()
        return scroll

    def create_overlay_page(self):
        t = get_theme()
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        layout.addWidget(self._page_header("Overlay", "Transparent in-game style status HUD"))

        main_card = Card("Game Overlay", "Top-left shows active features. Top-right shows primary/secondary icon.", badge="OV")
        main_card.toggle.setChecked(cfg.overlay.enabled)
        main_card.make_click_toggle()
        main_card.update_appearance(cfg.overlay.enabled)

        def _overlay_enabled(s):
            cfg.overlay.enabled = bool(s)
            cfg.save()
            self.overlay_window.apply_settings()
            if hasattr(self, "_overlay_chip"):
                self._overlay_chip.setText(f"Overlay: {'On' if cfg.overlay.enabled else 'Off'}")

        main_card.toggle.toggled_state.connect(_overlay_enabled)

        def _overlay_toggle_row(label, attr):
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setObjectName("RowLabel")
            toggle = ToggleButton(checked=getattr(cfg.overlay, attr))
            def _on(s, a=attr):
                setattr(cfg.overlay, a, bool(s))
                cfg.save()
                self.overlay_window.apply_settings()
                self.overlay_window.refresh()
            toggle.toggled_state.connect(_on)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(toggle)
            main_card.content_layout.addLayout(row)
            return toggle

        _overlay_toggle_row("Click Through", "click_through")
        _overlay_toggle_row("Compact Mode", "compact_mode")
        _overlay_toggle_row("Slot Label", "show_slot_label")
        _overlay_toggle_row("Show Gun Keybinds", "show_keybinds")
        _overlay_toggle_row("Soft Glow", "glow")
        _overlay_toggle_row("Pulse Icon", "pulse_icon")
        _overlay_toggle_row("Rainbow Accent", "rainbow_accent")

        main_card.add_slider("Opacity", 15, 100, cfg.overlay.opacity, lambda v: (
            setattr(cfg.overlay, "opacity", v),
            cfg.save(),
            self.overlay_window.apply_settings()
        ))
        main_card.add_slider("Scale", 70, 150, cfg.overlay.scale, lambda v: (
            setattr(cfg.overlay, "scale", v),
            cfg.save(),
            self.overlay_window.apply_settings()
        ))
        main_card.add_slider("Screen Margin", 4, 120, cfg.overlay.margin, lambda v: (
            setattr(cfg.overlay, "margin", v),
            cfg.save(),
            self.overlay_window.apply_settings()
        ))
        layout.addWidget(main_card)

        icon_card = Card("Gun Icons", "Upload transparent PNG/SVG/WebP images. Defaults are clean no-background gun silhouettes.", badge="IC")
        icon_card.toggle.hide()

        def _icon_preview(path, fallback):
            lbl = QLabel()
            lbl.setFixedSize(118, 58)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"border:1px solid {t['border']}; border-radius:8px; background:rgba(255,255,255,0.035);")
            pix = QPixmap(path if path and os.path.exists(path) else fallback)
            if not pix.isNull():
                lbl.setPixmap(pix.scaled(lbl.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            return lbl

        def _add_icon_picker(title, attr, fallback):
            row = QHBoxLayout()
            lbl = QLabel(title)
            lbl.setObjectName("RowLabel")
            preview = _icon_preview(getattr(cfg.overlay, attr), fallback)
            pick_btn = QPushButton("Upload")
            pick_btn.setObjectName("NeutralBtn")
            reset_btn = QPushButton("Use Default")
            reset_btn.setObjectName("NeutralBtn")

            def _refresh_preview():
                pix = QPixmap(getattr(cfg.overlay, attr) if getattr(cfg.overlay, attr) and os.path.exists(getattr(cfg.overlay, attr)) else fallback)
                if not pix.isNull():
                    preview.setPixmap(pix.scaled(preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.overlay_window.refresh()

            def _pick():
                path, _ = QFileDialog.getOpenFileName(
                    self,
                    f"Choose {title} Icon",
                    "",
                    "Images (*.png *.svg *.webp *.jpg *.jpeg *.bmp)"
                )
                if path:
                    setattr(cfg.overlay, attr, path)
                    cfg.save()
                    _refresh_preview()

            def _reset():
                setattr(cfg.overlay, attr, "")
                cfg.save()
                _refresh_preview()

            pick_btn.clicked.connect(_pick)
            reset_btn.clicked.connect(_reset)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(preview)
            row.addSpacing(8)
            row.addWidget(pick_btn)
            row.addWidget(reset_btn)
            icon_card.content_layout.addLayout(row)

        _add_icon_picker("Primary", "primary_icon_path", DEFAULT_PRIMARY_ICON)
        _add_icon_picker("Secondary", "secondary_icon_path", DEFAULT_SECONDARY_ICON)
        layout.addWidget(icon_card)

        preview_card = Card("Live Preview", "Turn the overlay on and press 1 or 2 to swap the top-right gun icon.", badge="PV")
        preview_card.toggle.hide()
        preview_panel = QFrame()
        preview_panel.setObjectName("Card")
        preview_panel.setMinimumHeight(150)
        preview_panel.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {_rgba(t['bg'], 0.78)};
                border: 1px solid {_rgba(t['accent'], 0.32)};
                border-radius: 14px;
            }}
        """)
        preview_lay = QVBoxLayout(preview_panel)
        preview_lay.setContentsMargins(18, 16, 18, 16)
        hud_top = QHBoxLayout()
        hud_title = QLabel("OBSIDIAN HUD")
        hud_title.setStyleSheet(f"color:{t['accent']}; font-size:11px; font-weight:900; letter-spacing:2px;")
        hud_slot = QLabel("Slot 1")
        hud_slot.setObjectName("BadgeLabel")
        hud_top.addWidget(hud_title)
        hud_top.addStretch()
        hud_top.addWidget(hud_slot)
        preview_lay.addLayout(hud_top)
        for row_text in ("SMG12  F1  82", "Turn Control  MOUSE5", "Overlay Glow  ON"):
            row_lbl = QLabel(row_text)
            row_lbl.setStyleSheet(f"color:{t['text']}; font-size:12px; font-weight:700; padding:3px 0;")
            preview_lay.addWidget(row_lbl)
        preview_card.content_layout.addWidget(preview_panel)
        status_lbl = QLabel("Primary = slot 1, secondary = slot 2. Borderless/windowed fullscreen works best.")
        status_lbl.setObjectName("CardDesc")
        preview_card.content_layout.addWidget(status_lbl)
        show_btn = QPushButton("Show Overlay Now")
        show_btn.setObjectName("SaveBtn")
        show_btn.clicked.connect(lambda: (
            setattr(cfg.overlay, "enabled", True),
            main_card.toggle.setChecked(True),
            main_card.toggle.update_style(),
            main_card.update_appearance(True),
            cfg.save(),
            self.overlay_window.apply_settings(),
            self._overlay_chip.setText("Overlay: On") if hasattr(self, "_overlay_chip") else None
        ))
        hide_btn = QPushButton("Hide Overlay")
        hide_btn.setObjectName("NeutralBtn")
        hide_btn.clicked.connect(lambda: (
            setattr(cfg.overlay, "enabled", False),
            main_card.toggle.setChecked(False),
            main_card.toggle.update_style(),
            main_card.update_appearance(False),
            cfg.save(),
            self.overlay_window.apply_settings(),
            self._overlay_chip.setText("Overlay: Off") if hasattr(self, "_overlay_chip") else None
        ))
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(show_btn)
        btn_row.addWidget(hide_btn)
        preview_card.content_layout.addLayout(btn_row)
        layout.addWidget(preview_card)

        layout.addStretch()
        return scroll

    def create_theme_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        self._theme_page_inner   = page
        self._theme_page_scroll  = scroll

        self._rebuild_theme_page()
        return scroll

    def _rebuild_theme_page(self):
        """Reconstruct the theme grid (called on load and after custom theme changes)."""
        page = self._theme_page_inner
        # Wipe old content
        old_lay = page.layout()
        if old_lay:
            while old_lay.count():
                item = old_lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            import sip
            try:
                sip.delete(old_lay)
            except Exception:
                pass

        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        t = get_theme()
        layout.addWidget(self._page_header("Theme", "Choose or create your colour palette"))

        self._theme_dots  = {}
        self._theme_cards = {}

        def _apply(name):
            self._change_theme(name)
            for n, frm in self._theme_cards.items():
                active = (n == name)
                frm.setProperty("active", "true" if active else "false")
                frm.style().unpolish(frm)
                frm.style().polish(frm)

        PALETTE_KEYS = [
            ("accent",     "Accent"),
            ("accent_dim", "Dim"),
            ("bg",         "BG"),
            ("sidebar",    "Sidebar"),
            ("card",       "Card"),
            ("border",     "Border"),
            ("text",       "Text"),
            ("subtext",    "Subtext"),
        ]

        grid = QGridLayout()
        grid.setSpacing(14)
        cols = 2

        all_theme_items = list(THEMES.items())
        for i, (name, theme_data) in enumerate(all_theme_items):
            is_active   = (name == _current_theme_name)
            is_custom   = name in custom_theme_registry.themes

            frame = QFrame()
            frame.setObjectName("Card")
            frame.setProperty("active", "true" if is_active else "false")
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(14, 12, 14, 12)
            frame_layout.setSpacing(8)
            self._theme_cards[name] = frame

            # ── Header ──
            hdr = QHBoxLayout()
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(f"font-size:13px; font-weight:800; color:{theme_data['text']};")
            hdr.addWidget(name_lbl)

            if is_custom:
                custom_badge = QLabel("CUSTOM")
                custom_badge.setStyleSheet(
                    f"font-size:8px; font-weight:800; color:{theme_data['accent']};"
                    f"background:rgba(255,255,255,0.06); border-radius:4px; padding:1px 5px; margin-left:4px;"
                )
                hdr.addWidget(custom_badge)

            hdr.addStretch()

            select_btn = QPushButton("\u2713 Active" if is_active else "Select")
            select_btn.setFixedHeight(26)
            select_btn.setStyleSheet(
                f"QPushButton {{ background-color:{theme_data['accent']}; color:#000; font-weight:700; "
                f"border-radius:6px; padding:2px 10px; border:none; font-size:11px; }}"
                if is_active else
                f"QPushButton {{ background-color:rgba(255,255,255,0.06); color:{theme_data['text']}; font-weight:600; "
                f"border-radius:6px; padding:2px 10px; border:1px solid {theme_data['border']}; font-size:11px; }}"
            )
            self._theme_dots[name] = select_btn

            def _make_handler(n, btn):
                def _handler():
                    _apply(n)
                    for nn, b in self._theme_dots.items():
                        td = THEMES.get(nn, {})
                        if not td:
                            continue
                        is_now = (nn == n)
                        b.setText("\u2713 Active" if is_now else "Select")
                        b.setStyleSheet(
                            f"QPushButton {{ background-color:{td['accent']}; color:#000; font-weight:700; "
                            f"border-radius:6px; padding:2px 10px; border:none; font-size:11px; }}"
                            if is_now else
                            f"QPushButton {{ background-color:rgba(255,255,255,0.06); color:{td['text']}; font-weight:600; "
                            f"border-radius:6px; padding:2px 10px; border:1px solid {td['border']}; font-size:11px; }}"
                        )
                return _handler

            select_btn.clicked.connect(_make_handler(name, select_btn))
            hdr.addWidget(select_btn)

            # Remove button for custom themes only
            if is_custom:
                rm_btn = QPushButton("\u2715")
                rm_btn.setFixedSize(26, 26)
                rm_btn.setStyleSheet(
                    "QPushButton { background-color:rgba(220,50,50,0.12); color:#c05050; "
                    "font-size:11px; font-weight:700; border:1px solid rgba(220,50,50,0.25); "
                    "border-radius:5px; }"
                    "QPushButton:hover { background-color:rgba(220,50,50,0.28); color:#e06060; }"
                )
                def _make_remove(n):
                    def _do_remove():
                        global _current_theme_name
                        reply = QMessageBox.question(
                            page, "Remove Theme",
                            f'Remove custom theme "{n}" permanently?',
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                            QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.Yes:
                            if _current_theme_name == n:
                                self._change_theme("Cyan")
                            custom_theme_registry.remove(n)
                            self._rebuild_theme_page()
                    return _do_remove
                rm_btn.clicked.connect(_make_remove(name))
                hdr.addSpacing(4)
                hdr.addWidget(rm_btn)

            frame_layout.addLayout(hdr)

            # ── Swatches ──
            swatches_row = QHBoxLayout()
            swatches_row.setSpacing(4)
            for key, label in PALETTE_KEYS:
                color = theme_data[key]
                swatch_w = QWidget()
                swatch_l = QVBoxLayout(swatch_w)
                swatch_l.setContentsMargins(0, 0, 0, 0)
                swatch_l.setSpacing(2)
                swatch_l.setAlignment(Qt.AlignmentFlag.AlignHCenter)

                swatch = QFrame()
                swatch.setFixedSize(22, 22)
                swatch.setStyleSheet(
                    f"background-color:{color}; border-radius:4px; "
                    f"border:1px solid {theme_data['border']};"
                )
                swatch_lbl = QLabel(label)
                swatch_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                swatch_lbl.setStyleSheet(
                    f"font-size:8px; color:{theme_data['subtext']}; font-weight:600;"
                )
                swatch_l.addWidget(swatch)
                swatch_l.addWidget(swatch_lbl)
                swatches_row.addWidget(swatch_w)

            swatches_row.addStretch()
            frame_layout.addLayout(swatches_row)

            grid.addWidget(frame, i // cols, i % cols)

        # ── "Create Theme" dashed cell ──
        next_i = len(all_theme_items)
        create_cell = self._build_create_theme_cell(t)
        grid.addWidget(create_cell, next_i // cols, next_i % cols)

        layout.addLayout(grid)
        layout.addStretch()

    def _build_create_theme_cell(self, t):
        frame = QFrame()
        frame.setObjectName("Card")
        frame.setStyleSheet(f"""
            QFrame#Card {{
                background-color: transparent;
                border: 2px dashed {t['border']};
                border-radius: 12px;
            }}
            QFrame#Card:hover {{ border-color: {t['accent']}; }}
        """)
        frame.setMinimumHeight(80)
        frame.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QVBoxLayout(frame)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(4)

        plus_lbl = QLabel("+")
        plus_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plus_lbl.setStyleSheet(f"font-size:24px; font-weight:300; color:{t['border']}; background:transparent;")

        txt_lbl = QLabel("Create Theme")
        txt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        txt_lbl.setStyleSheet(f"font-size:11px; font-weight:700; color:{t['subtext']}; letter-spacing:1px; background:transparent;")

        lay.addWidget(plus_lbl)
        lay.addWidget(txt_lbl)

        def _open(_event=None):
            dlg = ThemeCreatorDialog(self, self)
            dlg.theme_added.connect(self._rebuild_theme_page)
            dlg.exec()

        frame.mousePressEvent = _open
        return frame
    # =========================================================================
    # CUSTOM PAGE BUILDER
    # =========================================================================

    def _load_custom_pages(self):
        """Build widgets for all saved custom pages and add to stack + sidebar."""
        for i, page_data in enumerate(custom_page_registry.pages):
            widget = self.create_custom_page(i)
            self._custom_page_widgets.append(widget)
            self.content_stack.addWidget(widget)
        self._rebuild_custom_pages_sidebar()

    def _rebuild_custom_pages_sidebar(self):
        """Recreate sidebar buttons for custom pages."""
        # Clear existing buttons
        for btn in self._custom_page_buttons:
            self._pages_btn_layout.removeWidget(btn)
            btn.deleteLater()
        self._custom_page_buttons.clear()

        t = get_theme()
        has_pages = bool(custom_page_registry.pages)
        if hasattr(self, "_my_pages_lbl"):
            self._my_pages_lbl.setVisible(has_pages)
        if hasattr(self, "_pages_btn_container"):
            self._pages_btn_container.setVisible(has_pages)
        for i, page_data in enumerate(custom_page_registry.pages):
            stack_index = i + 4  # 0=home, 1=theme, 2=overlay, 3=settings, 4+=custom
            name = page_data.get("name", f"Page {i+1}")
            btn = QPushButton(f"  {name}")
            btn.setObjectName("SidebarButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=stack_index: self.switch_page(idx))

            # Right-click to edit/delete
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, pi=i: self._page_context_menu(pi)
            )
            self._pages_btn_layout.addWidget(btn)
            self._custom_page_buttons.append(btn)

    def _create_new_page(self):
        dlg = NewPageDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, badge = dlg.get_result()
            custom_page_registry.add_page(name, badge)
            i = len(custom_page_registry.pages) - 1
            widget = self.create_custom_page(i)
            self._custom_page_widgets.append(widget)
            self.content_stack.addWidget(widget)
            self._rebuild_custom_pages_sidebar()
            # Switch to new page
            self.switch_page(i + 4)

    def _page_context_menu(self, page_index: int):
        """Show Edit/Delete options for a custom page."""
        t = get_theme()
        menu = QDialog(self)
        menu.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        menu.setFixedWidth(160)
        menu.setStyleSheet(f"""
            QDialog {{ background:{t['card']}; border:1px solid {t['border']}; border-radius:8px; }}
            QPushButton {{ background:transparent; color:{t['text']}; border:none; text-align:left;
                           padding:9px 16px; font-size:12px; font-weight:600; }}
            QPushButton:hover {{ background:rgba(255,255,255,0.06); color:{t['accent']}; }}
        """)
        lay = QVBoxLayout(menu)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)

        def _edit():
            menu.accept()
            self._open_page_editor(page_index)

        def _delete():
            menu.accept()
            self._delete_custom_page(page_index)

        btn_edit = QPushButton("✏  Edit Buttons")
        btn_edit.clicked.connect(_edit)
        btn_del = QPushButton("🗑  Delete Page")
        btn_del.setStyleSheet(f"color:#e05555; background:transparent; border:none; text-align:left; padding:9px 16px; font-size:12px; font-weight:600;")
        btn_del.clicked.connect(_delete)
        lay.addWidget(btn_edit)
        lay.addWidget(btn_del)

        from PyQt6.QtGui import QCursor
        menu.move(QCursor.pos())
        menu.exec()

    def _open_page_editor(self, page_index: int):
        dlg = PageEditorDialog(self, page_index)
        def _rebuild():
            # Rebuild just this page's widget
            stack_index = page_index + 4
            old_widget = self._custom_page_widgets[page_index]
            self.content_stack.removeWidget(old_widget)
            old_widget.deleteLater()
            new_widget = self.create_custom_page(page_index)
            self._custom_page_widgets[page_index] = new_widget
            self.content_stack.insertWidget(stack_index, new_widget)
            self.switch_page(stack_index)
        dlg.page_changed.connect(_rebuild)
        dlg.exec()
        _rebuild()

    def _delete_custom_page(self, page_index: int):
        stack_index = page_index + 4
        # Remove from stack
        widget = self._custom_page_widgets.pop(page_index)
        self.content_stack.removeWidget(widget)
        widget.deleteLater()
        # Remove from registry
        custom_page_registry.remove_page(page_index)
        # Rebuild sidebar
        self._rebuild_custom_pages_sidebar()
        self.switch_page(0)

    def create_custom_page(self, page_index: int) -> QWidget:
        """Build the scroll page widget for a custom page."""
        t = get_theme()
        page_data = custom_page_registry.pages[page_index]

        container = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # Header row with Edit button
        hdr_row = QHBoxLayout()
        hdr_w = self._page_header(page_data.get("name", "My Page"),
                                  "Right-click the sidebar entry to edit or delete this page.")
        hdr_row.addWidget(hdr_w)
        hdr_row.addStretch()
        btn_edit_page = QPushButton("✏  Edit Buttons")
        btn_edit_page.setObjectName("NeutralBtn")
        btn_edit_page.clicked.connect(lambda: self._open_page_editor(page_index))
        hdr_row.addWidget(btn_edit_page)
        layout.addLayout(hdr_row)
        buttons = page_data.get("buttons", [])
        if not buttons:
            empty_lbl = QLabel("No buttons yet — click \"Edit Buttons\" to add some.")
            empty_lbl.setStyleSheet(f"color:{t['subtext']}; font-size:13px;")
            layout.addWidget(empty_lbl)
        else:
            grid = QGridLayout()
            grid.setSpacing(16)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 1)
            for idx, btn_data in enumerate(buttons):
                card = self._render_custom_btn(btn_data, page_index, idx)
                grid.addWidget(card, idx // 2, idx % 2)
            layout.addLayout(grid)

        layout.addStretch()
        return scroll

    def _render_custom_btn(self, btn_data: dict, page_index: int, btn_index: int) -> QFrame:
        """Render a single button as a Card on a custom page."""
        t = get_theme()
        btype = btn_data.get("type", BTYPE_CODE)
        label = btn_data.get("label", "Button")
        enabled = btn_data.get("enabled", True)

        type_badges = {BTYPE_KEYBIND: "⌨", BTYPE_GUN: btn_data.get("gun_badge", "GN"), BTYPE_CODE: "</>"}
        badge = type_badges.get(btype, "?")

        card = Card(label, {BTYPE_KEYBIND: "Key macro", BTYPE_GUN: "Gun recoil control", BTYPE_CODE: "Custom script"}.get(btype, ""), badge=badge)
        card.toggle.setChecked(enabled)
        card.make_click_toggle()
        card.update_appearance(enabled)

        def _on_toggle(s, _bd=btn_data, _pi=page_index, _bi=btn_index):
            _bd["enabled"] = bool(s)
            custom_page_registry.pages[_pi]["buttons"][_bi]["enabled"] = bool(s)
            custom_page_registry.save()

        card.toggle.toggled_state.connect(_on_toggle)

        if btype == BTYPE_KEYBIND:
            self._render_keybind_card(card, btn_data, page_index, btn_index)
        elif btype == BTYPE_GUN:
            self._render_gun_card(card, btn_data, page_index, btn_index)
        elif btype == BTYPE_CODE:
            self._render_code_card(card, btn_data, page_index, btn_index)

        return card

    def _render_keybind_card(self, card: Card, btn_data: dict, page_index: int, btn_index: int):
        t = get_theme()
        key = btn_data.get("key", "f")
        action_keys = [k.strip() for k in btn_data.get("action_keys", "").split(",") if k.strip()]
        delay_min = btn_data.get("delay_min", 50)
        delay_max = btn_data.get("delay_max", 100)
        hold_repeat = btn_data.get("hold_repeat", False)

        # Info rows
        key_row = QHBoxLayout()
        key_lbl = QLabel("Activate Key")
        key_lbl.setObjectName("RowLabel")
        key_btn = KeybindButton(key)
        def _on_key_change(k, _bd=btn_data, _pi=page_index, _bi=btn_index):
            _bd["key"] = k
            custom_page_registry.pages[_pi]["buttons"][_bi]["key"] = k
            custom_page_registry.save()
        key_btn.key_changed.connect(_on_key_change)
        key_row.addWidget(key_lbl)
        key_row.addStretch()
        key_row.addWidget(key_btn)
        card.content_layout.addLayout(key_row)

        action_lbl = QLabel(f"Keys: {', '.join(action_keys) if action_keys else '—'}")
        action_lbl.setStyleSheet(f"color:{t['accent']}; font-size:11px; font-weight:700;")
        card.content_layout.addWidget(action_lbl)

        delay_lbl = QLabel(f"Delay: {delay_min}–{delay_max} ms  |  Hold: {'ON' if hold_repeat else 'OFF'}")
        delay_lbl.setObjectName("CardDesc")
        card.content_layout.addWidget(delay_lbl)

        # Run button
        ic_ref = InputController()
        def _run(_checked=False, _keys=action_keys, _dmin=delay_min, _dmax=delay_max, _ic=ic_ref, _bd=btn_data):
            if not _bd.get("enabled", True):
                return
            def _task():
                for k in _keys:
                    _ic.press_key(k)
                    if len(_keys) > 1:
                        import random as _r
                        time.sleep(_r.uniform(_dmin, _dmax) / 1000.0)
            threading.Thread(target=_task, daemon=True).start()

        run_btn = QPushButton("▶  Run Now")
        run_btn.setObjectName("NeutralBtn")
        run_btn.clicked.connect(_run)
        card.content_layout.addWidget(run_btn)

    def _render_gun_card(self, card: Card, btn_data: dict, page_index: int, btn_index: int):
        t = get_theme()
        dy = btn_data.get("gun_dy", 8.0)
        dx = btn_data.get("gun_dx", 0.0)
        slot = btn_data.get("gun_slot", 1)

        # Strength slider
        strength_row = QHBoxLayout()
        strength_lbl = QLabel("Strength")
        strength_lbl.setObjectName("RowLabel")
        strength_val = btn_data.get("gun_strength", 100)
        val_lbl = QLabel(f"{strength_val}%")
        val_lbl.setStyleSheet(f"color:{t['accent']}; font-weight:700; font-size:12px; min-width:36px;")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(1, 100)
        slider.setValue(strength_val)
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height:3px; background:rgba(255,255,255,0.08); border-radius:2px; }}
            QSlider::handle:horizontal {{ background:{t['accent']}; width:13px; height:13px; margin:-5px 0; border-radius:7px; }}
            QSlider::sub-page:horizontal {{ background:{t['accent']}; border-radius:2px; }}
        """)
        def _on_strength(v, _bd=btn_data, _pi=page_index, _bi=btn_index):
            _bd["gun_strength"] = v
            custom_page_registry.pages[_pi]["buttons"][_bi]["gun_strength"] = v
            custom_page_registry.save()
            val_lbl.setText(f"{v}%")
        slider.valueChanged.connect(_on_strength)
        strength_row.addWidget(strength_lbl)
        strength_row.addStretch()
        strength_row.addWidget(val_lbl)
        strength_row.addSpacing(8)
        strength_row.addWidget(slider)
        card.content_layout.addLayout(strength_row)

        info = QLabel(f"dy={dy}  dx={dx}  |  Arm key: {slot}")
        info.setObjectName("CardDesc")
        card.content_layout.addWidget(info)

        # Register with gun_registry so it runs via the existing macro system
        ic_ref = InputController()
        def _apply_recoil(_checked=False, _bd=btn_data, _ic=ic_ref):
            if not _bd.get("enabled", True):
                return
            strength = _bd.get("gun_strength", 100) / 100.0
            _dy = _bd.get("gun_dy", 8.0) * strength * sens_scale('vertical')
            _dx = _bd.get("gun_dx", 0.0) * strength * sens_scale('horizontal')
            def _task():
                _ic.move_mouse_relative(int(round(_dx)), int(round(_dy)))
            threading.Thread(target=_task, daemon=True).start()

        pulse_btn = QPushButton("▶  Test Recoil Pulse")
        pulse_btn.setObjectName("NeutralBtn")
        pulse_btn.clicked.connect(_apply_recoil)
        card.content_layout.addWidget(pulse_btn)

    def _render_code_card(self, card: Card, btn_data: dict, page_index: int, btn_index: int):
        t = get_theme()
        code = btn_data.get("code", "")
        preview = code[:80].replace("\n", " ↵ ") + ("…" if len(code) > 80 else "")
        preview_lbl = QLabel(preview or "(no code)")
        preview_lbl.setStyleSheet(f"color:{t['subtext']}; font-size:11px; font-family:'Consolas','Courier New',monospace;")
        preview_lbl.setWordWrap(True)
        card.content_layout.addWidget(preview_lbl)

        status_lbl = QLabel("")
        status_lbl.setStyleSheet(f"font-size:11px; color:{t['accent']};")
        card.content_layout.addWidget(status_lbl)

        ic_ref = InputController()
        def _run_code(_checked=False, _bd=btn_data, _ic=ic_ref, _slbl=status_lbl):
            if not _bd.get("enabled", True):
                return
            _code = _bd.get("code", "")
            if not _code.strip():
                return
            _slbl.setText("Running…")
            def _task():
                try:
                    exec(_code, {"ic": _ic, "time": time, "random": random, "threading": threading, "cfg": cfg})
                    _slbl.setText("✓ Done")
                except Exception as e:
                    _slbl.setText(f"✗ Error: {e}")
            threading.Thread(target=_task, daemon=True).start()

        run_btn = QPushButton("â–¶  Run Script")
        run_btn.setObjectName("SaveBtn")
        run_btn.clicked.connect(_run_code)
        card.content_layout.addWidget(run_btn)

    def closeEvent(self, event):
        if hasattr(self, "overlay_window"):
            self.overlay_window.close()
        cfg.save()
        for t in self.threads:
            t.running = False
        for t in self.threads:
            t.quit()
            t.wait(1000)
        event.accept()


# =============================================================================
# ENTRY POINT
# =============================================================================

# ── Admin check & entry ────────────────────────────────────────────────────────

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def main():
    # Re-launch as admin if not already elevated
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
