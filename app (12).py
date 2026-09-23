import streamlit as st
import json, os, base64
from datetime import date, datetime, timedelta

# ----------------------------------------------------------------------
# CONFIG / CONSTANTS
# ----------------------------------------------------------------------
st.set_page_config(page_title="Night Shift", page_icon="🌙", layout="centered")

DATA_FILE = os.path.join(os.path.dirname(__file__), "carer_data.json")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
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
        "rates": [{"effective_from": "2026-01-01", "rate": 12.77}],
        "shift_overrides": {},           # date -> {status, hours, notes}
        "holiday_entitlement": {"2026": 246.4, "2027": 246.4},
        "holiday_requests": [],          # {id,start,end,dates,hours,requested,notes,status,doc}
        "training": [
            {"id": "t1", "name": "Yearly Updates Training", "last_done": "",
             "next_due": "2027-03-09", "recurrence": "yearly", "notes": ""},
            {"id": "t2", "name": "DMI Moving and Handling Updates", "last_done": "",
             "next_due": "2027-03-02", "recurrence": "yearly", "notes": ""},
            {"id": "t3", "name": "First Aid Training", "last_done": "",
             "next_due": "2027-02-28", "recurrence": "custom", "notes": "Exact date TBC"},
        ],
        "pay_period_start": "2026-07-27",  # anchor for the repeating 4-week pay cycle
        "pay_history": [],
        "notif_settings": {
            "shift": {"enabled": True, "lead_minutes": 60,
                      "message": "You have a shift tonight at {time} 🌙 Don't forget your water and apple juice so you stay hydrated. 💧🍎"},
            "training": {"enabled": True, "lead_days": 7},
            "holiday": {"enabled": True, "lead_days": 1},
            "payday": {"enabled": True, "lead_days": 1},
        },
        "fired_log": {}, "recent_log": [],
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
            is_june_2026 = b[0].startswith("2026-06")
            D["holiday_requests"].append({
                "id": "seed" + b[0], "start": b[0], "end": b[-1], "dates": b,
                "hours": len(b) * D["profile"]["paid_hours"], "requested": b[0],
                "notes": "", "status": "taken" if is_june_2026 else "approved", "doc": None,
            })
    D["seeded"] = True
    save_data(D)


def apply_status_anchor_fix():
    # one-time correction for data files created before statuses/anchor were confirmed
    if D.get("status_anchor_fix_applied"):
        return
    june_req = next((r for r in D["holiday_requests"] if "2026-06-23" in r["dates"]), None)
    if june_req:
        june_req["status"] = "taken"
    dec_req = next((r for r in D["holiday_requests"] if "2026-12-08" in r["dates"]), None)
    if dec_req:
        dec_req["status"] = "approved"
    D["pay_period_start"] = "2026-07-27"
    D["status_anchor_fix_applied"] = True
    save_data(D)


def apply_notif_schema_migration():
    # notif_settings shape changed from flat toggles to per-category objects with lead times
    ns = D.get("notif_settings")
    if not ns or not isinstance(ns.get("shift"), dict):
        D["notif_settings"] = default_data()["notif_settings"]
    if "fired_log" not in D:
        D["fired_log"] = {}
    if "recent_log" not in D:
        D["recent_log"] = []
    save_data(D)


seed_known_holidays()
apply_status_anchor_fix()
apply_notif_schema_migration()

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
    next_week_mon = monday_of(period_end) + timedelta(days=7)
    return next_week_mon + timedelta(days=4)  # Friday


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


def training_status(t):
    if not t.get("next_due"):
        return "upcoming"
    days = (date.fromisoformat(t["next_due"]) - date.today()).days
    if days < 0:
        return "overdue"
    if days <= 30:
        return "due soon"
    return "upcoming"


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


def fill_template(msg, vars_):
    for k, v in vars_.items():
        msg = msg.replace("{" + k + "}", str(v))
    return msg


def is_working_day(ds):
    if is_holiday_date(ds):
        return False
    st_ = shift_status_for(ds)
    return bool(st_ and st_["status"] in ("scheduled", "worked", "extra"))


def shift_datetime(ds, now):
    hh, mm = [int(x) for x in D["profile"]["shift_start"].split(":")]
    d = date.fromisoformat(ds)
    return datetime(d.year, d.month, d.day, hh, mm)


def due_shift_notif(now):
    S = D["notif_settings"]["shift"]
    if not S["enabled"]:
        return None
    for i in (0, 1):
        ds = (now.date() + timedelta(days=i)).isoformat()
        if not is_working_day(ds):
            continue
        dt = shift_datetime(ds, now)
        diff_min = (dt - now).total_seconds() / 60
        if 0 <= diff_min <= S["lead_minutes"]:
            key = f"shift:{ds}"
            if D["fired_log"].get(key):
                continue
            return {"key": key, "text": fill_template(
                S["message"], {"time": D["profile"]["shift_start"], "date": fmt(ds), "unit": D["profile"]["unit"]})}
    return None


