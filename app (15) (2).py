import streamlit as st
import json
import os
import calendar
import io
import base64
import streamlit.components.v1 as components
from datetime import date, datetime, timedelta
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFont


def make_app_icon():
    """Draw a green-and-red CM icon within this single Python file."""
    icon = Image.new("RGB", (512, 512), "#ffffff")
    draw = ImageDraw.Draw(icon)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 208)
    except OSError:
        font = ImageFont.load_default()
    for letter, left, color in (("C", 92, "#159263"), ("M", 243, "#d53857")):
        draw.text((left, 130), letter, fill=color, font=font)
    return icon


APP_ICON = make_app_icon()

# -----------------------------------------------------------------------------
# APP CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(page_title="CarerMate", page_icon=APP_ICON, layout="centered")

def install_ios_webapp_metadata():
    """Provide the matching icon without requiring an additional uploaded file."""
    icon_buffer = io.BytesIO()
    APP_ICON.save(icon_buffer, format="PNG")
    icon_data = "data:image/png;base64," + base64.b64encode(icon_buffer.getvalue()).decode("ascii")
    components.html(
        f"""
        <script>
        (() => {{
          const d = window.parent.document;
          const icon = '{icon_data}';
          const upsertLink = (rel, href) => {{
            let el = d.head.querySelector(`link[rel='${{rel}}']`);
            if (!el) {{ el = d.createElement('link'); el.rel = rel; d.head.appendChild(el); }}
            el.href = href;
          }};
          const upsertMeta = (name, content) => {{
            let el = d.head.querySelector(`meta[name='${{name}}']`);
            if (!el) {{ el = d.createElement('meta'); el.name = name; d.head.appendChild(el); }}
            el.content = content;
          }};
          upsertLink('apple-touch-icon', icon);
          upsertLink('icon', icon);
          upsertMeta('apple-mobile-web-app-capable', 'yes');
          upsertMeta('apple-mobile-web-app-title', 'CarerMate');
          upsertMeta('apple-mobile-web-app-status-bar-style', 'black-translucent');
          upsertMeta('theme-color', '#091429');
          d.title = 'CarerMate';
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


install_ios_webapp_metadata()

BASE_DIR = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE_DIR, "carer_data.json")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Rota anchor: week containing 18 Sep 2026 is Week A.
ANCHOR_DATE = date(2026, 9, 18)
ANCHOR_MONDAY = ANCHOR_DATE - timedelta(days=ANCHOR_DATE.weekday())
WEEK_A_DAYS = {1, 2, 5, 6}  # Tue, Wed, Sat, Sun (Mon=0)
WEEK_B_DAYS = {1, 2, 3, 4}  # Tue, Wed, Thu, Fri

# Confirmed payroll anchor from the last payday of 28 Aug 2026.
PAY_CYCLE_ANCHOR = "2026-07-27"

# -----------------------------------------------------------------------------
# STYLE
# -----------------------------------------------------------------------------
BASE_CSS = """
<style>
.stApp {
  --bg:light-dark(#f6f8f5,#091429);
  --panel:light-dark(#ffffff,#11213c);
  --panel2:light-dark(#eef4ef,#1a2c4a);
  --text:light-dark(#14294d,#f6f9ff);
  --muted:light-dark(#536787,#aebfda);
  --accent:light-dark(#c7294b,#e84b62);
  --accent2:light-dark(#a51e3e,#ffabb8);
  --green:light-dark(#12865e,#42c38d);
  --orange:light-dark(#a86409,#f7bb69);
  --red:light-dark(#c7294b,#f36a7d);
  --border:light-dark(#d8e5da,#36534a);
  --accent-soft:light-dark(#ffe7ec,#42263b);
  --accent-border:light-dark(#f3b7c4,#a64c68);
  --accent-text:light-dark(#9f1837,#ffe0e5);
  --hero-bg:linear-gradient(130deg,#157a55,#176148 68%,#254c43);
  --progress-bg:light-dark(#dcebe0,#2a4239);
  --nav-bg:light-dark(rgba(249,251,255,.97),rgba(9,20,41,.97));
  --nav-muted:light-dark(#617393,#a2b2cf);
}
.stApp, [data-testid="stAppViewContainer"] { background:var(--bg)!important; color:var(--text)!important; }
[data-testid="stHeader"], [data-testid="stToolbar"] { background: transparent; }
[data-testid="stSidebar"] { display:none; }
.block-container { max-width: 760px; padding-top: 1.1rem; padding-bottom: 7.2rem; }
h1,h2,h3 { color:var(--text)!important; letter-spacing:-.02em; }
p, label, .stMarkdown, .stCaption { color:var(--text); }
[data-testid="stCaptionContainer"] { color:var(--muted)!important; }
hr { border-color:var(--border)!important; }

/* Streamlit inputs */
.stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input,
[data-baseweb="select"] > div {
  background:var(--panel2)!important; color:var(--text)!important; border-color:var(--border)!important;
  border-radius:12px!important;
}
.stButton button, .stFormSubmitButton button {
  width:100%; border-radius:12px; min-height:44px; border:1px solid var(--accent-border);
  background:var(--accent-soft); box-shadow:0 0 0 1px rgba(232,75,98,.18) inset; color:var(--accent-text); font-weight:700;
}
.stButton button:hover, .stFormSubmitButton button:hover { border-color:var(--accent); color:white; }
[data-testid="stExpander"] { background:var(--panel); border:1px solid var(--border); border-radius:16px; }
.stTabs [data-baseweb="tab-list"] { gap:8px; }
.stTabs [data-baseweb="tab"] { border-radius:999px; background:var(--panel); padding:7px 14px; }
.stTabs [aria-selected="true"] { background:var(--accent-soft)!important; color:var(--accent-text)!important; }

/* App components */
.brand { display:flex; align-items:center; justify-content:space-between; margin:0 0 14px; }
.brand-name { font-size:1.08rem; font-weight:800; letter-spacing:.01em; display:flex; align-items:center; gap:9px; }
.brand-logo { width:34px; height:34px; border-radius:10px; background:#fff; border:1px solid #d7d7d7; display:inline-flex; align-items:center; justify-content:center; box-shadow:0 2px 8px rgba(0,0,0,.18); font-weight:900; letter-spacing:-.11em; padding-right:.11em; }
.brand-logo .c { color:#159263; } .brand-logo .m { color:#d53857; }
.st-key-brand_header [data-testid="stHorizontalBlock"] { flex-direction:row!important; flex-wrap:nowrap!important; align-items:center!important; gap:8px!important; }
.st-key-brand_header [data-testid="stColumn"]:first-child { flex:1 1 auto!important; width:auto!important; min-width:0!important; }
.st-key-brand_header [data-testid="stColumn"]:last-child { flex:0 0 auto!important; width:auto!important; min-width:0!important; }
.st-key-brand_header [data-testid="stPopover"] button { width:auto!important; min-width:46px!important; min-height:46px!important; border-radius:50%!important; padding:0 10px!important; background:var(--panel)!important; border:1px solid var(--border)!important; color:var(--text)!important; }
.hero { background:var(--hero-bg); border:1px solid rgba(145,219,172,.35); border-radius:24px; padding:24px; box-shadow:0 20px 45px rgba(0,30,16,.16); margin:8px 0 14px; }
.hero-label { color:#e3f6e8; font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; }
.hero-value { color:#fff; font-size:2.35rem; line-height:1.05; font-weight:850; margin-top:6px; }
.hero-sub { color:#e0f4e7; margin-top:6px; font-size:.9rem; }
.grid2 { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin:10px 0; }
.grid3 { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; margin:10px 0; }
.card { background:var(--panel); border:1px solid var(--border); border-radius:19px; padding:16px; min-height:105px; box-shadow:0 10px 30px rgba(1,12,40,.08); }
.card-label { color:var(--muted); font-size:.76rem; margin-bottom:5px; }
.card-value { color:var(--text); font-size:1.25rem; font-weight:800; line-height:1.12; }
.card-sub { color:var(--muted); font-size:.75rem; margin-top:5px; }
.card-icon { font-size:1.45rem; line-height:1; margin-bottom:9px; }
.card-green { background:linear-gradient(145deg,rgba(20,151,95,.22),var(--panel) 75%); border-color:rgba(61,187,131,.46); }
.card-red { background:linear-gradient(145deg,rgba(239,68,68,.17),var(--panel) 68%); border-color:rgba(239,68,68,.42); }
.card-blue { background:linear-gradient(145deg,rgba(27,157,101,.17),var(--panel) 68%); border-color:rgba(61,187,131,.42); }
.card-purple { background:linear-gradient(145deg,rgba(26,132,84,.20),var(--panel) 68%); border-color:rgba(61,187,131,.35); }
.card-amber { background:linear-gradient(145deg,rgba(245,158,11,.18),var(--panel) 68%); border-color:rgba(245,158,11,.42); }
.card-teal { background:linear-gradient(145deg,rgba(24,135,91,.17),var(--panel) 68%); border-color:rgba(61,187,131,.38); }
.quick-strip { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; margin:12px 0 4px; }
.quick-chip { border-radius:14px; padding:10px 8px; text-align:center; font-size:.72rem; font-weight:750; border:1px solid var(--border); background:var(--panel); }
.quick-chip .qicon { display:block; font-size:1.25rem; margin-bottom:3px; }
.section-title { color:var(--text); font-weight:800; font-size:1.05rem; margin:24px 0 10px; letter-spacing:-.02em; }
.progress-shell { height:10px; background:var(--progress-bg); border-radius:99px; overflow:hidden; margin:10px 0 5px; }
.progress-fill { height:100%; background:linear-gradient(90deg,#159263,#d2474d); border-radius:99px; }
.status-row { background:var(--panel); border:1px solid var(--border); border-radius:15px; padding:13px 14px; margin:8px 0; }
.status-title { font-weight:750; }
.muted { color:var(--muted); }
.notify-bell { position:relative; display:inline-flex; align-items:center; justify-content:center; width:38px; height:38px; border-radius:999px; border:1px solid var(--accent-border); background:var(--accent-soft); color:var(--accent2)!important; text-decoration:none!important; font-size:1.15rem; }
.notify-badge { position:absolute; top:-5px; right:-5px; min-width:18px; height:18px; padding:0 4px; border-radius:999px; background:var(--red); color:white; font-size:.62rem; font-weight:800; display:flex; align-items:center; justify-content:center; border:2px solid var(--bg); }
.brand-actions { display:flex; align-items:center; gap:8px; }
.brand-inline{padding:0!important;margin:0!important}.header-page-pill{display:inline-flex;margin-top:4px}
.notification-card { background:var(--panel); border:1px solid var(--border); border-radius:17px; padding:14px; margin:9px 0; display:grid; grid-template-columns:42px 1fr; gap:11px; align-items:start; }
.notification-icon { width:42px; height:42px; border-radius:13px; display:flex; align-items:center; justify-content:center; font-size:1.25rem; background:var(--accent-soft); }
.notification-title { font-weight:800; color:var(--text); margin-bottom:3px; }
.notification-body { color:var(--muted); font-size:.84rem; line-height:1.35; }
.notification-time { color:var(--accent2); font-size:.72rem; font-weight:700; margin-top:6px; }

/* Calendar */
.calendar-head,
.calendar-grid {
  display:grid !important;
  grid-template-columns:repeat(7, minmax(0, 1fr)) !important;
  grid-auto-flow:row !important;
  width:100% !important;
  max-width:100% !important;
  gap:5px;
  box-sizing:border-box;
}
.calendar-head > div { min-width:0; color:var(--muted); font-size:.7rem; text-align:center; padding:6px 0; }
.calendar-grid > a { min-width:0 !important; width:100% !important; box-sizing:border-box !important; }
.cal-day { position:relative; aspect-ratio:1/1; min-height:39px; border-radius:11px; border:1px solid var(--border); background:var(--panel); color:var(--text)!important; text-decoration:none!important; display:flex!important; align-items:center; justify-content:center; font-size:.84rem; overflow:hidden; }
.cal-day.out { opacity:.28; }
.cal-day.today { border-color:var(--accent); box-shadow:inset 0 0 0 1px var(--accent); }
.cal-day.work::after,.cal-day.holiday::after,.cal-day.pending::after { content:""; position:absolute; bottom:5px; width:5px; height:5px; border-radius:50%; }
.cal-day.work::after { background:var(--green); }
.cal-day.holiday::after { background:var(--red); }
.cal-day.pending::after { background:var(--orange); }
.cal-day.selected { background:var(--accent-soft); border-color:var(--accent); }
.cal-legend { color:var(--muted); font-size:.76rem; margin-top:10px; line-height:1.6; }
.legend-work { color:var(--green); }
.legend-leave { color:var(--red); }
.legend-pending { color:var(--orange); }
.st-key-calendar_native [data-testid="stHorizontalBlock"] { display:grid!important; grid-template-columns:repeat(7,minmax(0,1fr))!important; gap:4px!important; }
.st-key-calendar_native [data-testid="stColumn"] { min-width:0!important; width:100%!important; }
.st-key-calendar_native .stButton button { position:relative!important; width:100%!important; aspect-ratio:1/1!important; min-height:0!important; padding:0!important; border-radius:11px!important; background:var(--panel)!important; border:1px solid var(--border)!important; color:var(--text)!important; font-size:.78rem!important; line-height:1.1!important; box-shadow:none!important; }
.st-key-calendar_native .stButton button:hover { border-color:var(--green)!important; }
.st-key-calendar_native .stButton button[kind="primary"] { background:var(--accent-soft)!important; border-color:var(--accent)!important; }
.st-key-calendar_native .stButton button:disabled { opacity:.28!important; }
.calendar-empty { aspect-ratio:1/1; }

/* Smooth bottom navigation using a native Streamlit radio.
   Keeps the original six-tab proportions without browser reloads. */
.st-key-bottom_nav_native {
  position:fixed !important;
  z-index:9999 !important;
  bottom:0 !important;
  left:0 !important;
  right:0 !important;
  background:var(--nav-bg) !important;
  backdrop-filter:blur(14px);
  border-top:1px solid var(--border);
  padding:7px 6px max(8px, env(safe-area-inset-bottom)) !important;
}
.st-key-bottom_nav_native [role="radiogroup"] {
  display:grid !important;
  grid-template-columns:repeat(6,minmax(0,1fr)) !important;
  gap:2px !important;
  width:100% !important;
}
.st-key-bottom_nav_native [role="radiogroup"] label {
  margin:0 !important;
  padding:7px 1px !important;
  min-width:0 !important;
  min-height:54px !important;
  border-radius:12px !important;
  display:flex !important;
  align-items:center !important;
  justify-content:center !important;
  text-align:center !important;
  background:transparent !important;
  color:var(--nav-muted) !important;
}
.st-key-bottom_nav_native [role="radiogroup"] label > div:first-child {
  display:none !important;
}
.st-key-bottom_nav_native [role="radiogroup"] label p {
  margin:0 !important;
  font-size:.66rem !important;
  line-height:1.35 !important;
  font-weight:650 !important;
  color:inherit !important;
  white-space:pre-line !important;
}
.st-key-bottom_nav_native [role="radiogroup"] label:has(input:checked) {
  background:var(--accent-soft) !important;
  color:var(--accent2) !important;
}
.st-key-bottom_nav_native [role="radiogroup"] label:has(input:checked) p {
  color:var(--accent2) !important;
}

@media (max-width:520px) {
  /* Keep the bar attached to the bottom while lifting its clickable labels. */
  .st-key-bottom_nav_native [role="radiogroup"] label {
    box-sizing:border-box!important;
    min-height:124px!important;
    justify-content:flex-start!important;
    padding:12px 1px 66px!important;
  }
  .block-container { padding-left:10px; padding-right:10px; padding-top:.8rem; padding-bottom:10rem; }
  .hero { padding:17px; }
  .hero-value { font-size:2rem; }
  .card { padding:12px; min-height:82px; }
  .card-value { font-size:1.05rem; }
  .grid3 { gap:6px; }
  .calendar-head, .calendar-grid {
    display:grid !important;
    grid-template-columns:repeat(7, minmax(0, 1fr)) !important;
    gap:3px !important;
    width:100% !important;
    max-width:100% !important;
  }
  .calendar-head > div { font-size:.61rem; padding:4px 0; }
  .cal-day { min-height:0 !important; height:auto !important; aspect-ratio:1/1 !important; border-radius:8px; font-size:.72rem; padding:0 !important; }
  .cal-day.work::after,.cal-day.holiday::after,.cal-day.pending::after { bottom:3px; width:4px; height:4px; }
  .cal-legend { font-size:.68rem; }
}
</style>
"""

# -----------------------------------------------------------------------------
# DATA
# -----------------------------------------------------------------------------
def default_data():
    return {
        "profile": {
            "name": "",
            "email": "",
            "role": "Carer / Caregiver",
            "unit": "Earlswood",
            "manager": "Sham",
            "shift_start": "20:00",
            "shift_end": "08:00",
            "shift_len": 12,
            "unpaid_break": 1,
            "paid_hours": 11,
            "shifts_per_week": 4,
            "paid_hours_per_week": 44,
        },
        "appearance": {"theme": "dark"},
        "rates": [{"effective_from": "2026-01-01", "rate": 12.77}],
        "shift_overrides": {},
        "holiday_entitlement": {"2026": 246.4, "2027": 246.4},
        "holiday_requests": [],
        "training": [
            {
                "id": "t1",
                "name": "Yearly Updates Training",
                "last_done": "",
                "next_due": "2027-03-09",
                "due_month": "",
                "recurrence": "yearly",
                "notes": "",
                "doc": None,
            },
            {
                "id": "t2",
                "name": "DMI Moving and Handling Updates",
                "last_done": "",
                "next_due": "2027-03-02",
                "due_month": "",
                "recurrence": "yearly",
                "notes": "",
                "doc": None,
            },
            {
                "id": "t3",
                "name": "First Aid Training",
                "last_done": "",
                "next_due": "",
                "due_month": "2027-02",
                "recurrence": "custom",
                "notes": "Exact date TBC",
                "doc": None,
            },
        ],
        "pay_period_start": PAY_CYCLE_ANCHOR,
        "pay_history": [],
        "notif_settings": {
            "shift_tonight": True,
            "shift_tomorrow": True,
            "holiday_start": True,
            "holiday_5_days": True,
            "holiday_3_days": True,
            "holiday_pending": True,
            "training_due": True,
            "training_5_days": True,
            "training_3_days": True,
            "training_overdue": True,
            "pay_period_end": True,
            "payday_tomorrow": True,
        },
        "known_holiday_dates": {
            "2026": [
                "2026-06-23", "2026-06-24", "2026-06-25", "2026-06-26",
                "2026-12-08", "2026-12-09", "2026-12-12", "2026-12-13",
                "2026-12-15", "2026-12-16", "2026-12-17", "2026-12-18",
            ],
            "2027": [
                "2027-01-28", "2027-01-29", "2027-02-11", "2027-02-12",
                "2027-02-25", "2027-02-26", "2027-03-16", "2027-03-17",
                "2027-03-20", "2027-03-21",
            ],
        },
        "seeded": False,
        "migration_v3": False,
    }


def deep_merge_defaults(existing, defaults):
    """Keep saved values, but add newly introduced keys."""
    if not isinstance(existing, dict):
        return defaults
    result = dict(defaults)
    for key, value in existing.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_defaults(value, result[key])
        else:
            result[key] = value
    return result


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return deep_merge_defaults(json.load(f), default_data())
        except (json.JSONDecodeError, OSError):
            pass
    return default_data()


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


if "D" not in st.session_state:
    st.session_state.D = load_data()
D = st.session_state.D


st.markdown(BASE_CSS, unsafe_allow_html=True)

# Crisp line icons are drawn inline, so the app needs no extra uploaded assets.
ICON_PATHS = {
    "Home": '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/>',
    "Calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18"/>',
    "Leave": '<path d="M4 21h16M12 21v-9m0 0c-4-4-8-3-9 0 3-1 5 0 9 2m0-2c3-4 7-4 9-1-3 0-5 1-9 3M12 12c-1-5-4-6-6-6 1 3 3 5 6 8m0-2c1-5 4-6 6-6-1 3-3 5-6 8"/>',
    "Training": '<path d="m2 9 10-5 10 5-10 5zM6 12v5c3 3 9 3 12 0v-5M22 9v7"/>',
    "Pay": '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/>',
    "Profile": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3-7 8-7s8 3 8 7"/>',
    "Moon": '<path d="M20 15A8 8 0 0 1 9 4a8 8 0 1 0 11 11z"/>',
    "Sparkles": '<path d="m12 2 1.7 5.3L19 9l-5.3 1.7L12 16l-1.7-5.3L5 9l5.3-1.7zM20 17l.6 1.4L22 19l-1.4.6L20 21l-.6-1.4L18 19l1.4-.6z"/>',
    "Clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "Water": '<path d="M12 3c-3 4-6 8-6 12a6 6 0 0 0 12 0c0-4-3-8-6-12z"/>',
}


def line_icon(name, size=24):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{ICON_PATHS[name]}</svg>')


NAV_PAGES = ["Home", "Calendar", "Leave", "Training", "Pay", "Profile"]
nav_icon_css = []
for position, name in enumerate(NAV_PAGES, 1):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="black" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
           f'{ICON_PATHS[name]}</svg>')
    nav_icon_css.append(
        f'.st-key-bottom_nav_native [role="radiogroup"] label:nth-child({position})::before'
        f'{{-webkit-mask:url("data:image/svg+xml,{quote(svg)}") center/contain no-repeat;'
        f'mask:url("data:image/svg+xml,{quote(svg)}") center/contain no-repeat;}}'
    )
st.markdown('<style>.st-key-bottom_nav_native [role="radiogroup"] label{flex-direction:column!important;gap:3px!important}'
            '.st-key-bottom_nav_native [role="radiogroup"] label::before{content:"";display:block;width:21px;'
            'height:21px;background:currentColor;flex:none}' + ''.join(nav_icon_css) +
            '.card-icon svg,.notification-icon svg{display:block;color:var(--green)}'
            '.page-heading{display:flex;align-items:center;gap:10px;font-size:2rem;line-height:1.2;'
            'font-weight:750;margin:.5rem 0 1rem}.page-heading svg{color:var(--green)}</style>',
            unsafe_allow_html=True)


def page_heading(name):
    st.markdown(f'<h1 class="page-heading">{line_icon(name, 28)}{name}</h1>', unsafe_allow_html=True)


def notification_icon(symbol):
    name = {"💧": "Water", "🌙": "Moon", "🌴": "Leave", "🎓": "Training", "💷": "Pay", "💳": "Pay"}.get(symbol, "Calendar")
    return line_icon(name, 22)


def holiday_hours_for_dates(dates):
    return len(dates) * float(D["profile"]["paid_hours"])


def add_seed_request(dates, status, label):
    if not dates:
        return
    dates = sorted(dates)
    D["holiday_requests"].append(
        {
            "id": f"seed_{label}",
            "start": dates[0],
            "end": dates[-1],
            "dates": dates,
            "hours": holiday_hours_for_dates(dates),
            "requested": dates[0],
            "notes": "",
            "status": status,
            "doc": None,
        }
    )


def seed_known_holidays():
    if D.get("seeded"):
        return
    add_seed_request(["2026-06-23", "2026-06-24", "2026-06-25", "2026-06-26"], "taken", "jun26")
    add_seed_request(
        ["2026-12-08", "2026-12-09", "2026-12-12", "2026-12-13", "2026-12-15", "2026-12-16", "2026-12-17", "2026-12-18"],
        "approved",
        "dec26",
    )
    # Known 2027 dates are preloaded as pending until the user confirms approval.
    add_seed_request(
        ["2027-01-28", "2027-01-29", "2027-02-11", "2027-02-12", "2027-02-25", "2027-02-26", "2027-03-16", "2027-03-17", "2027-03-20", "2027-03-21"],
        "pending",
        "known27",
    )
    D["seeded"] = True
    save_data(D)


def migrate_existing_data():
    if D.get("migration_v3"):
        return

    # Confirmed payroll anchor.
    D["pay_period_start"] = PAY_CYCLE_ANCHOR

    # Ensure current rate is present and editable through rate history.
    if not D.get("rates"):
        D["rates"] = [{"effective_from": "2026-01-01", "rate": 12.77}]

    # Correct known leave statuses even if an older build seeded them incorrectly.
    for r in D.get("holiday_requests", []):
        dates = set(r.get("dates", []))
        if "2026-06-23" in dates:
            r["status"] = "taken"
        elif "2026-12-08" in dates:
            r["status"] = "approved"
        elif dates and all(d.startswith("2027-") for d in dates) and str(r.get("id", "")).startswith("seed"):
            r["status"] = "pending"
        r["hours"] = holiday_hours_for_dates(r.get("dates", []))

    # First Aid: month known, exact date unknown.
    for t in D.get("training", []):
        t.setdefault("due_month", "")
        t.setdefault("doc", None)
        if t.get("name", "").strip().lower() == "first aid training":
            t["next_due"] = ""
            t["due_month"] = "2027-02"
            t["notes"] = t.get("notes") or "Exact date TBC"

    p = D["profile"]
    p["paid_hours_per_week"] = float(p.get("paid_hours", 11)) * float(p.get("shifts_per_week", 4))

    D["migration_v3"] = True
    save_data(D)


seed_known_holidays()
migrate_existing_data()

# -----------------------------------------------------------------------------
# CORE LOGIC
# -----------------------------------------------------------------------------
def monday_of(d):
    return d - timedelta(days=d.weekday())


def week_type_for(d):
    diff_weeks = (monday_of(d) - ANCHOR_MONDAY).days // 7
    return "A" if diff_weeks % 2 == 0 else "B"


def is_rota_work_day(d):
    days = WEEK_A_DAYS if week_type_for(d) == "A" else WEEK_B_DAYS
    return d.weekday() in days


def current_rate(date_str):
    rates = sorted(D["rates"], key=lambda r: r["effective_from"])
    if not rates:
        return 0.0
    rate = float(rates[0]["rate"])
    for r in rates:
        if r["effective_from"] <= date_str:
            rate = float(r["rate"])
        else:
            break
    return rate


def is_holiday_date(ds):
    return any(r.get("status") in ("approved", "taken") and ds in r.get("dates", []) for r in D["holiday_requests"])


def is_pending_holiday_date(ds):
    return any(r.get("status") == "pending" and ds in r.get("dates", []) for r in D["holiday_requests"])


def shift_status_for(ds):
    ov = D["shift_overrides"].get(ds)
    if ov:
        return ov
    d = date.fromisoformat(ds)
    if is_rota_work_day(d):
        return {"status": "scheduled"}
    return None


def all_shift_dates_in_range(start_d, end_d):
    out = []
    d = start_d
    while d <= end_d:
        ds = d.isoformat()
        ov = D["shift_overrides"].get(ds)
        rota = is_rota_work_day(d)
        hol = is_holiday_date(ds)
        counts = False
        extra = False
        if not hol:
            if ov:
                if ov.get("status") in ("scheduled", "worked", "extra"):
                    counts = True
                extra = ov.get("status") == "extra"
            elif rota:
                counts = True
        if counts:
            hours = float(ov.get("hours", D["profile"]["paid_hours"])) if ov else float(D["profile"]["paid_hours"])
            out.append({"date": ds, "hours": hours, "extra": extra})
        d += timedelta(days=1)
    return out


def current_period_for(ref_date):
    start = date.fromisoformat(D["pay_period_start"])
    end = start + timedelta(days=27)
    while end < ref_date:
        start += timedelta(days=28)
        end = start + timedelta(days=27)
    while start > ref_date:
        start -= timedelta(days=28)
        end = start + timedelta(days=27)
    return start, end


def payday_for(period_end):
    # Employer rule supplied: last working day of the following week.
    # Current implementation treats Friday as the normal last working day.
    next_week_mon = monday_of(period_end) + timedelta(days=7)
    return next_week_mon + timedelta(days=4)


def next_payday_for(ref_date):
    """Keep the preceding period's payday visible until that payday passes."""
    period_start, period_end = current_period_for(ref_date)
    previous_payday = payday_for(period_start - timedelta(days=1))
    if previous_payday >= ref_date:
        return previous_payday
    return payday_for(period_end)


def est_gross_for(shifts):
    return sum(float(s["hours"]) * current_rate(s["date"]) for s in shifts)


def estimate_tax_ni(period_gross, periods_per_year=13):
    """Approximate only; not a payroll engine."""
    annual_gross = float(period_gross) * periods_per_year
    personal_allowance = 12570
    basic_band = 37700
    taxable = max(0, annual_gross - personal_allowance)
    basic_portion = min(taxable, basic_band)
    higher_portion = max(0, taxable - basic_band)
    annual_tax = basic_portion * 0.20 + higher_portion * 0.40

    ni_pt, ni_uel = 12570, 50270
    niable = max(0, annual_gross - ni_pt)
    ni_basic = min(niable, ni_uel - ni_pt)
    ni_higher = max(0, niable - (ni_uel - ni_pt))
    annual_ni = ni_basic * 0.08 + ni_higher * 0.02

    return {
        "tax": annual_tax / periods_per_year,
        "ni": annual_ni / periods_per_year,
        "net": (annual_gross - annual_tax - annual_ni) / periods_per_year,
    }


def holiday_summary(year):
    ent = float(D["holiday_entitlement"].get(str(year), 0))
    reqs = [r for r in D["holiday_requests"] if any(dd.startswith(str(year)) for dd in r.get("dates", []))]

    def hours_for_status(status):
        total = 0.0
        for r in reqs:
            if r.get("status") == status:
                year_dates = [d for d in r.get("dates", []) if d.startswith(str(year))]
                total += holiday_hours_for_dates(year_dates)
        return total

    taken = hours_for_status("taken")
    approved = hours_for_status("approved")
    pending = hours_for_status("pending")
    confirmed_remaining = ent - taken - approved
    potential_remaining = confirmed_remaining - pending
    return {
        "ent": ent,
        "taken": taken,
        "approved": approved,
        "pending": pending,
        "confirmed_remaining": confirmed_remaining,
        "potential_remaining": potential_remaining,
    }


def training_sort_key(t):
    if t.get("next_due"):
        return t["next_due"]
    if t.get("due_month"):
        return f"{t['due_month']}-31"
    return "9999-12-31"


def training_due_label(t):
    if t.get("next_due"):
        return date.fromisoformat(t["next_due"]).strftime("%d %b %Y")
    if t.get("due_month"):
        return datetime.strptime(t["due_month"], "%Y-%m").strftime("%B %Y") + " · date TBC"
    return "TBC"


def training_status(t):
    today_ = date.today()
    if t.get("next_due"):
        due = date.fromisoformat(t["next_due"])
    elif t.get("due_month"):
        y, m = map(int, t["due_month"].split("-"))
        due = date(y, m, calendar.monthrange(y, m)[1])
    else:
        return "upcoming"
    days = (due - today_).days
    if days < 0:
        return "overdue"
    if days <= 30:
        return "due soon"
    return "upcoming"


def next_shift_from(ref_date):
    d = ref_date
    for _ in range(90):
        ds = d.isoformat()
        if not is_holiday_date(ds):
            st_ = shift_status_for(ds)
            if st_ and st_.get("status") in ("scheduled", "worked", "extra"):
                return ds
        d += timedelta(days=1)
    return None


def save_uploaded_file(uploaded_file, prefix):
    if uploaded_file is None:
        return None
    safe_name = os.path.basename(uploaded_file.name)
    fname = f"{prefix}_{safe_name}"
    path = os.path.join(UPLOAD_DIR, fname)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


def fmt(ds):
    return date.fromisoformat(ds).strftime("%a %d %b %Y")


def fmt_short(ds):
    return date.fromisoformat(ds).strftime("%d %b %Y")


def badge(status):
    icons = {
        "overdue": "🔴",
        "due soon": "🟠",
        "upcoming": "⚪",
        "approved": "🔵",
        "taken": "✅",
        "pending": "🟠",
        "declined": "🔴",
        "cancelled": "⚪",
    }
    return f"{icons.get(status, '⚪')} {status.title()}"


def render_bottom_nav(active):
    pages = NAV_PAGES
    if "main_nav" not in st.session_state or st.session_state.main_nav not in pages:
        st.session_state.main_nav = active if active in pages else "Home"

    with st.container(key="bottom_nav_native"):
        chosen = st.radio(
            "Navigation",
            options=pages,
            index=pages.index(st.session_state.main_nav),
            horizontal=True,
            label_visibility="collapsed",
            key="bottom_nav_radio",
        )

    return chosen


def render_brand(page, notif_count=0):
    with st.container(key="brand_header"):
        left, right = st.columns([8, 2], vertical_alignment="center")
        with left:
            st.markdown(
                "<div class='brand brand-inline'><div class='brand-name'><span class='brand-logo'><span class='c'>C</span><span class='m'>M</span></span><span>CarerMate</span></div></div>",
                unsafe_allow_html=True,
            )
        with right:
            render_notification_bell(date.today())


def render_notification_bell(today_):
    alerts = notification_items(today_, include_upcoming=False)
    upcoming = notification_items(today_, include_upcoming=True)
    current_keys = {(x["title"], x["body"]) for x in alerts}
    upcoming_only = [x for x in upcoming if (x["title"], x["body"]) not in current_keys]

    bell_label = f"🔔 {len(alerts)}" if alerts else "🔔"
    with st.popover(bell_label, help="Notifications", use_container_width=False):
        st.markdown("### 🔔 Notifications")
        if alerts:
            st.caption("Needs your attention")
            for item in alerts:
                st.markdown(
                    f"<div class='notification-card'><div class='notification-icon'>{notification_icon(item['icon'])}</div><div><div class='notification-title'>{item['title']}</div><div class='notification-body'>{item['body']}</div><div class='notification-time'>{item['when']}</div></div></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("You’re all caught up.")

        if upcoming_only:
            st.markdown("**Coming up**")
            for item in upcoming_only[:8]:
                st.markdown(
                    f"<div class='notification-card'><div class='notification-icon'>{notification_icon(item['icon'])}</div><div><div class='notification-title'>{item['title']}</div><div class='notification-body'>{item['body']}</div><div class='notification-time'>{item['when']}</div></div></div>",
                    unsafe_allow_html=True,
                )


def card(label, value, sub="", icon="", tone=""):
    tone_cls = f" card-{tone}" if tone else ""
    icon_html = f"<div class='card-icon'>{line_icon(icon)}</div>" if icon else ""
    return f"<div class='card{tone_cls}'>{icon_html}<div class='card-label'>{label}</div><div class='card-value'>{value}</div><div class='card-sub'>{sub}</div></div>"


def notification_items(today_, include_upcoming=False):
    """Build notification cards. Current alerts are shown first; upcoming adds a short planning view."""
    nset = D["notif_settings"]
    items = []
    today_s = today_.isoformat()
    tomorrow = (today_ + timedelta(days=1)).isoformat()

    st_today = shift_status_for(today_s)
    working_today = (not is_holiday_date(today_s)) and bool(st_today and st_today.get("status") in ("scheduled", "worked", "extra"))
    next_s = next_shift_from(today_ + timedelta(days=1 if working_today else 0))

    if nset.get("shift_tonight") and working_today:
        items.append({"icon":"💧", "title":"Shift tonight", "body":f"Your shift starts at {D['profile']['shift_start']}. Don’t forget your water and some juice so you stay hydrated.", "when":"Today", "priority":0})
    if nset.get("shift_tomorrow") and next_s == tomorrow:
        items.append({"icon":"🌙", "title":"Shift tomorrow", "body":f"Your next shift starts at {D['profile']['shift_start']} tomorrow.", "when":"Tomorrow", "priority":1})

    # Approved holiday reminders: 5 days, 3 days and 1 day before the first upcoming leave date.
    for r in D["holiday_requests"]:
        if r.get("status") != "approved":
            continue
        future_dates = sorted(ds for ds in r.get("dates", []) if ds >= today_s)
        if not future_dates:
            continue
        first = date.fromisoformat(future_dates[0])
        days = (first - today_).days
        if days == 5 and nset.get("holiday_5_days", True):
            items.append({"icon":"🌴", "title":"Holiday in 5 days", "body":f"Your approved leave starts {fmt_short(first.isoformat())}.", "when":"5 days", "priority":2})
        if days == 3 and nset.get("holiday_3_days", True):
            items.append({"icon":"🌴", "title":"Holiday in 3 days", "body":f"Your approved leave starts {fmt_short(first.isoformat())}.", "when":"3 days", "priority":2})
        if days == 1 and nset.get("holiday_start"):
            items.append({"icon":"🌴", "title":"Holiday starts tomorrow", "body":f"Your approved leave starts {fmt_short(first.isoformat())}.", "when":"Tomorrow", "priority":1})
        if include_upcoming and 0 <= days <= 30 and days not in (1,3,5):
            items.append({"icon":"🌴", "title":"Upcoming holiday", "body":f"Approved leave starts {fmt_short(first.isoformat())}.", "when":f"In {days} days" if days else "Today", "priority":5})

    if nset.get("holiday_pending") and any(r.get("status") == "pending" for r in D["holiday_requests"]):
        items.append({"icon":"🟠", "title":"Pending leave request", "body":"You have a holiday request still waiting for approval.", "when":"Action needed", "priority":3})

    # Training reminders. Exact 5/3-day reminders only work once an exact due date is set.
    for t in D["training"]:
        due = t.get("next_due")
        if due:
            due_d = date.fromisoformat(due)
            days = (due_d - today_).days
            if days == 5 and nset.get("training_5_days", True):
                items.append({"icon":"🎓", "title":"Training in 5 days", "body":f"{t['name']} is due {fmt_short(due)}.", "when":"5 days", "priority":2})
            if days == 3 and nset.get("training_3_days", True):
                items.append({"icon":"🎓", "title":"Training in 3 days", "body":f"{t['name']} is due {fmt_short(due)}.", "when":"3 days", "priority":2})
            status = training_status(t)
            if days < 0 and nset.get("training_overdue"):
                items.append({"icon":"🚨", "title":"Training overdue", "body":f"{t['name']} was due {fmt_short(due)}.", "when":"Overdue", "priority":0})
            elif include_upcoming and 0 <= days <= 30 and days not in (3,5):
                items.append({"icon":"🎓", "title":"Upcoming training", "body":f"{t['name']} is due {fmt_short(due)}.", "when":f"In {days} days" if days else "Today", "priority":5})
        elif include_upcoming and t.get("due_month"):
            label = datetime.strptime(t["due_month"], "%Y-%m").strftime("%B %Y")
            items.append({"icon":"🎓", "title":"Training date TBC", "body":f"{t['name']} is due in {label}; exact date not entered yet.", "when":"Date TBC", "priority":6})

    _, period_end = current_period_for(today_)
    payday = next_payday_for(today_)
    if nset.get("payday_tomorrow") and payday.isoformat() == tomorrow:
        items.append({"icon":"💷", "title":"Payday tomorrow", "body":f"Expected payday is {fmt_short(payday.isoformat())}.", "when":"Tomorrow", "priority":1})
    if nset.get("pay_period_end") and 0 <= (period_end - today_).days <= 2:
        items.append({"icon":"💳", "title":"Pay period ending", "body":f"This pay period ends {fmt_short(period_end.isoformat())}.", "when":"Soon", "priority":2})
    if include_upcoming and 0 <= (payday - today_).days <= 30:
        days = (payday - today_).days
        items.append({"icon":"💷", "title":"Next payday", "body":f"Expected payday is {fmt_short(payday.isoformat())}.", "when":f"In {days} days" if days else "Today", "priority":7})

    # Deduplicate cards that can overlap between current and upcoming rules.
    seen, clean = set(), []
    for item in sorted(items, key=lambda x: x.get("priority", 9)):
        key = (item["title"], item["body"])
        if key not in seen:
            seen.add(key); clean.append(item)
    return clean


def build_notifications(today_, working_today=None, next_s=None, payday=None):
    return [x["body"] for x in notification_items(today_, include_upcoming=False)]


# -----------------------------------------------------------------------------
# NAVIGATION
# -----------------------------------------------------------------------------
allowed_pages = ["Home", "Calendar", "Leave", "Training", "Pay", "Profile"]
requested_page = st.query_params.get("page", "")
if "main_nav" not in st.session_state:
    st.session_state.main_nav = requested_page if requested_page in allowed_pages else "Home"

page = st.session_state.main_nav
today = date.today()
current_alerts = notification_items(today, include_upcoming=False)
render_brand(page, len(current_alerts))

# -----------------------------------------------------------------------------
# HOME
# -----------------------------------------------------------------------------
if page == "Home":
    name = D["profile"]["name"].strip() or "there"

    today_str = today.isoformat()
    st_today = shift_status_for(today_str)
    working_today = (not is_holiday_date(today_str)) and bool(st_today and st_today.get("status") in ("scheduled", "worked", "extra"))
    next_s = next_shift_from(today + timedelta(days=1 if working_today else 0))

    week_start = monday_of(today)
    week_end = week_start + timedelta(days=6)
    week_shifts = all_shift_dates_in_range(week_start, week_end)

    p_start, p_end = current_period_for(today)
    period_shifts = all_shift_dates_in_range(p_start, p_end)
    period_gross = est_gross_for(period_shifts)

    # Add holiday pay date-by-date, respecting effective-dated rates.
    period_holiday_dates = []
    for r in D["holiday_requests"]:
        if r.get("status") in ("approved", "taken"):
            for ds in r.get("dates", []):
                if p_start.isoformat() <= ds <= p_end.isoformat():
                    period_holiday_dates.append(ds)
    holiday_gross = sum(float(D["profile"]["paid_hours"]) * current_rate(ds) for ds in set(period_holiday_dates))
    period_gross += holiday_gross

    tax_ni = estimate_tax_ni(period_gross)
    payday = next_payday_for(today)
    hs = holiday_summary(today.year)
    next_train = sorted(D["training"], key=training_sort_key)[0] if D["training"] else None

    st.markdown(f"<div class='hero'><div class='hero-label'>Welcome back</div><div class='hero-value'>Hello, {name} 👋</div><div class='hero-sub'>{D['profile']['unit']} · {today.strftime('%A %d %B %Y')}</div></div>", unsafe_allow_html=True)

    status_value = "Working" if working_today else "Off today"
    next_value = fmt_short(next_s) if next_s else "—"
    today_tone = "blue" if working_today else "teal"
    st.markdown(
        "<div class='grid2'>"
        + card("Today", status_value, f"{D['profile']['shift_start']}–{D['profile']['shift_end']}" if working_today else "No scheduled shift", "Moon" if working_today else "Sparkles", today_tone)
        + card("Next shift", next_value, D["profile"]["shift_start"] if next_s else "", "Calendar", "blue")
        + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='grid2'>"
        + card("Paid hours this week", f"{sum(s['hours'] for s in week_shifts):.0f}h", f"{len(week_shifts)} shifts", "Clock", "purple")
        + card("Est. take-home", f"£{tax_ni['net']:.2f}", f"Gross £{period_gross:.2f}", "Pay", "blue")
        + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='grid2'>"
        + card("Next payday", fmt_short(payday.isoformat()), f"{max(0,(payday-today).days)} days away", "Pay", "blue")
        + card("Holiday remaining", f"{hs['confirmed_remaining']:.1f}h", f"≈ {hs['confirmed_remaining']/float(D['profile']['paid_hours']):.1f} shifts", "Leave", "red")
        + "</div>",
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# CALENDAR
# -----------------------------------------------------------------------------
elif page == "Calendar":
    page_heading("Calendar")

    if "calendar_month" not in st.session_state:
        try:
            initial_year = int(st.query_params.get("year", today.year))
            initial_month = int(st.query_params.get("month", today.month))
            st.session_state.calendar_month = date(initial_year, initial_month, 1)
        except ValueError:
            st.session_state.calendar_month = today.replace(day=1)
    if "calendar_selected" not in st.session_state:
        st.session_state.calendar_selected = ""

    current_first = st.session_state.calendar_month
    year, month = current_first.year, current_first.month
    prev_last = current_first - timedelta(days=1)
    next_first = (current_first.replace(day=28) + timedelta(days=4)).replace(day=1)

    nav1, nav2, nav3 = st.columns([1, 2.2, 1])
    if nav1.button("← Prev", key="calendar_prev"):
        st.session_state.calendar_month = prev_last.replace(day=1)
        st.session_state.calendar_selected = ""
        st.rerun()
    nav2.markdown(f"<div style='text-align:center;font-weight:800'>{current_first.strftime('%B %Y')}</div>", unsafe_allow_html=True)
    if nav3.button("Next →", key="calendar_next"):
        st.session_state.calendar_month = next_first
        st.session_state.calendar_selected = ""
        st.rerun()

    grid_start = monday_of(current_first)
    cells = [grid_start + timedelta(days=i) for i in range(42)]
    st.markdown("<div class='calendar-head'>" + "".join(f"<div>{d}</div>" for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]) + "</div>", unsafe_allow_html=True)
    day_styles = []
    with st.container(key="calendar_native"):
        for week in range(6):
            columns = st.columns(7, gap="small")
            for weekday, col in enumerate(columns):
                d = cells[week * 7 + weekday]
                with col:
                    if d.month != month:
                        st.button(str(d.day), key=f"calendar_day_{d.isoformat()}", disabled=True, use_container_width=True)
                        continue
                    ds = d.isoformat()
                    if is_holiday_date(ds):
                        dot_color = "var(--red)"
                    elif is_pending_holiday_date(ds):
                        dot_color = "var(--orange)"
                    else:
                        shift = shift_status_for(ds)
                        dot_color = "var(--green)" if shift and shift.get("status") in ("scheduled", "worked", "extra") else ""
                    selector = f".st-key-calendar_day_{ds} button"
                    if dot_color:
                        day_styles.append(f"{selector}::after{{content:'';position:absolute;bottom:5px;left:50%;transform:translateX(-50%);width:5px;height:5px;border-radius:50%;background:{dot_color}}}")
                    if d == today:
                        day_styles.append(f"{selector}{{border-color:var(--accent)!important;box-shadow:inset 0 0 0 1px var(--accent)!important}}")
                    if st.button(str(d.day), key=f"calendar_day_{ds}", type="primary" if ds == st.session_state.calendar_selected else "secondary", use_container_width=True):
                        st.session_state.calendar_selected = ds
    st.markdown("<style>" + "".join(day_styles) + "</style>", unsafe_allow_html=True)

    st.markdown("<div class='cal-legend'><span class='legend-work'>●</span> Blue = work &nbsp; <span class='legend-leave'>●</span> Red = approved/taken leave &nbsp; <span class='legend-pending'>●</span> Amber = pending leave</div>", unsafe_allow_html=True)

    selected = st.session_state.calendar_selected
    if selected:
        try:
            date.fromisoformat(selected)
            st.markdown(f"<div class='section-title'>Edit {date.fromisoformat(selected).strftime('%A %d %B')}</div>", unsafe_allow_html=True)
            cur = D["shift_overrides"].get(selected, {})
            current_status = cur.get("status") or (shift_status_for(selected) or {}).get("status", "off")
            options = ["scheduled", "worked", "missed", "cancelled", "extra", "off"]
            idx = options.index(current_status) if current_status in options else 0
            status = st.selectbox("Shift status", options, index=idx, key=f"shift_status_{selected}")
            hours = st.number_input("Paid hours", value=float(cur.get("hours", D["profile"]["paid_hours"])), min_value=0.0, step=0.5, key=f"shift_hours_{selected}")
            notes = st.text_area("Notes", value=cur.get("notes", ""), key=f"shift_notes_{selected}")
            if st.button("Save day"):
                if status in ("off", "cancelled"):
                    D["shift_overrides"][selected] = {"status": "cancelled", "hours": 0.0, "notes": notes}
                else:
                    D["shift_overrides"][selected] = {"status": status, "hours": hours, "notes": notes}
                save_data(D)
                st.success("Saved.")
                st.rerun()
        except ValueError:
            pass

    with st.expander("＋ Add extra shift"):
        with st.form("extra_shift_form"):
            ex_date = st.date_input("Date", value=today)
            ex_hours = st.number_input("Paid hours", value=float(D["profile"]["paid_hours"]), min_value=0.0, step=0.5)
            ex_notes = st.text_area("Notes")
            if st.form_submit_button("Add shift"):
                D["shift_overrides"][ex_date.isoformat()] = {"status": "extra", "hours": ex_hours, "notes": ex_notes}
                save_data(D)
                st.success("Extra shift added.")
                st.rerun()

# -----------------------------------------------------------------------------
# LEAVE
# -----------------------------------------------------------------------------
elif page == "Leave":
    page_heading("Leave")
    tab1, tab2 = st.tabs(["Overview", "Requests"])

    with tab1:
        year = today.year
        hs = holiday_summary(year)
        shifts_remaining = hs["confirmed_remaining"] / float(D["profile"]["paid_hours"]) if D["profile"]["paid_hours"] else 0
        allocated = hs["taken"] + hs["approved"]
        pct = min(100, max(0, (allocated / hs["ent"] * 100) if hs["ent"] else 0))

        st.markdown(f"<div class='hero'><div class='hero-label'>{year} holiday balance</div><div class='hero-value'>{hs['confirmed_remaining']:.1f}h</div><div class='hero-sub'>≈ {shifts_remaining:.1f} shifts remaining</div></div>", unsafe_allow_html=True)
        st.markdown("<div class='grid3'>" + card("Taken", f"{hs['taken']:.0f}h") + card("Approved", f"{hs['approved']:.0f}h") + card("Pending", f"{hs['pending']:.0f}h") + "</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='section-title'>Entitlement use</div><div class='progress-shell'><div class='progress-fill' style='width:{pct:.1f}%'></div></div><div class='muted'>{allocated:.1f}h allocated of {hs['ent']:.1f}h</div>", unsafe_allow_html=True)
        if hs["pending"] > 0:
            st.caption(f"If all pending leave is approved, potential remaining balance will be {hs['potential_remaining']:.1f}h.")

        with st.expander("Edit annual entitlement"):
            new_ent = st.number_input(f"Entitlement for {year} (hours)", value=float(D["holiday_entitlement"].get(str(year), 0)), min_value=0.0, step=0.5)
            if st.button("Update entitlement"):
                D["holiday_entitlement"][str(year)] = new_ent
                save_data(D)
                st.rerun()

    with tab2:
        with st.expander("＋ Add leave request", expanded=False):
            start = st.date_input("Start date", value=today, key="leave_start")
            end = st.date_input("End date", value=today, key="leave_end")
            if end < start:
                st.warning("End date must be on or after the start date.")
                candidate_dates = []
            else:
                candidate_dates = []
                d = start
                while d <= end:
                    ds = d.isoformat()
                    # Only scheduled rota shifts (or explicit scheduled/worked shifts) are offered as leave dates.
                    ss = shift_status_for(ds)
                    if ss and ss.get("status") in ("scheduled", "worked"):
                        candidate_dates.append(ds)
                    d += timedelta(days=1)

            selected_dates = st.multiselect(
                "Shift dates to book as leave",
                options=candidate_dates,
                default=candidate_dates,
                format_func=lambda ds: fmt(ds),
                help="Only scheduled work shifts are listed. Holiday entitlement is deducted only for the shifts selected here.",
            )
            proposed_hours = holiday_hours_for_dates(selected_dates)
            st.caption(f"This request will use {proposed_hours:.1f} holiday hours.")
            status = st.selectbox("Status", ["pending", "approved", "declined", "cancelled", "taken"], key="new_leave_status")
            notes = st.text_area("Notes", key="new_leave_notes")
            doc = st.file_uploader("Approval evidence (optional)", type=["png", "jpg", "jpeg", "pdf"], key="new_leave_doc")
            if st.button("Create request", key="create_leave"):
                if not selected_dates:
                    st.error("Select at least one shift date.")
                else:
                    req_id = f"h{int(datetime.now().timestamp())}"
                    D["holiday_requests"].append(
                        {
                            "id": req_id,
                            "start": min(selected_dates),
                            "end": max(selected_dates),
                            "dates": sorted(selected_dates),
                            "hours": holiday_hours_for_dates(selected_dates),
                            "requested": today.isoformat(),
                            "notes": notes,
                            "status": status,
                            "doc": save_uploaded_file(doc, req_id) if doc else None,
                        }
                    )
                    save_data(D)
                    st.success("Holiday request created.")
                    st.rerun()

        st.markdown("<div class='section-title'>Leave history</div>", unsafe_allow_html=True)
        reqs = sorted(D["holiday_requests"], key=lambda r: r.get("start", ""), reverse=True)
        for r in reqs:
            hours = holiday_hours_for_dates(r.get("dates", []))
            title = f"{fmt_short(r['start'])} – {fmt_short(r['end'])} · {badge(r['status'])}"
            with st.expander(title):
                st.write(f"**{hours:.1f}h** · {len(r.get('dates', []))} shift(s)")
                st.caption(", ".join(fmt_short(ds) for ds in r.get("dates", [])))
                new_status = st.selectbox(
                    "Status",
                    ["pending", "approved", "declined", "cancelled", "taken"],
                    index=["pending", "approved", "declined", "cancelled", "taken"].index(r.get("status", "pending")),
                    key=f"status_{r['id']}",
                )
                notes = st.text_area("Notes", value=r.get("notes", ""), key=f"leave_notes_{r['id']}")
                doc = st.file_uploader("Upload/replace approval evidence", key=f"doc_{r['id']}", type=["png", "jpg", "jpeg", "pdf"])
                c1, c2 = st.columns(2)
                if c1.button("Save", key=f"save_{r['id']}"):
                    r["status"] = new_status
                    r["notes"] = notes
                    r["hours"] = hours
                    if doc:
                        r["doc"] = save_uploaded_file(doc, r["id"])
                    save_data(D)
                    st.rerun()
                if c2.button("Delete", key=f"del_{r['id']}"):
                    D["holiday_requests"] = [x for x in D["holiday_requests"] if x["id"] != r["id"]]
                    save_data(D)
                    st.rerun()

# -----------------------------------------------------------------------------
# TRAINING
# -----------------------------------------------------------------------------
elif page == "Training":
    page_heading("Training")

    if D["training"]:
        for t in sorted(D["training"], key=training_sort_key):
            with st.expander(f"{t['name']} · {badge(training_status(t))}"):
                st.caption(f"Due: {training_due_label(t)}")

                name = st.text_input("Training name", value=t.get("name", ""), key=f"trname_{t['id']}")
                exact_known = st.checkbox("Exact due date known", value=bool(t.get("next_due")), key=f"exact_{t['id']}")
                if exact_known:
                    base_due = date.fromisoformat(t["next_due"]) if t.get("next_due") else today
                    next_due = st.date_input("Next due date", value=base_due, key=f"due_{t['id']}")
                    due_month = ""
                else:
                    current_month = t.get("due_month") or today.strftime("%Y-%m")
                    y0, m0 = map(int, current_month.split("-"))
                    mc1, mc2 = st.columns(2)
                    month_num = mc1.selectbox("Due month", list(range(1, 13)), index=m0 - 1, format_func=lambda m: calendar.month_name[m], key=f"month_{t['id']}")
                    year_num = mc2.number_input("Due year", min_value=2020, max_value=2100, value=y0, step=1, key=f"year_{t['id']}")
                    next_due = None
                    due_month = f"{int(year_num):04d}-{int(month_num):02d}"

                recurrence_options = ["yearly", "2-yearly", "custom", "none"]
                rec_val = t.get("recurrence", "none") if t.get("recurrence", "none") in recurrence_options else "custom"
                recurrence = st.selectbox("Recurrence", recurrence_options, index=recurrence_options.index(rec_val), key=f"recur_{t['id']}")
                notes = st.text_area("Notes", value=t.get("notes", ""), key=f"trnotes_{t['id']}")
                doc = st.file_uploader("Upload/replace certificate", key=f"cert_{t['id']}", type=["png", "jpg", "jpeg", "pdf"])

                c1, c2, c3 = st.columns(3)
                if c1.button("Save", key=f"save_tr_{t['id']}"):
                    t["name"] = name.strip() or t["name"]
                    t["next_due"] = next_due.isoformat() if exact_known and next_due else ""
                    t["due_month"] = "" if exact_known else due_month
                    t["recurrence"] = recurrence
                    t["notes"] = notes
                    if doc:
                        t["doc"] = save_uploaded_file(doc, t["id"])
                    save_data(D)
                    st.rerun()

                if c2.button("Completed", key=f"complete_{t['id']}"):
                    t["last_done"] = today.isoformat()
                    if recurrence == "yearly":
                        t["next_due"] = today.replace(year=today.year + 1).isoformat()
                        t["due_month"] = ""
                    elif recurrence == "2-yearly":
                        t["next_due"] = today.replace(year=today.year + 2).isoformat()
                        t["due_month"] = ""
                    save_data(D)
                    st.rerun()

                if c3.button("Delete", key=f"delete_tr_{t['id']}"):
                    D["training"] = [x for x in D["training"] if x["id"] != t["id"]]
                    save_data(D)
                    st.rerun()
    else:
        st.caption("No training records yet.")

    with st.expander("＋ Add training"):
        with st.form("new_training_form"):
            name = st.text_input("Training name")
            exact_known = st.checkbox("Exact due date known", value=True)
            if exact_known:
                due_date = st.date_input("Next due date", value=today)
                new_month = ""
            else:
                c1, c2 = st.columns(2)
                m = c1.selectbox("Due month", list(range(1, 13)), index=today.month - 1, format_func=lambda x: calendar.month_name[x])
                y = c2.number_input("Due year", min_value=2020, max_value=2100, value=today.year, step=1)
                due_date = None
                new_month = f"{int(y):04d}-{int(m):02d}"
            recurrence = st.selectbox("Recurrence", ["yearly", "2-yearly", "custom", "none"])
            notes = st.text_area("Notes")
            if st.form_submit_button("Add training"):
                if not name.strip():
                    st.error("Enter a training name.")
                else:
                    D["training"].append(
                        {
                            "id": f"tr{int(datetime.now().timestamp())}",
                            "name": name.strip(),
                            "last_done": "",
                            "next_due": due_date.isoformat() if exact_known and due_date else "",
                            "due_month": "" if exact_known else new_month,
                            "recurrence": recurrence,
                            "notes": notes,
                            "doc": None,
                        }
                    )
                    save_data(D)
                    st.success("Training added.")
                    st.rerun()

# -----------------------------------------------------------------------------
# PAY
# -----------------------------------------------------------------------------
elif page == "Pay":
    page_heading("Pay")
    tab1, tab2, tab3 = st.tabs(["Current", "History", "Rate"])

    p_start, p_end = current_period_for(today)
    shifts = all_shift_dates_in_range(p_start, p_end)
    normal = [s for s in shifts if not s["extra"]]
    extra = [s for s in shifts if s["extra"]]

    # Count holiday dates individually inside this pay period only.
    holiday_dates = set()
    for r in D["holiday_requests"]:
        if r.get("status") in ("approved", "taken"):
            for ds in r.get("dates", []):
                if p_start.isoformat() <= ds <= p_end.isoformat():
                    holiday_dates.add(ds)

    hol_hours = len(holiday_dates) * float(D["profile"]["paid_hours"])
    holiday_gross = sum(float(D["profile"]["paid_hours"]) * current_rate(ds) for ds in holiday_dates)
    total_paid = sum(float(s["hours"]) for s in shifts) + hol_hours
    gross = est_gross_for(shifts) + holiday_gross
    tax_ni = estimate_tax_ni(gross)
    payday = payday_for(p_end)

    with tab1:
        st.markdown(f"<div class='hero'><div class='hero-label'>Current pay period</div><div class='hero-value'>£{tax_ni['net']:.2f}</div><div class='hero-sub'>Estimated take-home · gross £{gross:.2f}</div></div>", unsafe_allow_html=True)
        st.markdown("<div class='grid2'>" + card("Period", f"{p_start.strftime('%d %b')}–{p_end.strftime('%d %b')}", str(p_end.year)) + card("Payday", payday.strftime("%d %b %Y"), f"{max(0,(payday-today).days)} days away") + "</div>", unsafe_allow_html=True)
        st.markdown("<div class='grid3'>" + card("Normal", f"{sum(s['hours'] for s in normal):.0f}h") + card("Extra", f"{sum(s['hours'] for s in extra):.0f}h") + card("Holiday", f"{hol_hours:.0f}h") + "</div>", unsafe_allow_html=True)
        st.caption("Tax and NI are estimates only and may not match payroll exactly.")

        with st.expander("Pay cycle settings"):
            new_start = st.date_input("4-week pay cycle anchor", value=date.fromisoformat(D["pay_period_start"]))
            if st.button("Update pay cycle anchor"):
                D["pay_period_start"] = new_start.isoformat()
                save_data(D)
                st.rerun()

        with st.expander("Log actual pay"):
            actual = st.number_input("Actual amount received (£)", value=0.0, min_value=0.0, step=1.0)
            if st.button("Save this pay period"):
                existing = next((p for p in D["pay_history"] if p.get("start") == p_start.isoformat()), None)
                record = {
                    "start": p_start.isoformat(),
                    "end": p_end.isoformat(),
                    "payday": payday.isoformat(),
                    "total_hours": total_paid,
                    "estimated": gross,
                    "estimated_net": tax_ni["net"],
                    "actual": actual if actual > 0 else None,
                }
                if existing:
                    existing.update(record)
                else:
                    D["pay_history"].append(record)
                save_data(D)
                st.success("Pay period saved.")
                st.rerun()

    with tab2:
        if not D["pay_history"]:
            st.caption("No past pay periods logged yet.")
        for p in reversed(D["pay_history"]):
            with st.expander(f"{fmt_short(p['start'])} – {fmt_short(p['end'])}"):
                st.write(f"Payday: **{fmt_short(p['payday'])}**")
                st.write(f"Paid hours: **{p['total_hours']:.1f}h**")
                st.write(f"Estimated gross: **£{p['estimated']:.2f}**")
                st.write(f"Estimated net: **£{p.get('estimated_net', p['estimated']):.2f}**")
                if p.get("actual") is not None:
                    diff = p["actual"] - p.get("estimated_net", p["estimated"])
                    st.write(f"Actual received: **£{p['actual']:.2f}**")
                    st.write(f"Difference: **£{diff:.2f}**")

    with tab3:
        st.markdown(f"<div class='hero'><div class='hero-label'>Current hourly rate</div><div class='hero-value'>£{current_rate(today.isoformat()):.2f}</div><div class='hero-sub'>per paid hour</div></div>", unsafe_allow_html=True)
        for r in sorted(D["rates"], key=lambda x: x["effective_from"], reverse=True):
            st.markdown(f"<div class='status-row'><div class='status-title'>£{float(r['rate']):.2f}/h</div><div class='muted'>From {fmt_short(r['effective_from'])}</div></div>", unsafe_allow_html=True)
        with st.expander("＋ Add new rate"):
            with st.form("new_rate_form"):
                eff = st.date_input("Effective from", value=today)
                val = st.number_input("Hourly rate (£)", value=float(current_rate(today.isoformat())), min_value=0.0, step=0.01)
                if st.form_submit_button("Save new rate"):
                    D["rates"].append({"effective_from": eff.isoformat(), "rate": val})
                    save_data(D)
                    st.success("Rate saved.")
                    st.rerun()

# -----------------------------------------------------------------------------
# PROFILE
# -----------------------------------------------------------------------------
elif page == "Profile":
    page_heading("Profile")
    p = D["profile"]

    st.markdown(f"<div class='hero'><div class='hero-label'>{p['role']}</div><div class='hero-value'>{p['name'] or 'Your profile'}</div><div class='hero-sub'>{p['unit']} · Unit manager: {p['manager']}{(' · ' + p.get('email','')) if p.get('email') else ''}</div></div>", unsafe_allow_html=True)

    with st.expander("Work profile", expanded=True):
        with st.form("profile_form"):
            name = st.text_input("Name", value=p["name"])
            email = st.text_input("Email", value=p.get("email", ""), placeholder="name@example.com")
            role = st.text_input("Job role", value=p["role"])
            unit = st.text_input("Unit", value=p["unit"])
            manager = st.text_input("Unit manager", value=p["manager"])
            c1, c2 = st.columns(2)
            shift_start = c1.text_input("Shift start", value=p["shift_start"])
            shift_end = c2.text_input("Shift end", value=p["shift_end"])
            c3, c4 = st.columns(2)
            shift_len = c3.number_input("Shift length (h)", value=float(p["shift_len"]), min_value=0.0, step=0.5)
            unpaid_break = c4.number_input("Unpaid break (h)", value=float(p["unpaid_break"]), min_value=0.0, step=0.5)
            c5, c6 = st.columns(2)
            paid_hours = c5.number_input("Paid hours/shift", value=float(p["paid_hours"]), min_value=0.0, step=0.5)
            shifts_per_week = c6.number_input("Shifts/week", value=float(p["shifts_per_week"]), min_value=0.0, step=1.0)
            if st.form_submit_button("Save profile"):
                p.update(
                    name=name,
                    email=email.strip(),
                    role=role,
                    unit=unit,
                    manager=manager,
                    shift_start=shift_start,
                    shift_end=shift_end,
                    shift_len=shift_len,
                    unpaid_break=unpaid_break,
                    paid_hours=paid_hours,
                    shifts_per_week=shifts_per_week,
                    paid_hours_per_week=paid_hours * shifts_per_week,
                )
                # Keep preloaded request hour totals in sync with paid hours per shift.
                for r in D["holiday_requests"]:
                    r["hours"] = holiday_hours_for_dates(r.get("dates", []))
                save_data(D)
                st.success("Profile saved.")
                st.rerun()

    with st.expander("Appearance"):
        st.info("Use the three-dot menu at the top right to choose Light or Dark. CarerMate follows that setting.")

    with st.expander("Pay cycle"):
        st.caption("Anchor date for the repeating four-week payroll cycle. Confirmed anchor: 27 Jul 2026.")
        anchor = st.date_input("Pay cycle anchor date", value=date.fromisoformat(D["pay_period_start"]), key="anchor_profile")
        if st.button("Update anchor", key="update_anchor_profile"):
            D["pay_period_start"] = anchor.isoformat()
            save_data(D)
            st.success("Pay cycle anchor updated.")
            st.rerun()

    with st.expander("Notification preferences"):
        labels = {
            "shift_tonight": "Working tonight",
            "shift_tomorrow": "Shift tomorrow",
            "holiday_start": "Holiday starting tomorrow",
            "holiday_5_days": "Holiday — 5 days before",
            "holiday_3_days": "Holiday — 3 days before",
            "holiday_pending": "Pending holiday reminder",
            "training_due": "Training due soon",
            "training_5_days": "Training — 5 days before",
            "training_3_days": "Training — 3 days before",
            "training_overdue": "Training overdue",
            "pay_period_end": "Pay period ending",
            "payday_tomorrow": "Payday tomorrow",
        }
        for key, label in labels.items():
            D["notif_settings"][key] = st.checkbox(label, value=D["notif_settings"].get(key, True), key=f"notif_{key}")
        if st.button("Save notification preferences"):
            save_data(D)
            st.success("Saved.")

    st.caption("Rota: Week A Tue/Wed/Sat/Sun ↔ Week B Tue/Wed/Thu/Fri. Week containing 18 Sep 2026 is Week A.")

selected_page = render_bottom_nav(page)
if selected_page != page:
    st.session_state.main_nav = selected_page
    st.rerun()
