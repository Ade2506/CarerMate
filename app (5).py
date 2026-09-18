import streamlit as st
import json, os, base64, secrets, urllib.request, urllib.error
from datetime import date, datetime, timedelta

# ----------------------------------------------------------------------
# CONFIG / CONSTANTS
# ----------------------------------------------------------------------
st.set_page_config(page_title="Night Shift", page_icon="🌙", layout="centered")


# ----------------------------------------------------------------------
# APP THEME / MOBILE-FIRST STYLING
# ----------------------------------------------------------------------
st.markdown("""
<style>
:root {
  --bg: #0f1117;
  --surface: #1a1d26;
  --surface-2: #202430;
  --border: #303543;
  --text: #f4f5f7;
  --muted: #969cad;
  --accent: #f2aa35;
  --accent-soft: rgba(242,170,53,.16);
  --success: #4ec38a;
  --danger: #ef6b73;
}
html, body, [data-testid="stAppViewContainer"], .stApp {
  background: var(--bg) !important;
  color: var(--text) !important;
}
[data-testid="stHeader"], #MainMenu, footer, [data-testid="stToolbar"] {
  display: none !important;
}
[data-testid="stSidebar"] { display: none !important; }
.block-container {
  max-width: 760px !important;
  padding: 2rem 1.35rem 7.5rem !important;
}
h1, h2, h3, h4, h5, h6, p, label, span { color: var(--text); }
h1 { font-size: 2.15rem !important; line-height: 1.08 !important; margin-bottom: .25rem !important; }
h2 { font-size: 1.45rem !important; margin-top: 1.45rem !important; }
h3 { font-size: 1.05rem !important; color: var(--muted) !important; }
[data-testid="stCaptionContainer"] { color: var(--muted) !important; }

/* Fixed mobile bottom navigation */
div[data-testid="stRadio"] {
  position: fixed !important;
  left: 0 !important; right: 0 !important; bottom: 0 !important;
  z-index: 10000 !important;
  background: rgba(23,26,34,.98) !important;
  border-top: 1px solid var(--border) !important;
  padding: .55rem .55rem max(.6rem, env(safe-area-inset-bottom)) !important;
  box-shadow: 0 -10px 30px rgba(0,0,0,.24) !important;
}
div[data-testid="stRadio"] > div { width: 100% !important; }
div[data-testid="stRadio"] [role="radiogroup"] {
  display: grid !important; grid-template-columns: repeat(6, 1fr) !important; gap: .15rem !important;
}
div[data-testid="stRadio"] label {
  margin: 0 !important; padding: .42rem .2rem !important; border-radius: .7rem !important;
  justify-content: center !important; text-align: center !important; min-width: 0 !important;
}
div[data-testid="stRadio"] label > div:first-child { display: none !important; }
div[data-testid="stRadio"] label p {
  font-size: .76rem !important; color: var(--muted) !important; text-align: center !important; white-space: nowrap !important;
}
div[data-testid="stRadio"] label:has(input:checked) { background: var(--accent-soft) !important; }
div[data-testid="stRadio"] label:has(input:checked) p { color: var(--accent) !important; font-weight: 700 !important; }

/* Cards / metrics */
[data-testid="stMetric"], [data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 1.25rem !important;
}
[data-testid="stMetric"] { padding: 1rem 1.05rem !important; }
[data-testid="stMetricLabel"] p { color: var(--muted) !important; font-size: .9rem !important; }
[data-testid="stMetricValue"] { color: var(--text) !important; font-weight: 800 !important; }

/* Inputs */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] textarea,
[data-testid="stDateInput"] input, [data-testid="stNumberInput"] input, [data-testid="stTextInput"] input {
  background: var(--surface-2) !important;
  border-color: var(--border) !important;
  color: var(--text) !important;
  border-radius: .9rem !important;
}
[data-baseweb="select"] * { color: var(--text) !important; }
[data-testid="stFileUploader"] section {
  background: var(--surface-2) !important; border-color: var(--border) !important; border-radius: 1rem !important;
}

/* Buttons */
.stButton > button, [data-testid="stFormSubmitButton"] button, [data-testid="stDownloadButton"] button {
  border-radius: .9rem !important;
  border: 1px solid var(--border) !important;
  background: var(--surface-2) !important;
  color: var(--text) !important;
  min-height: 2.8rem !important;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
  border-color: var(--accent) !important; color: var(--accent) !important;
}
button[kind="primary"] { background: var(--accent) !important; color: #141414 !important; border-color: var(--accent) !important; font-weight: 800 !important; }

/* Tabs */
[data-baseweb="tab-list"] { gap: .5rem !important; }
[data-baseweb="tab"] {
  background: var(--surface-2) !important; border: 1px solid var(--border) !important;
  border-radius: 999px !important; padding: .25rem .85rem !important;
}
[aria-selected="true"][data-baseweb="tab"] { background: var(--accent) !important; }
[aria-selected="true"][data-baseweb="tab"] p { color: #151515 !important; font-weight: 800 !important; }
[data-baseweb="tab-highlight"] { display: none !important; }

/* Expanders / alerts */
[data-testid="stExpander"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 1rem !important; }
[data-testid="stAlert"] { border-radius: 1rem !important; border: 1px solid var(--border) !important; }
hr { border-color: var(--border) !important; }

.app-card {
  background: var(--surface); border: 1px solid var(--border); border-radius: 1.25rem;
  padding: 1.05rem 1.1rem; margin: .75rem 0;
}
.app-card .kicker { color: var(--muted); font-size: .88rem; margin-bottom: .7rem; }
.app-row { display:flex; justify-content:space-between; gap:1rem; padding:.55rem 0; border-bottom:1px solid var(--border); }
.app-row:last-child { border-bottom:0; }
.app-row .label { color: var(--muted); }
.app-row .value { color: var(--text); font-weight:650; text-align:right; }
.hero { margin-bottom: 1.25rem; }
.hero .eyebrow { color: var(--muted); font-size: .96rem; }
.hero .title { color: var(--text); font-size: 2rem; font-weight: 800; line-height: 1.08; }
.section-title { color: var(--text); font-size: 1.45rem; font-weight: 800; margin: 1.45rem 0 .7rem; }
.accent { color: var(--accent); }

@media (max-width: 520px) {
  .block-container { padding: 1.4rem 1rem 7.2rem !important; }
  h1 { font-size: 1.9rem !important; }
  div[data-testid="stRadio"] label p { font-size: .68rem !important; }
}
</style>
""", unsafe_allow_html=True)

