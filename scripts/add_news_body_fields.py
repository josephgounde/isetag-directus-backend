#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adds body_fr/body_en (WYSIWYG rich text, mirrors admissions_richtext's
content_fr pattern: type text + interface input-rich-text-html) to `news`.
Requested 2026-08-27: "add a text field to the news collection for the real
article content that will be displayed on another view by the frontend
team" -- i.e. a future per-article detail page, distinct from the existing
`content_fr` (plain text) which stays the short excerpt used on the "A la
Une"/"Lire Aussi" cards."""
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
    print("\n== Fields ==")
    ensure_field(token, "news", "body_fr", "text", {
        "interface": "input-rich-text-html",
        "note": "Contenu integral de l'article (page de detail), distinct de "
                "content_fr qui reste l'extrait affiche sur les cartes A la "
                "Une / Lire Aussi.",
    })
    ensure_field(token, "news", "body_en", "text", {
        "interface": "input-rich-text-html",
        "note": "Full article body (English).",
    })
    print("\nDONE")


if __name__ == "__main__":
    main()
