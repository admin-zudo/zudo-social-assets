#!/usr/bin/env python3
"""Zudo Works video poster.

Runs from GitHub Actions on a schedule. Reads queue/video_queue.json, and for every
item whose due time has come, runs Make scenario 8132416 to post it to
Instagram / Facebook / LinkedIn. Status changes are committed back to the repo.

No AI is involved: this is a plain, deterministic script.
A push that changes this file also runs it once (useful if a scheduled run is late or missing).

Queue format (queue/video_queue.json):
{
  "slots": {
    "2026-10-31_1344_v1": {
      "slot": "2026-10-31T08:14:00Z", "ist": "31 Oct 2026, 13:44", "topic": "...",
      "items": [{"target": "linkedin_page", "due_utc": "2026-10-31T08:14:00Z",
                 "video_url": "...", "caption": "...", "title": "...", "cover_ms": 3000,
                 "status": "pending", "exec_id": "", "note": ""}]
    }
  }
}
Item status: pending -> posting -> done | failed.

Environment:
  MAKE_API_TOKEN  (required)  Make API token (GitHub secret)
  MAKE_BASE       default https://eu1.make.com/api/v2
  SCENARIO_ID     default 8132416
  MODE            "post" (default) or "check" (only tests the Make connection)
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

QUEUE = "queue/video_queue.json"
CHECK_FILE = "queue/poster_check.json"
MAKE_BASE = os.environ.get("MAKE_BASE", "https://eu1.make.com/api/v2").rstrip("/")
SCENARIO_ID = int(os.environ.get("SCENARIO_ID", "8132416"))
TOKEN = os.environ.get("MAKE_API_TOKEN", "").strip()
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GH_REPO = os.environ.get("GITHUB_REPOSITORY", "admin-zudo/zudo-social-assets")
JSD_MAIN = f"https://cdn.jsdelivr.net/gh/{GH_REPO}@main/"
CDN_BRANCH = "cdn"

MAX_PER_RUN = 10
MISSED_AFTER = timedelta(hours=6)          # don't post more than 6 h late
SAME_PLATFORM_GAP = 120                    # seconds between two posts on one platform
RETRY_DELAY = timedelta(minutes=20)
STUCK_AFTER = timedelta(minutes=45)        # "posting" with no exec id this long -> failed
POLL_SECONDS = 300                         # wait up to 5 min for a Make run to finish

TEMPORARY = re.compile(
    r"timeout|timed out|rate.?limit|too many|429|50[0-9]|temporar|try again|"
    r"processing|not ready|ECONNRESET|ETIMEDOUT|socket hang up|unavailable", re.I)
AUTH = re.compile(r"401|403|unauthori[sz]ed|forbidden|token|expired|re-?connect|"
                  r"permission|oauth|invalid.?(grant|credentials)", re.I)

log_lines = []


def log(msg):
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = f"[{stamp}Z] {msg}"
    print(line, flush=True)
    log_lines.append(msg)


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


# ---------------------------------------------------------------- Make API

def make(method, path, body=None, timeout=60):
    url = MAKE_BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Token {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "ZudoWorksVideoPoster/1.0 (+https://www.zudoworks.com)",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode() or "{}"
            return r.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = {"message": raw[:500]}
        return e.code, payload
    except Exception as e:  # network trouble
        return 0, {"message": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------- small CDN commit
# jsDelivr refuses a repo whose files add up to more than 50 MB, and this repo is far
# bigger. So for each jsDelivr video link we publish a tiny commit (branch "cdn",
# no history) that contains only that video, and give Make the link pinned to that
# commit. Nothing on main is changed or deleted.

def github(method, path, body=None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GH_REPO}{path}",
        data=json.dumps(body).encode() if body is not None else None, method=method,
        headers={"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json",
                 "User-Agent": "ZudoWorksVideoPoster/1.0", "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode() or "{}")


def small_cdn_url(url):
    """Return a jsDelivr link that works, or the original link if no change is needed."""
    if not url.startswith(JSD_MAIN) or not GH_TOKEN:
        return url
    path = url[len(JSD_MAIN):].split("?")[0]
    meta = github("GET", f"/contents/{urllib.request.quote(path)}?ref=main")
    tree = github("POST", "/git/trees", {"tree": [
        {"path": path, "mode": "100644", "type": "blob", "sha": meta["sha"]}]})
    commit = github("POST", "/git/commits", {
        "message": f"CDN copy of {path} (for jsDelivr; main is unchanged)", "tree": tree["sha"]})
    try:
        github("PATCH", f"/git/refs/heads/{CDN_BRANCH}", {"sha": commit["sha"], "force": True})
    except urllib.error.HTTPError:
        github("POST", "/git/refs", {"ref": f"refs/heads/{CDN_BRANCH}", "sha": commit["sha"]})
    new = f"https://cdn.jsdelivr.net/gh/{GH_REPO}@{commit['sha']}/{path}"
    # warm jsDelivr so the platform's fetch is quick (best effort)
    try:
        urllib.request.urlopen(urllib.request.Request(new, method="HEAD",
                               headers={"User-Agent": "ZudoWorksVideoPoster/1.0"}), timeout=60)
    except Exception as e:
        log(f"jsDelivr warm-up for {path}: {e}")
    return new


def run_scenario(item):
    video_url = item.get("video_url", "")
    try:
        video_url = small_cdn_url(video_url)
    except Exception as e:
        log(f"could not make a small CDN link, using the original: {e}")
    data = {
        "target": item["target"],
        "video_url": video_url,
        "caption": item.get("caption", ""),
        "title": item.get("title", ""),
        "cover_ms": item.get("cover_ms", 3000),
    }
    return make("POST", f"/scenarios/{SCENARIO_ID}/run",
                {"data": data, "responsive": False})


def execution_status(exec_id):
    """Returns (status, error_text). status: RUNNING / SUCCESS / WARNING / ERROR / UNKNOWN."""
    code, body = make("GET", f"/scenarios/{SCENARIO_ID}/executions/{exec_id}")
    if code == 200 and isinstance(body, dict):
        st = str(body.get("status", "")).upper()
        err = body.get("error")
        if isinstance(err, dict):
            err = err.get("message") or json.dumps(err)[:400]
        return (st or "UNKNOWN"), (err or "")
    # fall back to the execution log endpoint
    code, body = make("GET", f"/scenarios/{SCENARIO_ID}/logs/{exec_id}")
    if code == 200 and isinstance(body, dict):
        b = body.get("scenarioLog", body)
        ds = str(b.get("displayStatus", "")).upper()
        if not ds:
            ds = {1: "SUCCESS", 2: "WARNING", 3: "ERROR"}.get(b.get("status"), "RUNNING")
        if ds == "WAITING":
            ds = "RUNNING"
        err = b.get("interruptReason") or ""
        if ds == "ERROR" and not err:
            err = f"failed at module {b.get('interruptModuleName') or b.get('interruptModuleId') or '?'}"
        return ds, str(err)
    return "UNKNOWN", ""


def wait_for(exec_id):
    deadline = time.time() + POLL_SECONDS
    status, err = "UNKNOWN", ""
    time.sleep(15)
    while time.time() < deadline:
        status, err = execution_status(exec_id)
        if status in ("SUCCESS", "WARNING", "ERROR"):
            return status, err
        time.sleep(15)
    return status, err


# ---------------------------------------------------------------- queue + git

def git(*args, check=True):
    return subprocess.run(["git", *args], check=check, capture_output=True, text=True)


def load():
    with open(QUEUE, encoding="utf-8") as f:
        q = json.load(f)
    q.setdefault("slots", {})
    return q


def save(q):
    with open(QUEUE, "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)
        f.write("\n")


def commit_change(apply, message):
    """Re-read the latest queue from main, apply a change, commit and push.

    apply(queue) -> bool (False = nothing to change any more). Retries on push races,
    re-applying the change to the fresh file each time so nobody's edits are lost.
    Returns True when the change is on main.
    """
    for attempt in range(6):
        git("fetch", "--depth", "1", "origin", "main")
        git("reset", "--hard", "origin/main")
        q = load()
        if not apply(q):
            return False
        save(q)
        git("add", QUEUE)
        if git("diff", "--cached", "--quiet", check=False).returncode == 0:
            return True
        git("commit", "-m", message)
        p = git("push", "origin", "HEAD:main", check=False)
        if p.returncode == 0:
            return True
        log(f"push race, retrying ({attempt + 1}): {p.stderr.strip()[:200]}")
        time.sleep(3 + attempt * 2)
    raise RuntimeError("could not push queue change after 6 attempts")


def find(q, slot_id, idx):
    try:
        return q["slots"][slot_id]["items"][idx]
    except (KeyError, IndexError):
        return None


def set_fields(slot_id, idx, expect_status, fields, message):
    def apply(q):
        it = find(q, slot_id, idx)
        if it is None or (expect_status and it.get("status") != expect_status):
            return False
        it.update(fields)
        return True
    return commit_change(apply, message)


# ---------------------------------------------------------------- main logic

def finish(slot_id, idx, item, status, err, exec_id):
    label = f"{item['target']} {slot_id}"
    if status in ("SUCCESS", "WARNING"):
        set_fields(slot_id, idx, "posting",
                   {"status": "done", "exec_id": exec_id,
                    "note": "posted" + (" (warning)" if status == "WARNING" else "")},
                   f"Video poster: posted {label}")
        log(f"POSTED {label} (exec {exec_id})")
        return
    reason = (err or "Make run failed").strip().replace("\n", " ")[:300]
    if AUTH.search(reason):
        set_fields(slot_id, idx, "posting",
                   {"status": "failed", "exec_id": exec_id, "note": f"auth: {reason}"},
                   f"Video poster: failed {label}")
        log(f"FAILED {label}: reconnect needed – {reason}")
    elif TEMPORARY.search(reason) and not str(item.get("note", "")).startswith("retry"):
        new_due = iso(now_utc() + RETRY_DELAY)
        set_fields(slot_id, idx, "posting",
                   {"status": "pending", "due_utc": new_due, "exec_id": exec_id,
                    "note": f"retry: {reason}"},
                   f"Video poster: retry later {label}")
        log(f"RETRY {label} at {new_due}: {reason}")
    else:
        set_fields(slot_id, idx, "posting",
                   {"status": "failed", "exec_id": exec_id, "note": reason},
                   f"Video poster: failed {label}")
        log(f"FAILED {label}: {reason}")


def resolve_stuck(q):
    """Items left in 'posting' by an earlier run that stopped before it finished."""
    now = now_utc()
    for slot_id, slot in q["slots"].items():
        for idx, it in enumerate(slot.get("items", [])):
            if it.get("status") != "posting":
                continue
            exec_id = it.get("exec_id") or ""
            if exec_id:
                status, err = execution_status(exec_id)
                if status in ("SUCCESS", "WARNING", "ERROR"):
                    finish(slot_id, idx, it, status, err, exec_id)
                elif parse(it.get("posting_at", iso(now))) < now - timedelta(hours=2):
                    set_fields(slot_id, idx, "posting",
                               {"status": "failed",
                                "note": f"Make run {exec_id} never finished – check in Make"},
                               f"Video poster: failed {it['target']} {slot_id}")
                    log(f"FAILED {it['target']} {slot_id}: Make run never finished")
            elif parse(it.get("posting_at", iso(now))) < now - STUCK_AFTER:
                # We don't know whether Make received it: never post twice, flag instead.
                set_fields(slot_id, idx, "posting",
                           {"status": "failed",
                            "note": "poster stopped mid-post – check the platform before reposting"},
                           f"Video poster: failed {it['target']} {slot_id}")
                log(f"FAILED {it['target']} {slot_id}: poster stopped mid-post")


def post_due():
    q = load()
    resolve_stuck(q)
    q = load()
    now = now_utc()

    due, missed = [], []
    for slot_id, slot in q["slots"].items():
        for idx, it in enumerate(slot.get("items", [])):
            if it.get("status") != "pending" or not it.get("due_utc"):
                continue
            d = parse(it["due_utc"])
            if d > now:
                continue
            (missed if now - d > MISSED_AFTER else due).append((d, slot_id, idx))

    for _, slot_id, idx in missed:
        it = find(q, slot_id, idx)
        set_fields(slot_id, idx, "pending", {"status": "failed", "note": "missed window"},
                   f"Video poster: missed window {it['target']} {slot_id}")
        log(f"MISSED {it['target']} {slot_id} (more than 6 h late, not posted)")

    if not due:
        log("Nothing due.")
        return

    due.sort()
    last_on = {}
    for _, slot_id, idx in due[:MAX_PER_RUN]:
        it = find(load(), slot_id, idx)
        if not it or it.get("status") != "pending":
            continue
        tgt = it["target"]
        if tgt in last_on:
            gap = SAME_PLATFORM_GAP - (time.time() - last_on[tgt])
            if gap > 0:
                time.sleep(gap)

        # claim it first, so no other run can post it too
        if not set_fields(slot_id, idx, "pending",
                          {"status": "posting", "posting_at": iso(now_utc())},
                          f"Video poster: posting {tgt} {slot_id}"):
            continue

        code, body = run_scenario(it)
        exec_id = str(body.get("executionId", "")) if isinstance(body, dict) else ""
        if code not in (200, 201, 202) or not exec_id:
            msg = body.get("message") if isinstance(body, dict) else str(body)
            reason = f"Make API {code}: {msg or body}"
            if code in (401, 403):
                reason += " (check the MAKE_API_TOKEN secret)"
            # Make never started the run, so putting it back is safe
            if code in (0, 429) or code >= 500:
                if str(it.get("note", "")).startswith("retry"):
                    set_fields(slot_id, idx, "posting", {"status": "failed", "note": reason[:300]},
                               f"Video poster: failed {tgt} {slot_id}")
                    log(f"FAILED {tgt} {slot_id}: {reason}")
                else:
                    new_due = iso(now_utc() + RETRY_DELAY)
                    set_fields(slot_id, idx, "posting",
                               {"status": "pending", "due_utc": new_due,
                                "note": f"retry: {reason}"[:300]},
                               f"Video poster: retry later {tgt} {slot_id}")
                    log(f"RETRY {tgt} {slot_id} at {new_due}: {reason}")
            else:
                set_fields(slot_id, idx, "posting", {"status": "failed", "note": reason[:300]},
                           f"Video poster: failed {tgt} {slot_id}")
                log(f"FAILED {tgt} {slot_id}: {reason}")
            continue

        set_fields(slot_id, idx, "posting", {"exec_id": exec_id},
                   f"Video poster: Make run started {tgt} {slot_id}")
        status, err = wait_for(exec_id)
        last_on[tgt] = time.time()
        if status in ("SUCCESS", "WARNING", "ERROR"):
            finish(slot_id, idx, it, status, err, exec_id)
        else:
            log(f"STILL RUNNING {tgt} {slot_id} (exec {exec_id}); next run will check it")


def check():
    code, body = make("GET", f"/scenarios/{SCENARIO_ID}")
    sc = body.get("scenario", {}) if isinstance(body, dict) else {}
    result = {
        "checked_at": iso(now_utc()),
        "make_api_ok": code == 200,
        "http_status": code,
        "scenario_id": SCENARIO_ID,
        "scenario_name": sc.get("name", ""),
        "scenario_active": sc.get("isActive", None),
        "message": "" if code == 200 else str(body.get("message", body))[:300],
    }
    with open(CHECK_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    git("add", CHECK_FILE)
    if git("diff", "--cached", "--quiet", check=False).returncode != 0:
        git("commit", "-m", "Video poster: connection check")
        git("push", "origin", "HEAD:main", check=False)
    log(f"Make API check: HTTP {code} {result['scenario_name']} {result['message']}")
    return code == 200


def main():
    if not TOKEN:
        log("MAKE_API_TOKEN secret is missing.")
        sys.exit(1)
    git("config", "user.name", "Zudo Works video poster")
    git("config", "user.email", "video-poster@users.noreply.github.com")
    ok = True
    try:
        if os.environ.get("MODE", "post") == "check":
            ok = check()
        else:
            post_due()
    finally:
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as f:
                f.write("### Zudo Works video poster\n\n")
                f.write("\n".join(f"- {l}" for l in log_lines) + "\n")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