APP_DIR = os.path.dirname(__file__)
# Set CARER_DATA_DIR to a persistent mounted directory when deploying online.
# If it is not set, data is stored beside app.py (fine for local use).
DATA_DIR = os.environ.get("CARER_DATA_DIR", APP_DIR)
os.makedirs(DATA_DIR, exist_ok=True)
DATA_FILE = os.path.join(DATA_DIR, "carer_data.json")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ANCHOR_DATE = date(2026, 9, 18)          # this week is Week A
ANCHOR_MONDAY = ANCHOR_DATE - timedelta(days=ANCHOR_DATE.weekday())
WEEK_A_DAYS = {1, 2, 5, 6}               # Mon=0 -> Tue, Wed, Sat, Sun
WEEK_B_DAYS = {1, 2, 3, 4}               # Tue, Wed, Thu, Fri
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def default_data():
    return {
        "profile": {
            "name": "", "role": "Carer / Caregiver", "unit": "Earlswood",
            "manager": "Sham", "shift_start": "20:00", "shift_end": "08:00",
            "shift_len": 12, "unpaid_break": 1, "paid_hours": 11,
            "shifts_per_week": 4, "paid_hours_per_week": 44,
        },
        "rates": [{"effective_from": "2026-01-01", "rate": 12.82, "estimated": True}],
        "shift_overrides": {},           # date -> {status, hours, notes}
        "holiday_entitlement": {"2026": 246.4, "2027": 246.4},
        "holiday_requests": [],          # {id,start,end,dates,hours,requested,notes,status,doc}
        "training": [
            {"id": "t1", "name": "Yearly Updates Training", "last_done": "",
             "next_due": "2027-03-09", "recurrence": "yearly", "notes": ""},
            {"id": "t2", "name": "DMI Moving and Handling Updates", "last_done": "",
             "next_due": "2027-03-02", "recurrence": "yearly", "notes": ""},
            {"id": "t3", "name": "First Aid Training", "last_done": "",
             "next_due": "", "due_month": "2027-02", "recurrence": "custom", "notes": "Exact date TBC"},
        ],
        "pay_period_start": "",  # must be set to the employer's actual 4-week cycle start
        "pay_history": [],
        "payday_overrides": {},
        "notif_settings": {
            "shift_tonight": True, "shift_tomorrow": True, "holiday_start": True,
            "holiday_pending": True, "training_due": True, "training_overdue": True,
            "pay_period_end": True, "payday_tomorrow": True,
            "push_enabled": False,
            "ntfy_topic": "",
            "shift_reminder_hour": 16,
            "shift_reminder_message": "You have a shift today 🌙 Your shift starts at 8:00 PM at Earlswood. Don’t forget your water and apple juice so you stay hydrated. 💧🍎",
        },
        "notification_log": {},
        "known_holiday_dates": {
            "2026": ["2026-06-23", "2026-06-24", "2026-06-25", "2026-06-26",
                     "2026-12-08", "2026-12-09", "2026-12-12", "2026-12-13",
                     "2026-12-15", "2026-12-16", "2026-12-17", "2026-12-18"],
            "2027": ["2027-01-28", "2027-01-29", "2027-02-11", "2027-02-12",
                     "2027-02-25", "2027-02-26", "2027-03-16", "2027-03-17",
                     "2027-03-20", "2027-03-21"],
        },
        "seeded": False,
    }


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            d = json.load(f)
        base = default_data()
        base.update(d)
        # Lightweight migration from the first prototype.
        base.setdefault("payday_overrides", {})
        base.setdefault("notification_log", {})
        base.setdefault("notif_settings", {})
        notif_defaults = default_data()["notif_settings"]
        for k, v in notif_defaults.items():
            base["notif_settings"].setdefault(k, v)
        for r in base.get("rates", []):
            if r.get("rate") == 12.77 and "estimated" not in r:
                r["rate"] = 12.82
                r["estimated"] = True
        for t in base.get("training", []):
            if t.get("name") == "First Aid Training" and t.get("notes") == "Exact date TBC":
                if t.get("next_due") == "2027-02-28":
                    t["next_due"] = ""
                    t["due_month"] = "2027-02"
        return base
    return default_data()


def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)


if "D" not in st.session_state:
    st.session_state.D = load_data()
D = st.session_state.D


def seed_known_holidays():
    if D.get("seeded"):
        return
    for yr, dates in D["known_holiday_dates"].items():
        dates = sorted(dates)
        blocks, cur = [], []
        for ds in dates:
            if not cur:
                cur = [ds]
            else:
                prev = date.fromisoformat(cur[-1])
                if (date.fromisoformat(ds) - prev).days <= 3:
                    cur.append(ds)
                else:
                    blocks.append(cur)
                    cur = [ds]
        if cur:
            blocks.append(cur)
        for b in blocks:
            # Seed only what we actually know:
            # June 2026 has already been taken; December 2026 is approved/booked;
            # 2027 dates were provided without an approval status, so keep them pending.
            if b[0].startswith("2026-06"):
                status = "taken"
            elif b[0].startswith("2026-12"):
                status = "approved"
            else:
                status = "pending"
            D["holiday_requests"].append({
                "id": "seed" + b[0], "start": b[0], "end": b[-1], "dates": b,
                "hours": len(b) * D["profile"]["paid_hours"], "requested": b[0],
                "notes": "", "status": status, "doc": None,
            })
    D["seeded"] = True
    save_data(D)


seed_known_holidays()

# ----------------------------------------------------------------------
# CORE LOGIC
# ----------------------------------------------------------------------

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
    rate = rates[0]["rate"]
    for r in rates:
        if r["effective_from"] <= date_str:
            rate = r["rate"]
        else:
            break
    return rate


def is_holiday_date(ds):
    return any(r["status"] in ("approved", "taken") and ds in r["dates"]
               for r in D["holiday_requests"])


