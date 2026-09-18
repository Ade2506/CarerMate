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
            "shift_tonight": True, "shift_tomorrow": True, "holiday_start": True,
            "holiday_pending": True, "training_due": True, "training_overdue": True,
            "pay_period_end": True, "payday_tomorrow": True,
        },
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


seed_known_holidays()
apply_status_anchor_fix()

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
    if N["payday_tomorrow"] and payday.isoformat() == tomorrow:
        out.append("Your payday is tomorrow.")
    _, end = current_period_for(today)
    if N["pay_period_end"] and 0 <= (end - today).days <= 2:
        out.append("Your pay period ends this week.")
    return out


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
    notifs = build_notifications(today, working_today, next_s, payday, hs)

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
            st.info(n)
    else:
        st.write("Nothing due right now.")

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
    st.subheader("Notifications")
    labels = {
        "shift_tonight": "Working tonight", "shift_tomorrow": "Shift tomorrow",
        "holiday_start": "Holiday starting tomorrow", "holiday_pending": "Pending holiday reminder",
        "training_due": "Training due soon", "training_overdue": "Training overdue",
        "pay_period_end": "Pay period ending", "payday_tomorrow": "Payday tomorrow",
    }
    for key, label in labels.items():
        val = st.checkbox(label, value=D["notif_settings"].get(key, True), key=f"notif_{key}")
        D["notif_settings"][key] = val
    if st.button("Save notification settings"):
        save_data(D)
        st.success("Saved.")
