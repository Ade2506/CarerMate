"""
ASSAY web dashboard — thin Flask layer around assay_signals.py.

assay_signals.py itself is UNCHANGED. Every analysis function (technical,
news, event-risk, decision engine) is reused exactly as-is; this file only
adds: a background refresh loop (replacing the old CLI while-loop's job),
an HTTP route that renders the current state as a webpage, and basic
password protection.

DEPLOYMENT NOTE — single worker only. Running this with more than one
worker process (e.g. `gunicorn --workers 2 app:app`) would give each
worker its own separate copy of the caches, causing duplicate API calls
and inconsistent state between requests. Always deploy with exactly one
worker: `gunicorn --workers 1 app:app`. For a personal single-user
dashboard, one worker handling both the background loop and occasional
page requests is more than enough.

Required environment variables (set these on the host, never in code):
    TWELVE_DATA_API_KEY
    FINNHUB_API_KEY
    FRED_API_KEY
    ASSAY_DASHBOARD_PASSWORD   (any username works; only the password is checked)
"""

import os
import secrets
import threading
import time
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, Response, render_template, request

import assay_signals as engine

app = Flask(__name__)

BACKGROUND_TICK_SECONDS = 30  # how often the background loop wakes up to check
                               # whether each source is actually due for a refresh
                               # (the due-checks inside refresh_gold/refresh_news/
                               # refresh_events are what actually gate real API
                               # calls — unchanged from the CLI version)


def background_loop():
    api_key = os.environ.get("TWELVE_DATA_API_KEY")
    finnhub_key = os.environ.get("FINNHUB_API_KEY")
    fred_key = os.environ.get("FRED_API_KEY")

    gold_budget = engine.Budget()
    finnhub_budget = engine.Budget(cap=engine.FINNHUB_DAILY_CALL_CAP)
    fred_budget = engine.Budget(cap=engine.FRED_DAILY_CALL_CAP)

    engine.load_gold_cache()
    engine.load_news_cache()
    engine.load_event_cache()

    while True:
        now = time.time()
        try:
            engine.refresh_gold(api_key, gold_budget, now)
            engine.refresh_news(finnhub_key, finnhub_budget, now)
            engine.refresh_events(fred_key, fred_budget, now)
        except Exception as e:
            # the background thread must never die silently — a crashed
            # thread here would freeze the dashboard on stale data forever
            # with no visible error, which is worse than a logged retry
            print(f"[background_loop] unexpected error, will retry next tick: {e}")

        # TEMPORARY diagnostic line — always prints, every tick, so we can
        # see directly in Render's logs whether this loop is even running
        # and exactly what each gold timeframe's state is. Remove once the
        # deployment issue is confirmed fixed.
        status = {tf: ("OK" if e["data"] is not None else (e["error"] or "no data yet"))
                  for tf, e in engine.gold_cache.items()}
        print(f"[assay-diag] tick @ {datetime.now().strftime('%H:%M:%S')} gold={status} "
              f"finnhub_key_set={bool(finnhub_key)} fred_key_set={bool(fred_key)} "
              f"twelvedata_key_set={bool(api_key)}", flush=True)

        time.sleep(BACKGROUND_TICK_SECONDS)


def _password_ok(candidate):
    expected = os.environ.get("ASSAY_DASHBOARD_PASSWORD", "")
    if not expected:
        # No password configured. Fails OPEN only in local/dev use — the
        # deployment guide is explicit that this must always be set in
        # production. Left this way (rather than hard-failing) so the app
        # is still usable for local testing without extra setup.
        return True
    return secrets.compare_digest(candidate, expected)


def requires_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        auth = request.authorization
        if not auth or not _password_ok(auth.password):
            return Response(
                "Authentication required", 401,
                {"WWW-Authenticate": 'Basic realm="ASSAY Dashboard"'},
            )
        return view(*args, **kwargs)
    return wrapped


def build_view_model():
    now = time.time()
    tfs = engine.build_gold_tfs()

    # Even while not yet "ready" (gold data incomplete), surface any known
    # errors — mirrors the CLI version's behavior of showing per-timeframe
    # errors during "still gathering" rather than hiding them until ready.
    error_info = {
        "gold_errors": {tf: e["error"] for tf, e in engine.gold_cache.items() if e["error"]},
        "news_error": engine.news_cache["error"],
        "event_error": engine.event_cache["error"],
    }

    if tfs is None:
        return {"ready": False, **error_info}

    tech = engine.build_gold_signal(tfs)
    news = engine.aggregate_news(engine.news_cache["scored"], now)
    event = engine.classify_event_risk(datetime.now(timezone.utc))
    decision = engine.build_final_signal(tech, tfs, news, event)

    return {
        "ready": True,
        "updated": datetime.now().strftime("%H:%M:%S"),
        "tech": tech,
        "news": news,
        "event": event,
        "decision": decision,
        "explanation": engine.build_final_explanation(decision),
        "levels": decision.get("levels"),
        "tfs": tfs,
        "fmt": engine.fmt,
        **error_info,
    }


@app.route("/")
@requires_auth
def index():
    return render_template("dashboard.html", **build_view_model())


@app.route("/healthz")
def healthz():
    # unauthenticated on purpose — hosting platforms ping this to check the
    # service is alive; it reveals nothing about gold signals or keys
    return "ok"


# Started once, at import time, so it runs exactly once as long as the
# server process is started with a single worker (see module docstring).
_background_thread = threading.Thread(target=background_loop, daemon=True)
_background_thread.start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