def is_pending_holiday_date(ds):
    return any(r["status"] == "pending" and ds in r["dates"] for r in D["holiday_requests"])


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
        counts, extra = False, False
        if hol:
            pass
        elif ov:
            if ov["status"] in ("worked", "extra"):
                counts = True
            if ov["status"] == "extra":
                extra = True
        elif rota:
            counts = True
        if counts:
            hours = ov.get("hours", D["profile"]["paid_hours"]) if ov else D["profile"]["paid_hours"]
            out.append({"date": ds, "hours": hours, "extra": extra})
        d += timedelta(days=1)
    return out


def current_period_for(ref_date):
    start_str = D.get("pay_period_start", "").strip()
    if not start_str:
        return None, None
    start = date.fromisoformat(start_str)
    end = start + timedelta(days=27)
    while end < ref_date:
        start += timedelta(days=28)
        end = start + timedelta(days=27)
    while start > ref_date:
        start -= timedelta(days=28)
        end = start + timedelta(days=27)
    return start, end


def payday_for(period_end):
    override = D.get("payday_overrides", {}).get(period_end.isoformat())
    if override:
        return date.fromisoformat(override)
    next_week_mon = monday_of(period_end) + timedelta(days=7)
    # Default to Friday, the usual last working day of the following week.
    # This can be manually overridden in the Pay tab for bank holidays/payroll changes.
    return next_week_mon + timedelta(days=4)


def est_gross_for(shifts):
    return sum(s["hours"] * current_rate(s["date"]) for s in shifts)


def estimate_tax_ni(period_gross, periods_per_year=13):
    annual_gross = period_gross * periods_per_year
    PA, BASIC_BAND = 12570, 37700
    taxable = max(0, annual_gross - PA)
    basic_portion = min(taxable, BASIC_BAND)
    higher_portion = max(0, taxable - BASIC_BAND)
    annual_tax = basic_portion * 0.2 + higher_portion * 0.4
    NI_PT, NI_UEL = 12570, 50270
    niable = max(0, annual_gross - NI_PT)
    ni_basic = min(niable, NI_UEL - NI_PT)
    ni_higher = max(0, niable - (NI_UEL - NI_PT))
    annual_ni = ni_basic * 0.08 + ni_higher * 0.02
    return {
        "tax": annual_tax / periods_per_year,
        "ni": annual_ni / periods_per_year,
        "net": (annual_gross - annual_tax - annual_ni) / periods_per_year,
    }


def holiday_summary(year):
    ent = D["holiday_entitlement"].get(str(year), 0)
    reqs = [r for r in D["holiday_requests"] if any(dd.startswith(str(year)) for dd in r["dates"])]
    taken = sum(r["hours"] for r in reqs if r["status"] == "taken")
    approved = sum(r["hours"] for r in reqs if r["status"] == "approved")
    pending = sum(r["hours"] for r in reqs if r["status"] == "pending")
    confirmed_remaining = ent - taken - approved
    potential_remaining = confirmed_remaining - pending
    return dict(ent=ent, taken=taken, approved=approved, pending=pending,
                confirmed_remaining=confirmed_remaining, potential_remaining=potential_remaining)


def holiday_hours_in_range(start_d, end_d):
    total = 0.0
    hours_per_shift = float(D["profile"]["paid_hours"])
    for r in D["holiday_requests"]:
        if r["status"] not in ("approved", "taken"):
            continue
        for ds in r.get("dates", []):
            dd = date.fromisoformat(ds)
            if start_d <= dd <= end_d:
                total += hours_per_shift
    return total


def training_sort_key(t):
    if t.get("next_due"):
        return t["next_due"]
    if t.get("due_month"):
        return t["due_month"] + "-99"
    return "9999-99-99"


def training_status(t):
    if t.get("next_due"):
        due = date.fromisoformat(t["next_due"])
    elif t.get("due_month"):
        year, month = map(int, t["due_month"].split("-"))
        if month == 12:
            due = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            due = date(year, month + 1, 1) - timedelta(days=1)
    else:
        return "upcoming"
    days = (due - date.today()).days
    if days < 0:
        return "overdue"
    if days <= 30:
        return "due soon"
    return "upcoming"


def training_due_label(t):
    if t.get("next_due"):
        return fmt_short(t["next_due"])
    if t.get("due_month"):
        year, month = map(int, t["due_month"].split("-"))
        return date(year, month, 1).strftime("%B %Y") + " – date TBC"
    return "TBC"


def next_shift_from(ref_date):
    d = ref_date
    for _ in range(60):
        ds = d.isoformat()
        if not is_holiday_date(ds):
            st_ = shift_status_for(ds)
            if st_ and st_["status"] in ("scheduled", "worked", "extra"):
                return ds
        d += timedelta(days=1)
    return None


def build_notifications(today, working_today, next_s, payday, hs):
    N = D["notif_settings"]
    out = []
    tomorrow = (today + timedelta(days=1)).isoformat()
    if N["shift_tonight"] and working_today:
        out.append(f"You are working tonight at {D['profile']['shift_start']}.")
    if N["shift_tomorrow"] and next_s == tomorrow:
        out.append("Your next shift is tomorrow.")
    if N["holiday_start"] and any(r["status"] == "approved" and r["start"] == tomorrow for r in D["holiday_requests"]):
        out.append("Your holiday starts tomorrow.")
    if N["holiday_pending"] and any(r["status"] == "pending" for r in D["holiday_requests"]):
        out.append("You have a holiday request still pending.")
    for t in D["training"]:
        s = training_status(t)
        if N["training_overdue"] and s == "overdue":
            out.append(f"{t['name']} is overdue.")
        elif N["training_due"] and s == "due soon":
            out.append(f"{t['name']} is due soon.")
    if N["payday_tomorrow"] and payday and payday.isoformat() == tomorrow:
        out.append("Your payday is tomorrow.")
    _, end = current_period_for(today)
    if N["pay_period_end"] and end and 0 <= (end - today).days <= 2:
        out.append("Your pay period ends this week.")
    return out




