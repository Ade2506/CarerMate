"""Background notification runner for the Night Shift Streamlit app.

Run this script hourly (cron, GitHub Actions, Render cron job, etc.). It reads the
same carer_data.json file as app.py and sends due push notifications through ntfy.
"""
import json, os, urllib.request
from datetime import date, datetime, timedelta

APP_DIR = os.path.dirname(__file__)
DATA_DIR = os.environ.get("CARER_DATA_DIR", APP_DIR)
DATA_FILE = os.path.join(DATA_DIR, "carer_data.json")
ANCHOR_DATE = date(2026, 9, 18)
ANCHOR_MONDAY = ANCHOR_DATE - timedelta(days=ANCHOR_DATE.weekday())
WEEK_A_DAYS = {1, 2, 5, 6}
WEEK_B_DAYS = {1, 2, 3, 4}


def load_data():
    if not os.path.exists(DATA_FILE):
        raise SystemExit(f"No data file found at {DATA_FILE}")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)


def monday_of(d):
    return d - timedelta(days=d.weekday())


def week_type_for(d):
    diff_weeks = (monday_of(d) - ANCHOR_MONDAY).days // 7
    return "A" if diff_weeks % 2 == 0 else "B"


def is_rota_work_day(d):
    days = WEEK_A_DAYS if week_type_for(d) == "A" else WEEK_B_DAYS
    return d.weekday() in days


def is_holiday_date(D, ds):
    return any(r.get("status") in ("approved", "taken") and ds in r.get("dates", [])
               for r in D.get("holiday_requests", []))


def shift_status_for(D, ds):
    ov = D.get("shift_overrides", {}).get(ds)
    if ov:
        return ov
    if is_rota_work_day(date.fromisoformat(ds)):
        return {"status": "scheduled"}
    return None


def next_shift_from(D, ref_date):
    d = ref_date
    for _ in range(60):
        ds = d.isoformat()
        if not is_holiday_date(D, ds):
            s = shift_status_for(D, ds)
            if s and s.get("status") in ("scheduled", "worked", "extra"):
                return ds
        d += timedelta(days=1)
    return None


def send_ntfy(D, title, message):
    topic = D.get("notif_settings", {}).get("ntfy_topic", "").strip()
    if not topic:
        return False
    req = urllib.request.Request(
        f"https://ntfy.sh/{topic}",
        data=message.encode("utf-8"),
        method="POST",
        headers={"Title": title, "Priority": "default"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def push_once(D, key, title, message):
    log = D.setdefault("notification_log", {})
    if log.get(key):
        return False
    if send_ntfy(D, title, message):
        log[key] = datetime.now().isoformat(timespec="seconds")
        if len(log) > 200:
            D["notification_log"] = dict(sorted(log.items(), key=lambda x: x[1], reverse=True)[:200])
        save_data(D)
        return True
    return False


def main():
    D = load_data()
    cfg = D.get("notif_settings", {})
    if not cfg.get("push_enabled") or not cfg.get("ntfy_topic", "").strip():
        return

    now = datetime.now()
    today = now.date()
    ds = today.isoformat()
    tomorrow = today + timedelta(days=1)
    tomorrow_ds = tomorrow.isoformat()

    working_today = (not is_holiday_date(D, ds)) and bool(
        shift_status_for(D, ds) and shift_status_for(D, ds).get("status") in ("scheduled", "worked", "extra")
    )
    reminder_hour = int(cfg.get("shift_reminder_hour", 16))
    if cfg.get("shift_tonight") and working_today and now.hour >= reminder_hour:
        msg = cfg.get("shift_reminder_message") or (
            f"You have a shift today. Your shift starts at {D['profile']['shift_start']} at {D['profile']['unit']}."
        )
        push_once(D, f"shift_today:{ds}", "Shift reminder", msg)

    if cfg.get("shift_tomorrow") and next_shift_from(D, today) == tomorrow_ds and now.hour >= 18:
        push_once(
            D, f"shift_tomorrow:{tomorrow_ds}", "Shift tomorrow",
            f"You’re working tomorrow at {D['profile']['shift_start']} in {D['profile']['unit']}. Get your things ready for the night.",
        )

    if cfg.get("holiday_start"):
        for r in D.get("holiday_requests", []):
            if r.get("status") == "approved" and r.get("start") == tomorrow_ds:
                push_once(D, f"holiday:{r.get('id')}:{tomorrow_ds}", "Holiday starts tomorrow", "Your approved holiday starts tomorrow.")

    # Training reminders. For exact dates, alert at 30 days and after due date.
    for t in D.get("training", []):
        due_s = t.get("next_due", "")
        if not due_s:
            continue
        due = date.fromisoformat(due_s)
        days = (due - today).days
        if cfg.get("training_due") and 0 <= days <= 30:
            push_once(D, f"training_due:{t.get('id')}:{due_s}", "Training due soon", f"{t.get('name')} is due on {due.strftime('%d %b %Y')}.")
        if cfg.get("training_overdue") and days < 0:
            push_once(D, f"training_overdue:{t.get('id')}:{today.isoformat()}", "Training overdue", f"{t.get('name')} is overdue.")


if __name__ == "__main__":
    main()
