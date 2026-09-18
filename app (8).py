import streamlit as st
import json
import os
import calendar
from datetime import date, datetime, timedelta
from urllib.parse import quote

# -----------------------------------------------------------------------------
# APP CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(page_title="CarerMate", page_icon="❤️", layout="centered")

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
st.markdown(
    """
<style>
:root {
  --bg:#0f1115;
  --panel:#171a20;
  --panel2:#1d2128;
  --text:#f7f4ee;
  --muted:#a7abb4;
  --accent:#22c55e;
  --accent2:#86efac;
  --green:#22c55e;
  --orange:#f59e0b;
  --red:#ef4444;
  --border:#2a2f38;
}
html, body, [data-testid="stAppViewContainer"], .stApp { background: var(--bg); color: var(--text); }
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
  width:100%; border-radius:12px; min-height:44px; border:1px solid #245337;
  background:#10251a; box-shadow:0 0 0 1px rgba(34,197,94,.18) inset; color:var(--accent2); font-weight:700;
}
.stButton button:hover, .stFormSubmitButton button:hover { border-color:var(--accent); color:white; }
[data-testid="stExpander"] { background:var(--panel); border:1px solid var(--border); border-radius:16px; }
.stTabs [data-baseweb="tab-list"] { gap:8px; }
.stTabs [data-baseweb="tab"] { border-radius:999px; background:var(--panel); padding:7px 14px; }
.stTabs [aria-selected="true"] { background:#12321f!important; color:var(--accent2)!important; }

/* App components */
.brand { display:flex; align-items:center; justify-content:space-between; margin:0 0 14px; }
.brand-name { font-size:1.08rem; font-weight:800; letter-spacing:.01em; }
.brand-pill { color:var(--accent2); background:#10251a; border:1px solid #245337; padding:5px 9px; border-radius:999px; font-size:.74rem; }
.hero { background:linear-gradient(145deg,#10251a,#171a20 58%); border:1px solid #245337; border-radius:22px; padding:20px; margin:8px 0 14px; }
.hero-label { color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; }
.hero-value { color:var(--text); font-size:2.35rem; line-height:1.05; font-weight:850; margin-top:6px; }
.hero-sub { color:var(--muted); margin-top:6px; font-size:.9rem; }
.grid2 { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin:10px 0; }
.grid3 { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; margin:10px 0; }
.card { background:var(--panel); border:1px solid var(--border); border-radius:17px; padding:14px; min-height:88px; }
.card-label { color:var(--muted); font-size:.76rem; margin-bottom:5px; }
.card-value { color:var(--text); font-size:1.25rem; font-weight:800; line-height:1.12; }
.card-sub { color:var(--muted); font-size:.75rem; margin-top:5px; }
.section-title { color:var(--text); font-weight:800; font-size:1.05rem; margin:22px 0 8px; }
.progress-shell { height:10px; background:#282c33; border-radius:99px; overflow:hidden; margin:10px 0 5px; }
.progress-fill { height:100%; background:linear-gradient(90deg,#16a34a,#4ade80); border-radius:99px; }
.status-row { background:var(--panel); border:1px solid var(--border); border-radius:15px; padding:13px 14px; margin:8px 0; }
.status-title { font-weight:750; }
.muted { color:var(--muted); }

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
.cal-day.selected { background:#12321f; border-color:var(--accent); }
.cal-legend { color:var(--muted); font-size:.76rem; margin-top:10px; line-height:1.6; }
.legend-work { color:var(--green); }
.legend-leave { color:var(--red); }
.legend-pending { color:var(--orange); }

/* Bottom navigation */
.bottom-nav { position:fixed; z-index:9999; bottom:0; left:0; right:0; background:rgba(15,17,21,.96); backdrop-filter:blur(14px); border-top:1px solid var(--border); display:grid; grid-template-columns:repeat(6,1fr); padding:7px 6px max(8px, env(safe-area-inset-bottom)); }
.bottom-nav a { text-decoration:none!important; color:#858a94!important; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:2px; font-size:.64rem; font-weight:650; min-width:0; padding:6px 1px; border-radius:12px; }
.bottom-nav a .ico { font-size:1.22rem; line-height:1; }
.bottom-nav a.active { color:var(--accent2)!important; background:#10251a; }

@media (max-width:520px) {
  .block-container { padding-left:10px; padding-right:10px; padding-top:.8rem; }
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
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# DATA
# -----------------------------------------------------------------------------
def default_data():
    return {
        "profile": {
            "name": "",
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
            "holiday_pending": True,
            "training_due": True,
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
        "approved": "🟢",
        "taken": "✅",
        "pending": "🟠",
        "declined": "🔴",
        "cancelled": "⚪",
    }
    return f"{icons.get(status, '⚪')} {status.title()}"


def page_link(page, icon, label, active):
    cls = "active" if page == active else ""
    return f'<a class="{cls}" href="?page={quote(page)}"><span class="ico">{icon}</span><span>{label}</span></a>'


def render_bottom_nav(active):
    html = "<nav class='bottom-nav'>"
    html += page_link("Home", "🏠", "Home", active)
    html += page_link("Calendar", "📅", "Calendar", active)
    html += page_link("Leave", "🌴", "Leave", active)
    html += page_link("Training", "🎓", "Training", active)
    html += page_link("Pay", "💷", "Pay", active)
    html += page_link("Profile", "👤", "Profile", active)
    html += "</nav>"
    st.markdown(html, unsafe_allow_html=True)


def render_brand(page):
    st.markdown(
        f"<div class='brand'><div class='brand-name'>CarerMate</div><div class='brand-pill'>{page}</div></div>",
        unsafe_allow_html=True,
    )


def card(label, value, sub=""):
    return f"<div class='card'><div class='card-label'>{label}</div><div class='card-value'>{value}</div><div class='card-sub'>{sub}</div></div>"


def build_notifications(today_, working_today, next_s, payday):
    nset = D["notif_settings"]
    out = []
    tomorrow = (today_ + timedelta(days=1)).isoformat()
    if nset.get("shift_tonight") and working_today:
        out.append(f"You have a shift tonight at {D['profile']['shift_start']}. Don’t forget your water and apple juice so you stay hydrated. 💧🍎")
    if nset.get("shift_tomorrow") and next_s == tomorrow:
        out.append("Your next shift is tomorrow.")
    if nset.get("holiday_start") and any(r.get("status") == "approved" and r.get("start") == tomorrow for r in D["holiday_requests"]):
        out.append("Your holiday starts tomorrow.")
    if nset.get("holiday_pending") and any(r.get("status") == "pending" for r in D["holiday_requests"]):
        out.append("You have a holiday request still pending.")
    for t in D["training"]:
        status = training_status(t)
        if nset.get("training_overdue") and status == "overdue":
            out.append(f"{t['name']} is overdue.")
        elif nset.get("training_due") and status == "due soon":
            out.append(f"{t['name']} is due soon.")
    if nset.get("payday_tomorrow") and payday.isoformat() == tomorrow:
        out.append("Your payday is tomorrow.")
    _, period_end = current_period_for(today_)
    if nset.get("pay_period_end") and 0 <= (period_end - today_).days <= 2:
        out.append("Your pay period ends this week.")
    return out


# -----------------------------------------------------------------------------
# NAVIGATION
# -----------------------------------------------------------------------------
allowed_pages = ["Home", "Calendar", "Leave", "Training", "Pay", "Profile"]
page = st.query_params.get("page", "Home")
if page not in allowed_pages:
    page = "Home"

today = date.today()
render_brand(page)

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
    payday = payday_for(p_end)
    hs = holiday_summary(today.year)
    next_train = sorted(D["training"], key=training_sort_key)[0] if D["training"] else None

    st.markdown(f"<div class='hero'><div class='hero-label'>Welcome back</div><div class='hero-value'>Hello, {name} 👋</div><div class='hero-sub'>{D['profile']['unit']} · {today.strftime('%A %d %B %Y')}</div></div>", unsafe_allow_html=True)

    status_value = "Working" if working_today else "Off today"
    next_value = fmt_short(next_s) if next_s else "—"
    st.markdown("<div class='grid2'>" + card("Today", status_value, f"{D['profile']['shift_start']}–{D['profile']['shift_end']}" if working_today else "No scheduled shift") + card("Next shift", next_value, D["profile"]["shift_start"] if next_s else "") + "</div>", unsafe_allow_html=True)

    st.markdown("<div class='grid2'>" + card("Paid hours this week", f"{sum(s['hours'] for s in week_shifts):.0f}h", f"{len(week_shifts)} shifts") + card("Est. take-home", f"£{tax_ni['net']:.2f}", f"Gross £{period_gross:.2f}") + "</div>", unsafe_allow_html=True)

    st.markdown("<div class='grid2'>" + card("Next payday", fmt_short(payday.isoformat()), f"{max(0,(payday-today).days)} days away") + card("Holiday remaining", f"{hs['confirmed_remaining']:.1f}h", f"≈ {hs['confirmed_remaining']/float(D['profile']['paid_hours']):.1f} shifts") + "</div>", unsafe_allow_html=True)

    if next_train:
        st.markdown("<div class='section-title'>Training</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='status-row'><div class='status-title'>{next_train['name']}</div><div class='muted'>{training_due_label(next_train)} · {badge(training_status(next_train))}</div></div>", unsafe_allow_html=True)

    notifications = build_notifications(today, working_today, next_s, payday)
    if notifications:
        st.markdown("<div class='section-title'>Reminders</div>", unsafe_allow_html=True)
        for n in notifications[:4]:
            st.info(n)

# -----------------------------------------------------------------------------
# CALENDAR
# -----------------------------------------------------------------------------
elif page == "Calendar":
    st.title("Calendar")

    try:
        year = int(st.query_params.get("year", today.year))
        month = int(st.query_params.get("month", today.month))
    except ValueError:
        year, month = today.year, today.month
    if month < 1 or month > 12:
        year, month = today.year, today.month

    current_first = date(year, month, 1)
    prev_last = current_first - timedelta(days=1)
    prev_y, prev_m = prev_last.year, prev_last.month
    next_first = (current_first.replace(day=28) + timedelta(days=4)).replace(day=1)
    next_y, next_m = next_first.year, next_first.month

    nav1, nav2, nav3 = st.columns([1, 2.2, 1])
    nav1.markdown(f"<a href='?page=Calendar&year={prev_y}&month={prev_m}' style='text-decoration:none;color:#86efac'>← Prev</a>", unsafe_allow_html=True)
    nav2.markdown(f"<div style='text-align:center;font-weight:800'>{current_first.strftime('%B %Y')}</div>", unsafe_allow_html=True)
    nav3.markdown(f"<div style='text-align:right'><a href='?page=Calendar&year={next_y}&month={next_m}' style='text-decoration:none;color:#86efac'>Next →</a></div>", unsafe_allow_html=True)

    grid_start = monday_of(current_first)
    cells = [grid_start + timedelta(days=i) for i in range(42)]
    selected = st.query_params.get("day", "")

    cal = "<div class='calendar-head'>" + "".join(f"<div>{d}</div>" for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]) + "</div><div class='calendar-grid'>"
    for d in cells:
        ds = d.isoformat()
        classes = ["cal-day"]
        if d.month != month:
            classes.append("out")
        if ds == today.isoformat():
            classes.append("today")
        if ds == selected:
            classes.append("selected")
        if is_holiday_date(ds):
            classes.append("holiday")
        elif is_pending_holiday_date(ds):
            classes.append("pending")
        else:
            ss = shift_status_for(ds)
            if ss and ss.get("status") in ("scheduled", "worked", "extra"):
                classes.append("work")
        href = f"?page=Calendar&year={year}&month={month}&day={ds}"
        cal += f"<a class='{' '.join(classes)}' href='{href}'>{d.day}</a>"
    cal += "</div><div class='cal-legend'><span class='legend-work'>●</span> Green = work &nbsp; <span class='legend-leave'>●</span> Red = approved/taken leave &nbsp; <span class='legend-pending'>●</span> Amber = pending leave</div>"
    st.markdown(cal, unsafe_allow_html=True)

    if selected:
        try:
            date.fromisoformat(selected)
            st.markdown("<div class='section-title'>Edit selected day</div>", unsafe_allow_html=True)
            cur = D["shift_overrides"].get(selected, {})
            current_status = cur.get("status") or (shift_status_for(selected) or {}).get("status", "off")
            options = ["scheduled", "worked", "missed", "cancelled", "extra", "off"]
            idx = options.index(current_status) if current_status in options else 0
            status = st.selectbox("Shift status", options, index=idx)
            hours = st.number_input("Paid hours", value=float(cur.get("hours", D["profile"]["paid_hours"])), min_value=0.0, step=0.5)
            notes = st.text_area("Notes", value=cur.get("notes", ""))
            if st.button("Save day"):
                if status == "off":
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
    st.title("Leave")
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
    st.title("Training")

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
    st.title("Pay")
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
    st.title("Profile")
    p = D["profile"]

    st.markdown(f"<div class='hero'><div class='hero-label'>{p['role']}</div><div class='hero-value'>{p['name'] or 'Your profile'}</div><div class='hero-sub'>{p['unit']} · Unit manager: {p['manager']}</div></div>", unsafe_allow_html=True)

    with st.expander("Work profile", expanded=True):
        with st.form("profile_form"):
            name = st.text_input("Name", value=p["name"])
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
            "holiday_pending": "Pending holiday reminder",
            "training_due": "Training due soon",
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

render_bottom_nav(page)
