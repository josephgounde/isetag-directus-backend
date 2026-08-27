#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wires programmes_hero into pages.programmes.sections -- it existed with
real content on dev and prod but was never linked to the page (found
2026-08-27 while reviewing the Programmes page structure). Adds it to the
pages_sections.item M2A allowlist first (on the relation, not the field --
see directus_singleton_gotcha.md)."""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("TARGET_BASE_URL", "http://localhost:8055").rstrip("/")
ENV_PATH = os.environ.get("ENV_PATH", r"J:\SiteWeb_ISETAG\Directus-backend\.env")

if "DIRECTUS_ADMIN_EMAIL" in os.environ:
    EMAIL = os.environ["DIRECTUS_ADMIN_EMAIL"]
    PASSWORD = os.environ["DIRECTUS_ADMIN_PASSWORD"]
else:
    env = {}
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            m = re.match(r"^([A-Z_]+)=(.*)$", line)
            if m:
                env[m.group(1)] = m.group(2)
    EMAIL = env["DIRECTUS_ADMIN_EMAIL"]
    PASSWORD = env["DIRECTUS_ADMIN_PASSWORD"]


def api(method, path, token, body=None, retries=6, delay=1.0):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, method=method)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read()
                return resp.status, (json.loads(raw) if raw else {})
        except urllib.error.HTTPError as e:
            raw = e.read()
            parsed = json.loads(raw) if raw else {}
            last = (e.code, parsed)
            if e.code in (400, 403) and "exist" in json.dumps(parsed) and attempt < retries - 1:
                time.sleep(delay)
                continue
            return last
    return last


def login():
    status, resp = api("POST", "/auth/login", None, {"email": EMAIL, "password": PASSWORD})
    if status >= 400:
        print(json.dumps(resp, indent=2)); sys.exit(1)
    return resp["data"]["access_token"]


def main():
    token = login()
    print("login OK,", BASE)

    status, resp = api("GET", "/relations/pages_sections/item", token)
    allowed = list(resp["data"]["meta"]["one_allowed_collections"] or [])
    if "programmes_hero" not in allowed:
        allowed.append("programmes_hero")
        status, resp = api("PATCH", "/relations/pages_sections/item", token, {"meta": {"one_allowed_collections": allowed}})
        if status >= 400:
            print(json.dumps(resp, indent=2)); sys.exit(1)
        print("  + programmes_hero added to pages_sections.item allowlist")
    else:
        print("  = programmes_hero already in allowlist")

    status, resp = api("GET", "/items/pages?filter[key][_eq]=programmes&fields=id", token)
    pages_id = resp["data"][0]["id"]

    q = f"filter[pages_id][_eq]={pages_id}&filter[collection][_eq]=programmes_hero&filter[item][_eq]=1"
    status, resp = api("GET", f"/items/pages_sections?{q}", token)
    if resp.get("data"):
        print(f"  = programmes_hero/1 already wired to page {pages_id}")
    else:
        status, resp = api("POST", "/items/pages_sections", token, {
            "pages_id": pages_id, "collection": "programmes_hero", "item": "1", "sort": 1,
        })
        if status >= 400:
            print(json.dumps(resp, indent=2)); sys.exit(1)
        print(f"  + programmes_hero/1 wired to page {pages_id} (sort=1)")

    print("DONE")


if __name__ == "__main__":
    main()
