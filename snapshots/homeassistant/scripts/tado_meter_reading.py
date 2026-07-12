#!/usr/bin/env python3
"""Submit dated gas meter readings to Tado Energy IQ.

Uses its own Tado OAuth device-code grant, fully independent of the Home
Assistant tado integration (whose refresh token must never be shared, as
Tado rotates refresh tokens on every use).

Modes:
  --login                     One-time interactive device-code authorization.
                              Prints a verification URL to approve, then saves
                              the token file.
  --submit N --date YYYY-MM-DD [--dry-run]
                              Refresh the access token (rotating and saving the
                              refresh token) and POST a dated meter reading.
                              --dry-run authenticates and resolves the home id
                              but does not POST the reading.

Token state: /config/.tado_meter_token.json (chmod 600, never synced to git).
Exit codes: 0 success; 1 transient/HTTP failure (retry later); 2 auth dead
(token file missing/revoked - rerun --login).
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CLIENT_ID = "1bb50063-6b0c-4d11-bd99-387f4a91cc46"  # Tado public API client
LOGIN_BASE = "https://login.tado.com/oauth2"
API_BASE = "https://my.tado.com/api/v2"
EIQ_BASE = "https://energy-insights.tado.com/api"
TOKEN_FILE = os.environ.get("TADO_TOKEN_FILE", "/config/.tado_meter_token.json")


def http_json(url, data=None, headers=None, method=None):
    """POST form/JSON or GET; return (status, parsed-json-or-None)."""
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
            return resp.status, (json.loads(body) if body.strip() else None)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except ValueError:
            return e.code, {"raw": body[:500]}


def save_tokens(tokens):
    tmp = TOKEN_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(tokens, f, indent=1)
    os.chmod(tmp, 0o600)
    os.replace(tmp, TOKEN_FILE)


def load_tokens():
    if not os.path.exists(TOKEN_FILE):
        print(f"Token file {TOKEN_FILE} missing - run --login first.", file=sys.stderr)
        sys.exit(2)
    with open(TOKEN_FILE) as f:
        return json.load(f)


def login():
    status, dev = http_json(
        f"{LOGIN_BASE}/device_authorize",
        data={"client_id": CLIENT_ID, "scope": "offline_access"},
    )
    if status != 200:
        print(f"device_authorize failed ({status}): {dev}", file=sys.stderr)
        sys.exit(1)
    url = dev.get("verification_uri_complete") or dev.get("verification_uri")
    interval = int(dev.get("interval", 5))
    expires_in = int(dev.get("expires_in", 300))
    print(f"Approve this login within {expires_in // 60} minutes:\n\n  {url}\n", flush=True)

    deadline = time.time() + expires_in
    while time.time() < deadline:
        time.sleep(interval)
        status, tok = http_json(
            f"{LOGIN_BASE}/token",
            data={
                "client_id": CLIENT_ID,
                "device_code": dev["device_code"],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
        if status == 200:
            home_id = fetch_home_id(tok["access_token"])
            save_tokens({"refresh_token": tok["refresh_token"], "home_id": home_id})
            print(f"Login OK. Home id {home_id}. Token saved to {TOKEN_FILE}.")
            return
        err = (tok or {}).get("error", "")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            interval += 5
            continue
        print(f"Device flow failed ({status}): {tok}", file=sys.stderr)
        sys.exit(1)
    print("Login timed out before approval.", file=sys.stderr)
    sys.exit(1)


def fetch_home_id(access_token):
    status, me = http_json(
        f"{API_BASE}/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    if status != 200 or not me.get("homes"):
        print(f"Could not resolve home id ({status}): {me}", file=sys.stderr)
        sys.exit(1)
    return me["homes"][0]["id"]


def refresh_access_token():
    tokens = load_tokens()
    status, tok = http_json(
        f"{LOGIN_BASE}/token",
        data={
            "client_id": CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
        },
    )
    if status == 200:
        tokens["refresh_token"] = tok["refresh_token"]  # Tado rotates it
        save_tokens(tokens)
        return tok["access_token"], tokens["home_id"]
    if status in (400, 401) and (tok or {}).get("error") == "invalid_grant":
        print("Refresh token revoked/expired - rerun --login.", file=sys.stderr)
        sys.exit(2)
    print(f"Token refresh failed ({status}): {tok}", file=sys.stderr)
    sys.exit(1)


def submit(reading, date, dry_run):
    access_token, home_id = refresh_access_token()
    if dry_run:
        print(f"DRY RUN OK: would POST reading={reading} date={date} to home {home_id}.")
        return
    status, resp = http_json(
        f"{EIQ_BASE}/homes/{home_id}/meterReadings",
        data=json.dumps({"date": date, "reading": reading}).encode(),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    if status in (200, 201):
        print(f"Submitted reading={reading} date={date} to home {home_id}.")
        return
    print(f"Meter reading POST failed ({status}): {resp}", file=sys.stderr)
    sys.exit(1)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--login", action="store_true")
    p.add_argument("--submit", type=int, metavar="READING")
    p.add_argument("--date", metavar="YYYY-MM-DD")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.login:
        login()
    elif args.submit is not None:
        if not args.date:
            p.error("--submit requires --date")
        time.strptime(args.date, "%Y-%m-%d")  # validate format
        submit(args.submit, args.date, args.dry_run)
    else:
        p.error("choose --login or --submit")


if __name__ == "__main__":
    main()
