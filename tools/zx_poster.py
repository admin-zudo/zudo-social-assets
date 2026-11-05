#!/usr/bin/env python3
"""Zoho Explained poster: posts each day's episode at exactly 00:00 IST (18:30 UTC).

Started by .github/workflows/zx-poster.yml about 15-25 minutes before midnight IST.
Finds queue slots whose id starts with "zx-" and whose items are due within the next
75 minutes, claims them, waits until the due second, starts every Make run at the same
moment (Instagram, LinkedIn page, LinkedIn profile ...), then records the results.

Reuses the plumbing of tools/video_poster.py (same queue file, same Make scenario,
same status flow pending -> posting -> done | failed). If this workflow ever fails to
start, the regular Video poster run (:23/:53 UTC) still posts anything left pending.
No AI involved.
"""
import os
import sys
import threading
import time
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import video_poster as vp  # noqa: E402

LOOKAHEAD = timedelta(minutes=75)
GRACE = timedelta(minutes=10)


def pending_zx():
    q = vp.load()
    now = vp.now_utc()
    out = []
    for slot_id, slot in q["slots"].items():
        if not slot_id.startswith("zx-"):
            continue
        for idx, it in enumerate(slot.get("items", [])):
            if it.get("status") != "pending" or not it.get("due_utc"):
                continue
            d = vp.parse(it["due_utc"])
            if now - GRACE <= d <= now + LOOKAHEAD:
                out.append((d, slot_id, idx, it))
    return out


def sleep_until(t):
    while True:
        left = (t - vp.now_utc()).total_seconds()
        if left <= 0:
            return
        time.sleep(min(left, 30))


def main():
    if not vp.TOKEN:
        vp.log("MAKE_API_TOKEN secret is missing.")
        sys.exit(1)
    vp.git("config", "user.name", "Zudo Works video poster")
    vp.git("config", "user.email", "video-poster@users.noreply.github.com")
    items = pending_zx()
    if not items:
        vp.log("No Zoho Explained post due in the next 75 minutes.")
        return
    due = min(d for d, *_ in items)
    batch = [x for x in items if x[0] == due]
    vp.log(f"{len(batch)} item(s) due at {vp.iso(due)}; waiting.")

    # claim ~40 s early so no other run can take them
    sleep_until(due - timedelta(seconds=40))
    claimed = []
    for d, slot_id, idx, it in batch:
        if vp.set_fields(slot_id, idx, "pending",
                         {"status": "posting", "posting_at": vp.iso(due)},
                         f"Zoho Explained: posting {it['target']} {slot_id}"):
            claimed.append((slot_id, idx, it))

    sleep_until(due)
    results = {}

    def fire(k, it):
        results[k] = vp.run_scenario(it)

    threads = [threading.Thread(target=fire, args=((s, i), it)) for s, i, it in claimed]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    vp.log(f"Started {len(claimed)} Make run(s) at {vp.iso(vp.now_utc())}.")

    started = []
    for slot_id, idx, it in claimed:
        code, body = results[(slot_id, idx)]
        exec_id = str(body.get("executionId", "")) if isinstance(body, dict) else ""
        if code in (200, 201, 202) and exec_id:
            vp.set_fields(slot_id, idx, "posting", {"exec_id": exec_id},
                          f"Zoho Explained: Make run started {it['target']} {slot_id}")
            started.append((slot_id, idx, it, exec_id))
            continue
        msg = body.get("message") if isinstance(body, dict) else str(body)
        reason = f"Make API {code}: {msg or body}"[:300]
        if code in (0, 429) or code >= 500:
            # Make never started it: hand it back to the regular poster for a retry
            vp.set_fields(slot_id, idx, "posting",
                          {"status": "pending", "due_utc": vp.iso(vp.now_utc() + vp.RETRY_DELAY),
                           "note": f"retry: {reason}"},
                          f"Zoho Explained: retry later {it['target']} {slot_id}")
            vp.log(f"RETRY {it['target']} {slot_id}: {reason}")
        else:
            vp.set_fields(slot_id, idx, "posting", {"status": "failed", "note": reason},
                          f"Zoho Explained: failed {it['target']} {slot_id}")
            vp.log(f"FAILED {it['target']} {slot_id}: {reason}")

    for slot_id, idx, it, exec_id in started:
        status, err = vp.wait_for(exec_id)
        if status in ("SUCCESS", "WARNING", "ERROR"):
            vp.finish(slot_id, idx, it, status, err, exec_id)
        else:
            vp.log(f"STILL RUNNING {it['target']} {slot_id} (exec {exec_id}); next run will check it")


if __name__ == "__main__":
    try:
        main()
    finally:
        s = os.environ.get("GITHUB_STEP_SUMMARY")
        if s:
            with open(s, "a", encoding="utf-8") as f:
                f.write("### Zoho Explained poster\n\n" + "\n".join(f"- {l}" for l in vp.log_lines) + "\n")
