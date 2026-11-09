from core.paths import asset

THEMES = {
    "warm":   {"label": "Warm Saffron",     "bg": "#FBF5E6", "fg": "#2B2A26", "accent": "#C9A24B", "primary": "#1F3D2B", "hot": "#D98324", "bubble_bot": "#F1E6C8", "bubble_user": "#1F3D2B", "bubble_user_fg": "#FBF5E6", "input_bg": "#FFFFFF", "arrow": "dark"},
    "indigo": {"label": "Indigo Night",     "bg": "#1B1F3B", "fg": "#EDE6D5", "accent": "#E0B75A", "primary": "#F2D899", "hot": "#C78E3F", "bubble_bot": "#2A3560", "bubble_user": "#F2D899", "bubble_user_fg": "#1B1F3B", "input_bg": "#232A4A", "arrow": "light"},
    "lotus":  {"label": "Lotus Pink",       "bg": "#FDF1EC", "fg": "#3D1F1F", "accent": "#C98A5E", "primary": "#5A2A2A", "hot": "#E8A67B", "bubble_bot": "#F8E0D2", "bubble_user": "#5A2A2A", "bubble_user_fg": "#FDF1EC", "input_bg": "#FFFFFF", "arrow": "dark"},
    "forest": {"label": "Forest Sanctuary", "bg": "#EAF0E5", "fg": "#1A2A1E", "accent": "#B8973A", "primary": "#1F3D2B", "hot": "#C47028", "bubble_bot": "#D9E3CF", "bubble_user": "#1F3D2B", "bubble_user_fg": "#EAF0E5", "input_bg": "#FFFFFF", "arrow": "dark"},
    "dusk":   {"label": "Dusk Gold",        "bg": "#141B2A", "fg": "#EDE6D5", "accent": "#E0B75A", "primary": "#F2D899", "hot": "#C78E3F", "bubble_bot": "#1F2A44", "bubble_user": "#F2D899", "bubble_user_fg": "#141B2A", "input_bg": "#1A2338", "arrow": "light"},
}

_ACTIVE_THEME = "warm"

def current():
    return THEMES.get(_ACTIVE_THEME, THEMES["warm"])

# Backward compat
CREAM   = THEMES["warm"]["bg"]
FOREST  = THEMES["warm"]["primary"]
GOLD    = THEMES["warm"]["accent"]
SAFFRON = THEMES["warm"]["hot"]
INK     = THEMES["warm"]["fg"]

def _bg_path():
    p = asset("background.png")
    return str(p).replace("\\", "/") if p.exists() else None

def _chevron(theme):
    name = "chevron_light.png" if THEMES.get(theme, THEMES["warm"])["arrow"] == "light" else "chevron_dark.png"
    p = asset(name)
    return str(p).replace("\\", "/") if p.exists() else None

def qss(pt=13, theme="warm"):
    global _ACTIVE_THEME
    _ACTIVE_THEME = theme if theme in THEMES else "warm"
    t = THEMES[_ACTIVE_THEME]
    bg, fg, accent, primary, hot = t["bg"], t["fg"], t["accent"], t["primary"], t["hot"]
    bb, bu, buf = t["bubble_bot"], t["bubble_user"], t["bubble_user_fg"]
    ib = t["input_bg"]
    chev = _chevron(_ACTIVE_THEME)
    bg_img = _bg_path()
    root_bg = f"background: {bg};"
    if bg_img:
        root_bg = f"border-image: url({bg_img}) 0 0 0 0 stretch stretch;"
    if chev:
        chev_qss = f"QComboBox::down-arrow {{ image: url({chev}); width: 12px; height: 8px; margin-right: 8px; }}"
    else:
        chev_qss = ("QComboBox::down-arrow { image: none; width: 0; height: 0;"
                    f" border-left: 4px solid transparent; border-right: 4px solid transparent;"
                    f" border-top: 6px solid {primary}; margin-right: 8px; }}")
    return f"""
* {{ font-family: 'Segoe UI', 'Georgia', sans-serif; font-size: {pt}pt; color: {fg}; }}
QMainWindow, QDialog, QWidget#root {{ {root_bg} }}
QDialog#ring_dialog {{ border-image: none; background: {bg}; }}
QLabel, QCheckBox, QRadioButton {{ background: {bg}; border-radius: 6px; padding: 2px 6px; }}
QLabel#title {{ font-size: {pt + 6}pt; color: {primary}; font-weight: 600; background: transparent; }}
QPushButton {{ background: {primary}; color: {bg}; border: none; border-radius: 14px; padding: 9px 16px; }}
QPushButton:hover {{ background: {accent}; }}
QPushButton:disabled {{ background: #9aa89f; }}
QPushButton#gold {{ background: {accent}; color: {primary}; font-weight: 600; }}
QPushButton#saffron {{ background: {hot}; color: white; }}
QPushButton#danger {{ background: #9b3b2e; color: white; }}
QPushButton#ghost {{ background: {bg}; color: {primary}; border: 1px solid {accent}; }}
QLineEdit, QTextEdit, QSpinBox, QListWidget {{ background: {ib}; border: 1px solid {accent}; border-radius: 12px; padding: 7px; color: {fg}; }}
QComboBox {{ background: {ib}; border: 1px solid {accent}; border-radius: 12px; padding: 7px 28px 7px 12px; color: {fg}; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; width: 24px; border: none; background: transparent; }}
{chev_qss}
QComboBox QAbstractItemView {{ background: {ib}; color: {fg}; selection-background-color: {accent}; selection-color: {primary}; }}
QTextBrowser {{ background: {ib}; border: 1px solid {accent}; border-radius: 14px; padding: 6px; color: {fg}; }}
QLabel#status {{ color: {hot}; font-weight: 600; background: transparent; }}
QLabel#notice {{ background: {bb}; border: 1px solid {hot}; border-radius: 10px; padding: 6px 10px; }}
QLabel#sources {{ color: {fg}; font-size: {max(9, pt - 2)}pt; background: transparent; }}
QTabWidget::pane {{ border: 1px solid {accent}; border-radius: 10px; background: {bg}; }}
QTabBar::tab {{ background: {ib}; color: {fg}; padding: 6px 12px; border-radius: 8px; margin: 2px; }}
QTabBar::tab:selected {{ background: {primary}; color: {bg}; }}
"""