def due_training_notifs(now):
    T = D["notif_settings"]["training"]
    if not T["enabled"]:
        return []
    out = []
    for t in D["training"]:
        if not t.get("next_due"):
            continue
        days = (date.fromisoformat(t["next_due"]) - now.date()).days
        if days < 0:
            key = f"training-overdue:{t['id']}:{t['next_due']}"
            if not D["fired_log"].get(key):
                out.append({"key": key, "text": f"{t['name']} is overdue."})
        elif days <= T["lead_days"]:
            key = f"training-due:{t['id']}:{t['next_due']}"
            if not D["fired_log"].get(key):
                when = "today" if days < 1 else f"in {days} day(s)"
                out.append({"key": key, "text": f"{t['name']} is due {when} ({fmt_short(t['next_due'])})."})
    return out


def due_holiday_notifs(now):
    H = D["notif_settings"]["holiday"]
    if not H["enabled"]:
        return []
    out = []
    for r in D["holiday_requests"]:
        if r["status"] != "approved":
            continue
        days = (date.fromisoformat(r["start"]) - now.date()).days
        if 0 <= days <= H["lead_days"]:
            key = f"holiday-start:{r['id']}"
            if not D["fired_log"].get(key):
                when = "today" if days < 1 else f"in {days} day(s)"
                out.append({"key": key, "text": f"Your holiday starts {when} ({fmt(r['start'])})."})
    if any(r["status"] == "pending" for r in D["holiday_requests"]):
        key = f"holiday-pending:{now.date().isoformat()}"
        if not D["fired_log"].get(key):
            out.append({"key": key, "text": "You have a holiday request still pending."})
    return out


def due_payday_notif(now):
    P = D["notif_settings"]["payday"]
    if not P["enabled"]:
        return None
    _, end = current_period_for(now.date())
    payday = payday_for(end)
    days = (payday - now.date()).days
    if 0 <= days <= P["lead_days"]:
        key = f"payday:{payday.isoformat()}"
        if D["fired_log"].get(key):
            return None
        when = "today" if days < 1 else f"in {days} day(s)"
        return {"key": key, "text": f"Payday is {when} ({fmt_short(payday.isoformat())})."}
    return None


def collect_due_notifs(now):
    items = []
    s = due_shift_notif(now)
    if s:
        items.append(s)
    items += due_training_notifs(now)
    items += due_holiday_notifs(now)
    p = due_payday_notif(now)
    if p:
        items.append(p)
    return items


def fire_notifs(items):
    if not items:
        return
    for it in items:
        D["fired_log"][it["key"]] = True
        D["recent_log"].insert(0, {"text": it["text"], "at": datetime.now().isoformat()})
    D["recent_log"] = D["recent_log"][:20]
    save_data(D)


def check_notifs_now():
    # Runs whenever this Streamlit script executes (page load / any interaction / rerun).
    # There is no background process here, so nothing fires while the app isn't open.
    fire_notifs(collect_due_notifs(datetime.now()))


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
# SIDEBAR NAV
# ----------------------------------------------------------------------
st.sidebar.title("🌙 Night Shift")
page = st.sidebar.radio("Go to", ["Home", "Calendar", "Leave", "Training", "Pay", "Profile"])

