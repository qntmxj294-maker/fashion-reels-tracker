#!/usr/bin/env python3
"""Budget-reserved collection of public reels. Python standard library only."""
import argparse
import datetime as dt
from decimal import Decimal
import json
import math
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
UTC = dt.timezone.utc
KST = dt.timezone(dt.timedelta(hours=9))
MIN_VIEWS = 10_000_000
PROVIDERS = {"filtered": "themineworks~instagram-reels-views-scraper",
             "apify": "apify~instagram-reel-scraper"}

def read(path, default=None):
    if not path.exists():
        return default
    # Broken files must not silently reset the spending ledger.
    return json.loads(path.read_text(encoding="utf-8"))

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)

def api(token, path, payload=None):
    request = urllib.request.Request("https://api.apify.com/v2/" + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=280) as response:
        return json.load(response)

def config():
    cfg = read(ROOT / "config.json")
    if not isinstance(cfg, dict) or cfg.get("provider") not in PROVIDERS:
        raise ValueError("Invalid provider/config")
    for key, maximum in (("accounts_per_day", 4), ("max_reels_per_profile", 1000), ("newer_than_days", 3650)):
        value = cfg.get(key)
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError("Invalid " + key)
    per, budget = Decimal(str(cfg.get("per_account_cap_usd"))), Decimal(str(cfg.get("rolling_31_day_cap_usd")))
    if not per.is_finite() or not budget.is_finite() or not Decimal("0.01") <= per <= Decimal("0.10") or not per <= budget <= Decimal("3"):
        raise ValueError("Per-account $0.01–$0.10; rolling 31-day budget <= $3")
    return cfg

def accounts():
    raw = read(ROOT / "accounts.json", [])
    if not isinstance(raw, list):
        raise ValueError("Account list required")
    result = []
    for value in raw:
        if not isinstance(value, str) or not re.fullmatch(r"@?[A-Za-z0-9._]{1,30}", value.strip()):
            raise ValueError("Invalid account handle")
        handle = value.strip().lstrip("@").lower()
        if handle not in result:
            result.append(handle)
    return result