def send_ntfy_notification(title, message):
    """Send a phone/browser push through ntfy. Returns (success, detail)."""
    cfg = D.get("notif_settings", {})
    topic = cfg.get("ntfy_topic", "").strip()
    if not topic:
        return False, "No ntfy topic configured."
    url = f"https://ntfy.sh/{topic}"
    req = urllib.request.Request(
        url,
        data=message.encode("utf-8"),
        method="POST",
        headers={
            "Title": title.encode("utf-8", "ignore").decode("latin-1", "ignore"),
            "Tags": "crescent_moon,water",
            "Priority": "default",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300, f"HTTP {resp.status}"
    except Exception as e:
        return False, str(e)


def push_once(key, title, message):
    """Send at most once for a unique event key."""
    if D.get("notification_log", {}).get(key):
        return False
    ok, _ = send_ntfy_notification(title, message)
    if ok:
        D.setdefault("notification_log", {})[key] = datetime.now().isoformat(timespec="seconds")
        # Keep the log small: retain latest 200 entries.
        if len(D["notification_log"]) > 200:
            items = sorted(D["notification_log"].items(), key=lambda x: x[1], reverse=True)[:200]
            D["notification_log"] = dict(items)
        save_data(D)
        return True
    return False


def dispatch_push_notifications(now=None):
    """Send any notifications that are due when the app is running.

    For truly automatic background delivery, run notifier.py on an hourly scheduler.
    """
    cfg = D.get("notif_settings", {})
    if not cfg.get("push_enabled") or not cfg.get("ntfy_topic", "").strip():
        return
    now = now or datetime.now()
    today_ = now.date()
    ds = today_.isoformat()
    working_today_ = (not is_holiday_date(ds)) and bool(
        shift_status_for(ds) and shift_status_for(ds)["status"] in ("scheduled", "worked", "extra")
    )
    reminder_hour = int(cfg.get("shift_reminder_hour", 16))
    if cfg.get("shift_tonight") and working_today_ and now.hour >= reminder_hour:
        msg = cfg.get("shift_reminder_message") or (
            f"You have a shift today. Your shift starts at {D['profile']['shift_start']} at {D['profile']['unit']}."
        )
        push_once(f"shift_today:{ds}", "Shift reminder 🌙", msg)

    tomorrow = today_ + timedelta(days=1)
    tomorrow_ds = tomorrow.isoformat()
    next_s = next_shift_from(today_)
    if cfg.get("shift_tomorrow") and next_s == tomorrow_ds and now.hour >= 18:
        push_once(
            f"shift_tomorrow:{tomorrow_ds}",
            "Shift tomorrow 🌙",
            f"You’re working tomorrow at {D['profile']['shift_start']} in {D['profile']['unit']}. Get your things ready for the night.",
        )

    if cfg.get("holiday_start"):
        for r in D.get("holiday_requests", []):
            if r.get("status") == "approved" and r.get("start") == tomorrow_ds:
                push_once(f"holiday:{r['id']}:{tomorrow_ds}", "Holiday starts tomorrow 🎉", "Your approved holiday starts tomorrow.")

    if cfg.get("training_due") or cfg.get("training_overdue"):
        for t in D.get("training", []):
            status = training_status(t)
            if status == "due soon" and cfg.get("training_due"):
                push_once(f"training_due:{t['id']}:{today_.isoformat()}", "Training due soon", f"{t['name']} is due soon: {training_due_label(t)}.")
            elif status == "overdue" and cfg.get("training_overdue"):
                push_once(f"training_overdue:{t['id']}:{today_.isoformat()}", "Training overdue", f"{t['name']} is overdue.")

    p_start, p_end = current_period_for(today_)
    if p_end:
        payday = payday_for(p_end)
        if cfg.get("payday_tomorrow") and payday == tomorrow:
            push_once(f"payday:{payday.isoformat()}", "Payday tomorrow 💷", "Your expected payday is tomorrow.")
        if cfg.get("pay_period_end") and 0 <= (p_end - today_).days <= 2:
            push_once(f"payperiod:{p_end.isoformat()}:{today_.isoformat()}", "Pay period ending", "Your current 4-week pay period ends this week.")


def save_uploaded_file(uploaded_file, prefix):
    if uploaded_file is None:
        return None
    fname = f"{prefix}_{uploaded_file.name}"
    path = os.path.join(UPLOAD_DIR, fname)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


def fmt(ds):
    return date.fromisoformat(ds).strftime("%a %d %b %Y")


def fmt_short(ds):
    return date.fromisoformat(ds).strftime("%d %b %Y")


def badge(status):
    colors = {"overdue": "🔴", "due soon": "🟠", "upcoming": "⚪",
              "approved": "🟢", "taken": "🟢", "pending": "🟠",
              "declined": "🔴", "cancelled": "⚪"}
    return f"{colors.get(status, '⚪')} {status}"


# ----------------------------------------------------------------------
# MOBILE NAV
# ----------------------------------------------------------------------
page = st.radio(
    "Navigation",
    ["Home", "Calendar", "Leave", "Training", "Pay", "Profile"],
    horizontal=True,
    label_visibility="collapsed",
    key="main_nav",
)

today = date.today()
dispatch_push_notifications()

# ----------------------------------------------------------------------
# HOME
# ----------------------------------------------------------------------
if page == "Home":
    name = D["profile"]["name"] or "there"
    hour = datetime.now().hour
    greet = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    st.title(f"{greet}, {name}")
    st.caption(f"{D['profile']['unit']} · {today.strftime('%A %d %B %Y')}")

    today_str = today.isoformat()
    working_today = (not is_holiday_date(today_str)) and bool(
        shift_status_for(today_str) and shift_status_for(today_str)["status"] in ("scheduled", "worked", "extra")
    )
    next_s = next_shift_from(today + timedelta(days=1 if working_today else 0))

    week_start = monday_of(today)
    week_end = week_start + timedelta(days=6)
    week_shifts = all_shift_dates_in_range(week_start, week_end)

    p_start, p_end = current_period_for(today)
    if p_start and p_end:
        period_shifts = all_shift_dates_in_range(p_start, p_end)
        period_holiday_hours = holiday_hours_in_range(p_start, p_end)
        period_gross = est_gross_for(period_shifts) + period_holiday_hours * current_rate(p_end.isoformat())
        tax_ni = estimate_tax_ni(period_gross)
        payday = payday_for(p_end)
    else:
        period_shifts = []
        period_gross = 0.0
        tax_ni = {"tax": 0.0, "ni": 0.0, "net": 0.0}
        payday = None
    hs = holiday_summary(today.year)
    next_train = sorted(D["training"], key=training_sort_key)[0] if D["training"] else None
    notifs = build_notifications(today, working_today, next_s, payday, hs)


    st.markdown(
        f"""<div class="hero"><div class="title">{greet}, {name}</div>
        <div class="eyebrow">{D['profile']['unit']} · {today.strftime('%A %d %B %Y')}</div></div>""",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    c1.metric("Working today", "Yes" if working_today else "No")
    c2.metric("Shifts this week", len(week_shifts))

    if next_s:
        st.markdown(
            f"""<div class="app-card"><div class="kicker">Next shift</div>
            <div class="app-row"><span class="label">Date</span><span class="value">{fmt(next_s)}</span></div>
            <div class="app-row"><span class="label">Time</span><span class="value">{D['profile']['shift_start']} – {D['profile']['shift_end']}</span></div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("No upcoming shift found.")

    c3, c4 = st.columns(2)
    c3.metric("Paid hours this week", f"{sum(s['hours'] for s in week_shifts):.0f}h")
    c4.metric("Est. take-home this period", f"£{tax_ni['net']:.2f}" if p_start else "Set pay cycle")

    if payday:
        pay_html = f"<div class='app-row'><span class='label'>Next payday</span><span class='value'>{fmt_short(payday.isoformat())}</span></div><div class='app-row'><span class='label'>Countdown</span><span class='value'>{(payday-today).days} days</span></div>"
    else:
        pay_html = "<div class='app-row'><span class='label'>Next payday</span><span class='value'>Set pay cycle</span></div>"
    st.markdown(f"<div class='section-title'>Payday</div><div class='app-card'>{pay_html}</div>", unsafe_allow_html=True)

    next_leave = None
    for h in D.get('holidays', []):
        if h.get('status') == 'approved':
            future = [d for d in h.get('dates', []) if d >= today.isoformat()]
            if future:
                cand = min(future)
                if next_leave is None or cand < next_leave:
                    next_leave = cand
    leave_html = f"<div class='app-row'><span class='label'>Remaining (confirmed)</span><span class='value'>{hs['confirmed_remaining']:.1f}h</span></div>"
    leave_html += f"<div class='app-row'><span class='label'>Next approved leave</span><span class='value'>{fmt_short(next_leave) if next_leave else 'None booked'}</span></div>"
    leave_html += f"<div class='app-row'><span class='label'>Pending requests</span><span class='value'>{sum(1 for h in D.get('holidays', []) if h.get('status')=='pending')}</span></div>"
    st.markdown(f"<div class='section-title'>Holiday</div><div class='app-card'>{leave_html}</div>", unsafe_allow_html=True)

    if next_train:
        train_html = f"<div class='app-row'><span class='label'>Next due</span><span class='value'>{next_train['name']}</span></div><div class='app-row'><span class='label'>When</span><span class='value'>{training_due_label(next_train)}</span></div>"
        st.markdown(f"<div class='section-title'>Training</div><div class='app-card'>{train_html}</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'>Notifications</div>", unsafe_allow_html=True)
    if notifs:
        for n in notifs:
            st.info(n)
    else:
        st.caption("Nothing due right now.")

# ----------------------------------------------------------------------
# CALENDAR
# ----------------------------------------------------------------------
elif page == "Calendar":
    st.title("Calendar")
    colA, colB = st.columns(2)
    year = colA.number_input("Year", value=today.year, step=1)
    month = colB.number_input("Month", value=today.month, min_value=1, max_value=12, step=1)

    first_day = date(int(year), int(month), 1)
    grid_start = monday_of(first_day)
    cells = [grid_start + timedelta(days=i) for i in range(42)]

    st.write(" | ".join(DAY_NAMES))
    for w in range(6):
        cols = st.columns(7)
        for i in range(7):
            d = cells[w * 7 + i]
            ds = d.isoformat()
            in_month = d.month == int(month)
            hol = is_holiday_date(ds)
            pend = is_pending_holiday_date(ds)
            st_ = shift_status_for(ds)
            work = (not hol) and st_ and st_["status"] in ("scheduled", "worked", "extra")
            label = str(d.day)
            if not in_month:
                label = f"·{label}·"
            if hol:
                label = f"🟢{label}"
            elif work:
                label = f"🟡{label}"
            elif pend:
                label = f"🟠{label}"
            if cols[i].button(label, key=f"cal_{ds}"):
                st.session_state.selected_day = ds
    st.caption("🟡 Working · 🟢 Holiday · 🟠 Pending holiday")

    sel = st.session_state.get("selected_day")
    if sel:
        st.divider()
        st.subheader(f"Edit {fmt(sel)}")
        cur = D["shift_overrides"].get(sel, {})
        cur_status = cur.get("status", shift_status_for(sel)["status"] if shift_status_for(sel) else "off")
        options = ["scheduled", "worked", "missed", "cancelled", "extra"]
        idx = options.index(cur_status) if cur_status in options else 0
        status = st.selectbox("Shift status", options, index=idx, key="day_status")
        hours = st.number_input("Paid hours", value=float(cur.get("hours", D["profile"]["paid_hours"])), key="day_hours")
        notes = st.text_area("Notes", value=cur.get("notes", ""), key="day_notes")
        if st.button("Save day"):
            D["shift_overrides"][sel] = {"status": status, "hours": hours, "notes": notes}
            save_data(D)
            st.success("Saved.")
            st.rerun()

    st.divider()
    st.subheader("Add an extra shift")
    with st.form("extra_shift_form"):
        ex_date = st.date_input("Date", value=today)
        ex_hours = st.number_input("Paid hours", value=float(D["profile"]["paid_hours"]))
        ex_notes = st.text_area("Notes", value="")
        if st.form_submit_button("Add shift"):
            D["shift_overrides"][ex_date.isoformat()] = {"status": "extra", "hours": ex_hours, "notes": ex_notes}
            save_data(D)
            st.success("Extra shift added.")
            st.rerun()

# ----------------------------------------------------------------------
# LEAVE
# ----------------------------------------------------------------------
elif page == "Leave":
    st.title("Leave")
    tab1, tab2 = st.tabs(["Overview", "Requests"])

    with tab1:
        yr = today.year
        hs = holiday_summary(yr)
        st.write(f"**{yr} entitlement**")
        st.write(f"Total entitlement: {hs['ent']:.1f}h")
        st.write(f"Taken: {hs['taken']:.1f}h")
        st.write(f"Approved (future): {hs['approved']:.1f}h")
        st.write(f"Pending: {hs['pending']:.1f}h")
        st.write(f"Confirmed remaining: **{hs['confirmed_remaining']:.1f}h**")
        st.write(f"Potential remaining (if pending approved): {hs['potential_remaining']:.1f}h")
        st.write(f"≈ shifts remaining: {hs['confirmed_remaining'] / D['profile']['paid_hours']:.1f}")

        new_ent = st.number_input(f"Edit entitlement for {yr} (hours)",
                                   value=float(D["holiday_entitlement"].get(str(yr), 0)))
        if st.button("Update entitlement"):
            D["holiday_entitlement"][str(yr)] = new_ent
            save_data(D)
            st.rerun()

    with tab2:
        reqs = sorted(D["holiday_requests"], key=lambda r: r["start"], reverse=True)
        for r in reqs:
            with st.expander(f"{fmt(r['start'])} – {fmt(r['end'])} · {badge(r['status'])}"):
                st.write(f"Hours: {r['hours']}h")
                st.write(f"Notes: {r.get('notes') or '—'}")
                new_status = st.selectbox("Status", ["pending", "approved", "declined", "cancelled", "taken"],
                                           index=["pending", "approved", "declined", "cancelled", "taken"].index(r["status"]),
                                           key=f"status_{r['id']}")
                doc = st.file_uploader("Upload approval evidence", key=f"doc_{r['id']}", type=["png", "jpg", "jpeg", "pdf"])
                cols = st.columns(2)
                if cols[0].button("Save", key=f"save_{r['id']}"):
                    r["status"] = new_status
                    if doc:
                        r["doc"] = save_uploaded_file(doc, r["id"])
                    save_data(D)
                    st.rerun()
                if cols[1].button("Delete", key=f"del_{r['id']}"):
                    D["holiday_requests"] = [x for x in D["holiday_requests"] if x["id"] != r["id"]]
                    save_data(D)
                    st.rerun()

        st.divider()
        st.subheader("New holiday request")
        start = st.date_input("Start date", value=today, key="leave_start")
        end = st.date_input("End date", value=today, key="leave_end")
        if end < start:
            st.error("End date cannot be before start date.")
            candidate_dates = []
        else:
            candidate_dates = []
            d = start
            while d <= end:
                # Holiday entitlement is consumed only by scheduled rota shifts
                # (or an explicitly added shift) that the user selects.
                ds = d.isoformat()
                ov = D["shift_overrides"].get(ds)
                if is_rota_work_day(d) or (ov and ov.get("status") == "extra"):
                    candidate_dates.append(ds)
                d += timedelta(days=1)

        selected_dates = st.multiselect(
            "Select the shifts this holiday covers",
            options=candidate_dates,
            default=candidate_dates,
            format_func=lambda ds: fmt(ds),
            help="Only selected scheduled shifts use holiday entitlement."
        )
        holiday_hours = len(selected_dates) * D["profile"]["paid_hours"]
        st.caption(f"Holiday hours to use: {holiday_hours:.1f}h")

        with st.form("new_leave_form"):
            notes = st.text_area("Notes")
            status = st.selectbox("Status", ["pending", "approved", "declined", "cancelled", "taken"])
            if st.form_submit_button("Create request"):
                if end < start:
                    st.error("Please fix the date range first.")
                elif not selected_dates:
                    st.error("Select at least one shift date for this holiday request.")
                else:
                    D["holiday_requests"].append({
                        "id": f"h{int(datetime.now().timestamp())}", "start": start.isoformat(),
                        "end": end.isoformat(), "dates": selected_dates,
                        "hours": len(selected_dates) * D["profile"]["paid_hours"],
                        "requested": today.isoformat(), "notes": notes, "status": status, "doc": None,
                    })
                    save_data(D)
                    st.success("Holiday request created.")
                    st.rerun()

# ----------------------------------------------------------------------
# TRAINING
# ----------------------------------------------------------------------
elif page == "Training":
    st.title("Training")
    for t in sorted(D["training"], key=training_sort_key):
        with st.expander(f"{t['name']} · {badge(training_status(t))}"):
            st.write(f"Next due: {training_due_label(t)}")
            st.write(f"Recurrence: {t['recurrence']}")
            st.write(f"Notes: {t.get('notes') or '—'}")
            exact_known = st.checkbox("Exact due date known", value=bool(t.get("next_due")), key=f"known_{t['id']}")
            new_next = None
            due_month_value = t.get("due_month", "")
            if exact_known:
                new_next = st.date_input("Update next due date",
                                          value=date.fromisoformat(t["next_due"]) if t.get("next_due") else today,
                                          key=f"due_{t['id']}")
            else:
                due_month_value = st.text_input("Due month (YYYY-MM)", value=due_month_value,
                                                key=f"month_{t['id']}", help="Use this when the month is known but the exact date is TBC.")
            doc = st.file_uploader("Upload certificate", key=f"cert_{t['id']}", type=["png", "jpg", "jpeg", "pdf"])
            cols = st.columns(3)
            if cols[0].button("Save due date", key=f"savedue_{t['id']}"):
                if exact_known and new_next:
                    t["next_due"] = new_next.isoformat()
                    t["due_month"] = ""
                else:
                    t["next_due"] = ""
                    t["due_month"] = due_month_value.strip()
                if doc:
                    t["doc"] = save_uploaded_file(doc, t["id"])
                save_data(D)
                st.rerun()
            if cols[1].button("Mark completed & roll forward", key=f"complete_{t['id']}"):
                t["last_done"] = today.isoformat()
                if t["recurrence"] == "yearly":
                    t["next_due"] = today.replace(year=today.year + 1).isoformat()
                elif t["recurrence"] == "2-yearly":
                    t["next_due"] = today.replace(year=today.year + 2).isoformat()
                save_data(D)
                st.rerun()
            if cols[2].button("Delete", key=f"deltr_{t['id']}"):
                D["training"] = [x for x in D["training"] if x["id"] != t["id"]]
                save_data(D)
                st.rerun()

    st.divider()
    st.subheader("Add training")
    exact_new = st.checkbox("I know the exact due date", value=True, key="new_training_exact")
    with st.form("new_training_form"):
        name = st.text_input("Training name")
        if exact_new:
            next_due = st.date_input("Next due date", value=today)
            due_month = ""
        else:
            next_due = None
            due_month = st.text_input("Due month (YYYY-MM)", value=today.strftime("%Y-%m"))
        recurrence = st.selectbox("Recurrence", ["yearly", "2-yearly", "custom", "none"])
        notes = st.text_area("Notes")
        if st.form_submit_button("Add training"):
            D["training"].append({
                "id": f"tr{int(datetime.now().timestamp())}", "name": name, "last_done": "",
                "next_due": next_due.isoformat() if next_due else "", "due_month": due_month.strip(),
                "recurrence": recurrence, "notes": notes,
            })
            save_data(D)
            st.success("Training added.")
            st.rerun()

# ----------------------------------------------------------------------
# PAY
# ----------------------------------------------------------------------
elif page == "Pay":
    st.title("Pay")
    tab1, tab2, tab3 = st.tabs(["Current period", "History", "Rate"])

    p_start, p_end = current_period_for(today)
    if p_start and p_end:
        shifts = all_shift_dates_in_range(p_start, p_end)
        normal = [s for s in shifts if not s["extra"]]
        extra = [s for s in shifts if s["extra"]]
        hol_hours = holiday_hours_in_range(p_start, p_end)
        total_paid = sum(s["hours"] for s in shifts) + hol_hours
        gross = est_gross_for(shifts) + hol_hours * current_rate(p_end.isoformat())
        tax_ni = estimate_tax_ni(gross)
        payday = payday_for(p_end)
    else:
        shifts = normal = extra = []
        hol_hours = total_paid = gross = 0.0
        tax_ni = {"tax": 0.0, "ni": 0.0, "net": 0.0}
        payday = None

    with tab1:
        if not p_start:
            st.warning("The 4-week pay cycle is not configured yet. Enter the actual first day of one employer pay period below.")
            cycle_start = st.date_input("Actual 4-week pay-period start date", value=today, key="initial_pay_cycle_start")
            if st.button("Save pay-cycle start"):
                D["pay_period_start"] = cycle_start.isoformat()
                save_data(D)
                st.success("Pay cycle saved.")
                st.rerun()
        else:
            st.write(f"Period: **{fmt_short(p_start.isoformat())} – {fmt_short(p_end.isoformat())}**")
            st.write(f"Expected payday: **{fmt_short(payday.isoformat())}** ({(payday - today).days} days away)")
            st.caption("Payday defaults to Friday (the last working day of the following week) and can be overridden below for bank holidays or payroll changes.")
            payday_edit = st.date_input("Override payday for this pay period", value=payday, key="payday_override")
            cpay1, cpay2 = st.columns(2)
            if cpay1.button("Save payday override"):
                D.setdefault("payday_overrides", {})[p_end.isoformat()] = payday_edit.isoformat()
                save_data(D)
                st.success("Payday updated.")
                st.rerun()
            if cpay2.button("Use calculated Friday"):
                D.setdefault("payday_overrides", {}).pop(p_end.isoformat(), None)
                save_data(D)
                st.rerun()
            st.divider()
            st.write(f"Normal shifts: {len(normal)} ({sum(s['hours'] for s in normal)}h)")
            st.write(f"Extra shifts: {len(extra)} ({sum(s['hours'] for s in extra)}h)")
            st.write(f"Holiday hours: {hol_hours}h")
            st.write(f"Total paid hours: {total_paid}h")
            rate_now = current_rate(p_end.isoformat())
            st.write(f"Hourly rate used: £{rate_now:.2f}")
            if any(r.get("estimated") for r in D["rates"] if r["effective_from"] <= p_end.isoformat() and r["rate"] == rate_now):
                st.warning("The current hourly rate is an estimate, not a confirmed contractual rate. Update it in the Rate tab when you have the payslip/contract rate.")
            st.write(f"Gross pay (before tax): **£{gross:.2f}**")
            st.write(f"Income tax: -£{tax_ni['tax']:.2f}")
            st.write(f"National Insurance: -£{tax_ni['ni']:.2f}")
            st.write(f"Net pay (after tax): **£{tax_ni['net']:.2f}**")
            st.caption("Estimate only, based on a standard tax code and no other income or deductions — not a payslip.")

            new_start = st.date_input("Edit pay period start date (anchors the 4-week cycle)",
                                       value=date.fromisoformat(D["pay_period_start"]))
            if st.button("Update period start"):
                D["pay_period_start"] = new_start.isoformat()
                save_data(D)
                st.rerun()

            st.divider()
            actual = st.number_input("Actual amount received for this period (£) — optional", value=0.0)
            if st.button("Close this period & log pay"):
                D["pay_history"].append({
                    "start": p_start.isoformat(), "end": p_end.isoformat(), "payday": payday.isoformat(),
                    "total_hours": total_paid, "estimated": gross, "estimated_net": tax_ni["net"],
                    "actual": actual if actual > 0 else None,
                })
                D["pay_period_start"] = (p_end + timedelta(days=1)).isoformat()
                save_data(D)
                st.success("Pay period closed.")
                st.rerun()
    with tab2:
        if not D["pay_history"]:
            st.write("No past pay periods logged yet.")
        for p in reversed(D["pay_history"]):
            with st.expander(f"{fmt_short(p['start'])} – {fmt_short(p['end'])}"):
                st.write(f"Payday: {fmt_short(p['payday'])}")
                st.write(f"Total paid hours: {p['total_hours']}h")
                st.write(f"Estimated gross: £{p['estimated']:.2f}")
                st.write(f"Estimated net: £{p.get('estimated_net', p['estimated']):.2f}")
                if p.get("actual") is not None:
                    diff = p["actual"] - p.get("estimated_net", p["estimated"])
                    st.write(f"Actual received: £{p['actual']:.2f}")
                    st.write(f"Difference vs net estimate: £{diff:.2f}")
                else:
                    st.write("Actual received: not entered")

    with tab3:
        st.write("**Rate history**")
        for r in sorted(D["rates"], key=lambda r: r["effective_from"]):
            st.write(f"From {fmt_short(r['effective_from'])}: £{r['rate']:.2f}/h" + (" · estimate" if r.get("estimated") else " · confirmed"))
        st.divider()
        with st.form("new_rate_form"):
            eff = st.date_input("Effective from", value=today)
            val = st.number_input("New hourly rate (£)", value=current_rate(today.isoformat()), step=0.01)
            if st.form_submit_button("Save new rate"):
                D["rates"].append({"effective_from": eff.isoformat(), "rate": val, "estimated": False})
                save_data(D)
                st.success("Rate saved.")
                st.rerun()

# ----------------------------------------------------------------------
# PROFILE
# ----------------------------------------------------------------------
elif page == "Profile":
    st.title("Profile")
    p = D["profile"]
    with st.form("profile_form"):
        name = st.text_input("Name", value=p["name"])
        role = st.text_input("Job role", value=p["role"])
        unit = st.text_input("Unit", value=p["unit"])
        manager = st.text_input("Unit manager", value=p["manager"])
        col1, col2 = st.columns(2)
        shift_start = col1.text_input("Shift start (HH:MM)", value=p["shift_start"])
        shift_end = col2.text_input("Shift end (HH:MM)", value=p["shift_end"])
        col3, col4 = st.columns(2)
        shift_len = col3.number_input("Total shift length (h)", value=float(p["shift_len"]))
        unpaid_break = col4.number_input("Unpaid break (h)", value=float(p["unpaid_break"]))
        col5, col6 = st.columns(2)
        paid_hours = col5.number_input("Paid hours per shift", value=float(p["paid_hours"]))
        shifts_per_week = col6.number_input("Shifts per week", value=float(p["shifts_per_week"]))
        if st.form_submit_button("Save profile"):
            p.update(name=name, role=role, unit=unit, manager=manager, shift_start=shift_start,
                      shift_end=shift_end, shift_len=shift_len, unpaid_break=unpaid_break,
                      paid_hours=paid_hours, shifts_per_week=shifts_per_week,
                      paid_hours_per_week=paid_hours * shifts_per_week)
            save_data(D)
            st.success("Profile saved.")
            st.rerun()

    st.caption("Rota pattern: Week A (Tue/Wed/Sat/Sun) ↔ Week B (Tue/Wed/Thu/Fri), repeating. "
               "Week of 18 Sep 2026 is Week A.")

    st.divider()
    st.subheader("Notifications")
    st.caption("In-app reminders work whenever the app is open. Phone push notifications use ntfy and can also be sent automatically by the included notifier script when it is scheduled to run.")
    labels = {
        "shift_tonight": "Working tonight", "shift_tomorrow": "Shift tomorrow",
        "holiday_start": "Holiday starting tomorrow", "holiday_pending": "Pending holiday reminder",
        "training_due": "Training due soon", "training_overdue": "Training overdue",
        "pay_period_end": "Pay period ending", "payday_tomorrow": "Payday tomorrow",
    }
    for key, label in labels.items():
        val = st.checkbox(label, value=D["notif_settings"].get(key, True), key=f"notif_{key}")
        D["notif_settings"][key] = val

    st.markdown("**Phone push notifications**")
    push_enabled = st.checkbox("Enable phone push notifications", value=D["notif_settings"].get("push_enabled", False))
    D["notif_settings"]["push_enabled"] = push_enabled

    topic = st.text_input(
        "ntfy private topic",
        value=D["notif_settings"].get("ntfy_topic", ""),
        type="password",
        help="Install the ntfy app on the phone and subscribe to this exact private topic. Treat the topic like a password.",
    )
    D["notif_settings"]["ntfy_topic"] = topic.strip()
    if st.button("Generate a private notification topic"):
        D["notif_settings"]["ntfy_topic"] = "nightshift-" + secrets.token_urlsafe(18)
        save_data(D)
        st.success("Private topic generated. Copy it from the field after the page refresh and subscribe to it in ntfy.")
        st.rerun()

    reminder_hour = st.slider(
        "Shift-day reminder hour", min_value=0, max_value=23,
        value=int(D["notif_settings"].get("shift_reminder_hour", 16)),
        help="24-hour clock. 16 means 4 PM.",
    )
    D["notif_settings"]["shift_reminder_hour"] = reminder_hour
    reminder_message = st.text_area(
        "Shift-day notification message",
        value=D["notif_settings"].get("shift_reminder_message", ""),
        height=110,
    )
    D["notif_settings"]["shift_reminder_message"] = reminder_message

    cnot1, cnot2 = st.columns(2)
    if cnot1.button("Save notification settings"):
        save_data(D)
        st.success("Saved.")
    if cnot2.button("Send test phone notification"):
        save_data(D)
        ok, detail = send_ntfy_notification(
            "Night Shift test 🌙",
            "Notifications are connected. You’ll get shift reminders here, including your water and apple juice reminder. 💧🍎",
        )
        if ok:
            st.success("Test notification sent. Check the phone.")
        else:
            st.error(f"Could not send the test notification: {detail}")

    st.divider()
    st.subheader("Data backup")
    st.caption("For local use, data is saved on this machine. For online deployment, set CARER_DATA_DIR to persistent storage. You can also download a backup here.")
    backup_json = json.dumps(D, indent=2)
    st.download_button(
        "Download data backup",
        data=backup_json,
        file_name="carer_data_backup.json",
        mime="application/json",
    )
    restore = st.file_uploader("Restore from backup", type=["json"], key="restore_backup")
    if restore is not None and st.button("Restore backup now"):
        try:
            restored = json.loads(restore.getvalue().decode("utf-8"))
            st.session_state.D = restored
            save_data(restored)
            st.success("Backup restored.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not restore backup: {e}")