today = date.today()

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
    period_shifts = all_shift_dates_in_range(p_start, p_end)
    period_gross = est_gross_for(period_shifts)
    tax_ni = estimate_tax_ni(period_gross)
    payday = payday_for(p_end)
    hs = holiday_summary(today.year)
    next_train = sorted(D["training"], key=lambda t: t.get("next_due") or "9999")[0] if D["training"] else None
    check_notifs_now()
    notifs = D["recent_log"][:6]

    c1, c2 = st.columns(2)
    c1.metric("Working today", "Yes" if working_today else "No")
    c2.metric("Shifts this week", len(week_shifts))

    st.subheader("Next shift")
    if next_s:
        st.write(f"**{fmt(next_s)}** · {D['profile']['shift_start']} – {D['profile']['shift_end']}")
    else:
        st.write("No upcoming shift found.")

    c3, c4 = st.columns(2)
    c3.metric("Paid hours this week", f"{sum(s['hours'] for s in week_shifts):.0f}h")
    c4.metric("Est. take-home this period", f"£{tax_ni['net']:.2f}")

    st.subheader("Estimated pay this period")
    st.write(f"Gross (before tax): **£{period_gross:.2f}**")
    st.write(f"Income tax: -£{tax_ni['tax']:.2f}")
    st.write(f"National Insurance: -£{tax_ni['ni']:.2f}")
    st.write(f"Net (after tax): **£{tax_ni['net']:.2f}**")
    st.caption("Estimate only, based on a standard tax code and no other income or deductions.")

    st.subheader("Payday")
    st.write(f"Next payday: **{fmt_short(payday.isoformat())}** ({(payday - today).days} days away)")

    st.subheader("Holiday")
    st.write(f"Confirmed remaining: **{hs['confirmed_remaining']:.1f}h**")
    st.write(f"Potential remaining if pending approved: {hs['potential_remaining']:.1f}h")

    st.subheader("Training")
    if next_train:
        st.write(f"Next due: **{next_train['name']}** — {badge(training_status(next_train))} — "
                  f"{fmt_short(next_train['next_due']) if next_train.get('next_due') else 'TBC'}")

    st.subheader("Notifications")
    if notifs:
        for n in notifs:
            st.info(n["text"])
    else:
        st.write("Nothing due right now.")
    st.caption("In-app reminders — only checked when this page loads or you interact with it. Manage them in Profile.")

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
        with st.form("new_leave_form"):
            start = st.date_input("Start date", value=today)
            end = st.date_input("End date", value=today)
            notes = st.text_area("Notes")
            status = st.selectbox("Status", ["pending", "approved", "declined", "cancelled", "taken"])
            if st.form_submit_button("Create request"):
                dates = []
                d = start
                while d <= end:
                    dates.append(d.isoformat())
                    d += timedelta(days=1)
                D["holiday_requests"].append({
                    "id": f"h{int(datetime.now().timestamp())}", "start": start.isoformat(),
                    "end": end.isoformat(), "dates": dates, "hours": len(dates) * D["profile"]["paid_hours"],
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
    for t in sorted(D["training"], key=lambda t: t.get("next_due") or "9999"):
        with st.expander(f"{t['name']} · {badge(training_status(t))}"):
            st.write(f"Next due: {fmt_short(t['next_due']) if t.get('next_due') else 'TBC'}")
            st.write(f"Recurrence: {t['recurrence']}")
            st.write(f"Notes: {t.get('notes') or '—'}")
            new_next = st.date_input("Update next due date",
                                      value=date.fromisoformat(t["next_due"]) if t.get("next_due") else today,
                                      key=f"due_{t['id']}")
            doc = st.file_uploader("Upload certificate", key=f"cert_{t['id']}", type=["png", "jpg", "jpeg", "pdf"])
            cols = st.columns(3)
            if cols[0].button("Save due date", key=f"savedue_{t['id']}"):
                t["next_due"] = new_next.isoformat()
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
    with st.form("new_training_form"):
        name = st.text_input("Training name")
        next_due = st.date_input("Next due date", value=today)
        recurrence = st.selectbox("Recurrence", ["yearly", "2-yearly", "custom", "none"])
        notes = st.text_area("Notes")
        if st.form_submit_button("Add training"):
            D["training"].append({
                "id": f"tr{int(datetime.now().timestamp())}", "name": name, "last_done": "",
                "next_due": next_due.isoformat(), "recurrence": recurrence, "notes": notes,
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
    shifts = all_shift_dates_in_range(p_start, p_end)
    normal = [s for s in shifts if not s["extra"]]
    extra = [s for s in shifts if s["extra"]]
    hol_hours = sum(r["hours"] for r in D["holiday_requests"]
                     if r["status"] in ("approved", "taken")
                     and any(p_start.isoformat() <= dd <= p_end.isoformat() for dd in r["dates"]))
    total_paid = sum(s["hours"] for s in shifts) + hol_hours
    gross = est_gross_for(shifts) + hol_hours * current_rate(p_end.isoformat())
    tax_ni = estimate_tax_ni(gross)
    payday = payday_for(p_end)

    with tab1:
        st.write(f"Period: **{fmt_short(p_start.isoformat())} – {fmt_short(p_end.isoformat())}**")
        st.write(f"Expected payday: **{fmt_short(payday.isoformat())}** ({(payday - today).days} days away)")
        st.divider()
        st.write(f"Normal shifts: {len(normal)} ({sum(s['hours'] for s in normal)}h)")
        st.write(f"Extra shifts: {len(extra)} ({sum(s['hours'] for s in extra)}h)")
        st.write(f"Holiday hours: {hol_hours}h")
        st.write(f"Total paid hours: {total_paid}h")
        st.write(f"Hourly rate: £{current_rate(p_end.isoformat()):.2f}")
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
            st.write(f"From {fmt_short(r['effective_from'])}: £{r['rate']:.2f}/h")
        st.divider()
        with st.form("new_rate_form"):
            eff = st.date_input("Effective from", value=today)
            val = st.number_input("New hourly rate (£)", value=current_rate(today.isoformat()), step=0.01)
            if st.form_submit_button("Save new rate"):
                D["rates"].append({"effective_from": eff.isoformat(), "rate": val})
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
                      paid_hours=paid_hours, shifts_per_week=shifts_per_week)
            save_data(D)
            st.success("Profile saved.")
            st.rerun()

    st.caption("Rota pattern: Week A (Tue/Wed/Sat/Sun) ↔ Week B (Tue/Wed/Thu/Fri), repeating. "
               "Week of 18 Sep 2026 is Week A.")

    st.divider()
    st.subheader("Pay cycle anchor")
    st.caption("Start date of a known 4-week pay period, used to work out every future period and payday. "
               "Currently anchored to 27 Jul 2026, giving the period 24 Aug – 20 Sep 2026 with payday 25 Sep 2026.")
    anchor = st.date_input("Pay cycle anchor date", value=date.fromisoformat(D["pay_period_start"]), key="anchor_profile")
    if st.button("Update pay cycle anchor"):
        D["pay_period_start"] = anchor.isoformat()
        save_data(D)
        st.success("Pay cycle anchor updated.")
        st.rerun()

    st.divider()
    st.subheader("Shift reminders")
    S = D["notif_settings"]["shift"]
    S["enabled"] = st.checkbox("Enabled", value=S["enabled"], key="shift_notif_enabled")
    S["lead_minutes"] = st.number_input("Send this many minutes before the shift starts",
                                         value=int(S["lead_minutes"]), min_value=5, step=5, key="shift_lead")
    S["message"] = st.text_area("Reminder message — use {time}, {date}, {unit} as placeholders",
                                 value=S["message"], key="shift_msg")
    st.caption("Only fires on days you're actually rota'd on, including manually added extra shifts — "
               "never on holiday or off days. Each shift reminds you once.")
    if st.button("Save shift reminder settings"):
        save_data(D)
        st.success("Saved.")
    if st.button("Send test notification"):
        text = fill_template(S["message"], {"time": D["profile"]["shift_start"],
                                             "date": fmt(today.isoformat()), "unit": D["profile"]["unit"]})
        D["recent_log"].insert(0, {"text": f"[Test] {text}", "at": datetime.now().isoformat()})
        D["recent_log"] = D["recent_log"][:20]
        save_data(D)
        st.success("Test notification added — see it under Home → Notifications, or below.")
        st.info(text)

    st.divider()
    st.subheader("Other reminders")
    T, H, P = D["notif_settings"]["training"], D["notif_settings"]["holiday"], D["notif_settings"]["payday"]
    T["enabled"] = st.checkbox("Training due/overdue", value=T["enabled"], key="train_notif_enabled")
    T["lead_days"] = st.number_input("Remind this many days before due", value=int(T["lead_days"]), min_value=1, key="train_lead")
    H["enabled"] = st.checkbox("Holidays starting soon / pending", value=H["enabled"], key="hol_notif_enabled")
    H["lead_days"] = st.number_input("Remind this many days before it starts", value=int(H["lead_days"]), min_value=1, key="hol_lead")
    P["enabled"] = st.checkbox("Payday coming up", value=P["enabled"], key="pay_notif_enabled")
    P["lead_days"] = st.number_input("Remind this many days before payday", value=int(P["lead_days"]), min_value=1, key="pay_lead")
    if st.button("Save other reminder settings"):
        save_data(D)
        st.success("Saved.")

    if D["recent_log"]:
        st.divider()
        st.subheader("Recent notifications")
        for n in D["recent_log"][:10]:
            st.write(f"- {n['text']}")

    st.divider()
    st.warning(
        "In-app reminders vs. real push notifications: everything above only fires when this "
        "Streamlit page is open and running a script cycle (on load, or when you click something) — "
        "Streamlit has no background process, so nothing is sent while the app is closed or your "
        "phone is locked. To get a true push notification on your phone at the right time, you need "
        "something outside Streamlit that runs on a schedule and can reach your device even when the "
        "app isn't open — for example a small script (cron job or APScheduler) that reads this same "
        "carer_data.json, runs the same collect_due_notifs() check, and sends the result through a "
        "push service such as ntfy.sh, Pushover, a Telegram/WhatsApp bot, or a proper Web Push setup "
        "with a server and VAPID keys. Say the word and I can build that companion script separately."
    )