def reserve(state, handles, cfg, now, run_id):
    day = now.astimezone(KST).date().isoformat()
    ledger = state.setdefault("reservations", [])
    if any(r["day_kst"] == day or r["id"] == run_id for r in ledger):
        return None
    cutoff = now - dt.timedelta(days=31)
    used = sum((Decimal(str(r["cap_usd"])) for r in ledger
                if dt.datetime.fromisoformat(r["reserved_at"]) > cutoff), Decimal(0))
    per = Decimal(str(cfg["per_account_cap_usd"]))
    remaining = Decimal(str(cfg["rolling_31_day_cap_usd"])) - used
    count = min(len(handles), cfg["accounts_per_day"], max(0, int(remaining // per)))
    if not count:
        return None
    cursor = state.get("cursor", 0) % len(handles)
    selected = [handles[(cursor + i) % len(handles)] for i in range(count)]
    entry = {"id": run_id, "day_kst": day, "reserved_at": now.isoformat(),
             "accounts": selected, "config": cfg, "cap_usd": float(per * count),
             "per_account_cap_usd": str(per), "status": "reserved"}
    ledger.append(entry)
    state["cursor"] = (cursor + count) % len(handles)
    return entry

def prepare(run_id):
    cfg, handles = config(), accounts()
    token = os.getenv("APIFY_TOKEN", "").strip()
    if not token or not handles:
        print("No token/accounts: automatic collection disabled; manual mode available.")
        return
    # The response includes private data: never print it.
    plan = api(token, "users/me").get("data", {}).get("plan", {})
    if plan.get("tier") != "FREE" or plan.get("monthlyBasePriceUsd") != 0:
        raise ValueError("Cannot verify a Free plan; refusing actor execution")
    state = read(ROOT / "data/budget.json", {"cursor": 0, "reservations": []})
    entry = reserve(state, handles, cfg, dt.datetime.now(UTC), run_id)
    if entry:
        write(ROOT / "data/budget.json", state)
        print(f"Reserved ${entry['cap_usd']:.2f} for {len(entry['accounts'])} accounts.")
    else:
        print("Skipped: already reserved today or rolling budget exhausted.")

def numeric(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0

def normalize(row, checked, provider, fallback=""):
    if not isinstance(row, dict):
        return None
    if provider == "filtered":
        views, field = row.get("play_count"), "play_count"
        code = row.get("shortcode", "")
        username = row.get("username") or row.get("owner_username") or fallback
        likes, comments, posted = row.get("like_count"), row.get("comment_count"), row.get("taken_at")
    else:
        if row.get("productType") != "clips":
            return None
        field = "videoPlayCount" if numeric(row.get("videoPlayCount")) else "videoViewCount"
        views, code = row.get(field), row.get("shortCode", "")
        username = row.get("ownerUsername") or fallback
        likes, comments, posted = row.get("likesCount"), row.get("commentsCount"), row.get("timestamp")
    if not numeric(views) or views < MIN_VIEWS:
        return None
    if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", code):
        url = row.get("url", "")
        match = re.fullmatch(r"https://www\.instagram\.com/reel/([A-Za-z0-9_-]+)/?(?:\?.*)?", url) if isinstance(url, str) else None
        if not match:
            return None
        code = match[1]
    return {"id": code, "url": f"https://www.instagram.com/reel/{code}/", "username": str(username),
            "views": int(views), "metric": field, "likes": likes if numeric(likes) else None,
            "comments": comments if numeric(comments) else None,
            "posted_at": posted, "checked_at": checked, "source": "auto:" + provider}

def merge(old, rows):
    merged = {r["id"]: r for r in old if isinstance(r, dict) and isinstance(r.get("id"), str)}
    added = 0
    for item in rows:
        previous = merged.get(item["id"], {})
        added += not bool(previous)
        merged[item["id"]] = {**previous, **item,
            "first_found_at": previous.get("first_found_at") or item["checked_at"]}
    return sorted(merged.values(), key=lambda r: r.get("views", 0), reverse=True)[:2000], added

def collect(run_id):
    state = read(ROOT / "data/budget.json", {})
    entry = next((r for r in state.get("reservations", []) if r["id"] == run_id), None)
    if not entry or entry["status"] != "reserved":
        print("No unconsumed reservation for this execution. No actor started.")
        return
    if entry["day_kst"] != dt.datetime.now(KST).date().isoformat():
        raise ValueError("Reservation expired")
    token = os.getenv("APIFY_TOKEN", "").strip()
    if not token:
        raise ValueError("Token missing")
    entry["status"] = "started"
    write(ROOT / "data/budget.json", state)
    cfg, provider = entry["config"], entry["config"]["provider"]
    checked = dt.datetime.now(UTC).isoformat()
    data = read(ROOT / "data/reels.json", {"items": []})
    status = {"last_attempt_at": checked, "provider": provider, "accounts": [],
              "reserved_cap_usd": entry["cap_usd"], "rolling_31_day_cap_usd": cfg["rolling_31_day_cap_usd"]}
    successes = 0
    for handle in entry["accounts"]:
        report, items = {"username": handle, "status": "error"}, []
        try:
            if provider == "filtered":
                payload = {"usernames": [handle], "maxReelsPerProfile": cfg["max_reels_per_profile"],
                           "newerThanDays": cfg["newer_than_days"], "minViews": MIN_VIEWS,
                           "skipPinned": False, "includeReelDetails": False}
            else:
                payload = {"username": [handle], "resultsLimit": cfg["max_reels_per_profile"],
                           "onlyPostsNewerThan": (dt.datetime.now(UTC) - dt.timedelta(days=cfg["newer_than_days"])).date().isoformat(),
                           "skipPinnedPosts": False, "includeSharesCount": False, "includeTranscript": False}
            query = urllib.parse.urlencode({"maxTotalChargeUsd": entry["per_account_cap_usd"], "timeout": 240})
            rows = api(token, "acts/" + PROVIDERS[provider] + "/run-sync-get-dataset-items?" + query, payload)
            if not isinstance(rows, list):
                raise ValueError("Unexpected dataset")
            items = [item for row in rows if (item := normalize(row, checked, provider, handle))]
            successes += 1
            report.update(status="response_received", returned=len(rows), qualifying=len(items),
                note="Budget-limited output; an empty dataset does not prove no popular reels exist.")
        except urllib.error.HTTPError as error:
            report["error"] = "HTTP " + str(error.code)
        except Exception as error:
            report["error"] = type(error).__name__
        status["accounts"].append(report)
        data["items"], added = merge(data.get("items", []), items)
        status["new_items"] = status.get("new_items", 0) + added
        data["monitored_accounts"] = accounts()
        if report["status"] == "response_received":
            data["last_api_response_at"] = checked
        write(ROOT / "data/reels.json", data)
        write(ROOT / "data/status.json", status)
    entry["status"] = "complete" if successes == len(entry["accounts"]) else "partial_or_failed"
    entry["finished_at"] = dt.datetime.now(UTC).isoformat()
    write(ROOT / "data/budget.json", state)
    print(f"API responses: {successes}/{len(entry['accounts'])}; new rows: {status.get('new_items', 0)}.")
    if successes != len(entry["accounts"]):
        raise RuntimeError("Some accounts failed; previous data retained")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "collect", "dry-run"])
    args = parser.parse_args()
    run_id = os.getenv("COLLECTION_RUN_ID", "local-" + dt.datetime.now(KST).date().isoformat())
    if args.mode == "dry-run":
        cfg, handles = config(), accounts()
        state = read(ROOT / "data/budget.json", {"cursor": 0, "reservations": []})
        entry = reserve(state, handles, cfg, dt.datetime.now(UTC), run_id) if handles else None
        print(json.dumps({"no_network_calls": True, "plan": entry}, ensure_ascii=False, indent=2))
    elif args.mode == "prepare":
        prepare(run_id)
    else:
        collect(run_id)

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Stopped: " + type(error).__name__ + ". Check configuration, Free plan and Actions status.", file=sys.stderr)
        sys.exit(1)
