#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adds `featured` (boolean, matching testimonials.featured) and `status`
(published/draft/archived, matching documents/scholarships/tuition_plans) to
`news` -- caught 2026-08-27 while explaining the Actualites "Lire Aussi" grid:
news had no editorial way to pick the "A la Une" article and no draft/publish
control at all (every row was public the instant it was created). Sets the
existing GAP Motors row to status=published, featured=true, and tightens the
public read permission to filter[status][_eq]=published."""
import json
import os
import re
import sys
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


def api(method, path, token, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
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
        return e.code, (json.loads(raw) if raw else {})


def login():
    status, resp = api("POST", "/auth/login", None, {"email": EMAIL, "password": PASSWORD})
    if status >= 400:
        print(json.dumps(resp, indent=2)); sys.exit(1)
    return resp["data"]["access_token"]


def ensure_field(token, collection, field, ftype, meta=None, schema=None):
    status, _ = api("GET", f"/fields/{collection}/{field}", token)
    if status < 400:
        print(f"  = field {collection}.{field} already exists")
        return
    status, resp = api("POST", f"/fields/{collection}", token,
                        {"field": field, "type": ftype, "meta": meta or {}, "schema": schema or {}})
    if status >= 400:
        print(json.dumps(resp, indent=2)); sys.exit(1)
    print(f"  + field {collection}.{field} created")


def main():
    token = login()
    print("login OK")

    print("\n== 1. Fields ==")
    ensure_field(token, "news", "featured", "boolean",
                 {"interface": "boolean", "special": ["cast-boolean"]}, {"default_value": False})
    ensure_field(token, "news", "status", "string",
                 {"interface": "select-dropdown", "display": "labels",
                  "options": {"choices": [
                      {"text": "published", "value": "published"},
                      {"text": "draft", "value": "draft"},
                      {"text": "archived", "value": "archived"},
                  ]}},
                 {"default_value": "draft"})

    print("\n== 2. Backfill existing rows (mark real content published/featured) ==")
    status, resp = api("GET", "/items/news?limit=-1&fields=id,status,featured", token)
    for row in resp["data"]:
        if row.get("status") is None:
            api("PATCH", f"/items/news/{row['id']}", token, {"status": "published"})
            print(f"  = news/{row['id']} -> status=published")

    print("\n== 3. Tighten public read permission ==")
    status, resp = api("GET", "/policies?filter[name][_eq]=$t:public_label&fields=id", token)
    policy_id = resp["data"][0]["id"]
    status, resp = api("GET", f"/permissions?filter[policy][_eq]={policy_id}&filter[collection][_eq]=news&filter[action][_eq]=read", token)
    if resp.get("data"):
        perm_id = resp["data"][0]["id"]
        api("PATCH", f"/permissions/{perm_id}", token, {"permissions": {"status": {"_eq": "published"}}})
        print("  = news read permission filtered to status=published")
    else:
        print("  !! no existing public read permission on news -- run provision_public_read.py first")

    print("\nDONE")


if __name__ == "__main__":
    main()
