#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""User-confirmed (2026-08-27): retires poles.featured_name_fr/en,
poles.featured_description_fr/en, poles.tags_fr -- confirmed duplicate of
pole_filieres. Each pole's "featured" filiere text was copy-pasted verbatim
into featured_name_fr/featured_description_fr (e.g. Pole Industriel's
featured_description_fr is word-for-word identical to pole_filieres id=11),
and tags_fr just listed the OTHER filiere names as flat text with no links/
descriptions/images -- both fully superseded by the real pole_filieres
relational rows built after reviewing the actual Figma design file. Deletes
the fields (not the collection) on both dev and prod, one script, same
credential-override pattern as everything else in scripts/."""
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

FIELDS_TO_RETIRE = [
    "featured_name_fr",
    "featured_name_en",
    "featured_description_fr",
    "featured_description_en",
    "tags_fr",
]


def api(method, path, token, body=None, retries=6, delay=1.0):
    """Retries transient 400/403s whose message mentions the field/collection
    'exist' -- prod's schema cache has been observed flapping right after
    schema writes (2026-08-27, see ISETAG_project_instructions.md)."""
    import time
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
    for field in FIELDS_TO_RETIRE:
        status, _ = api("GET", f"/fields/poles/{field}", token)
        if status >= 400:
            print(f"  = poles.{field} already gone")
            continue
        status, resp = api("DELETE", f"/fields/poles/{field}", token)
        if status >= 400:
            print(json.dumps(resp, indent=2)); sys.exit(1)
        print(f"  - poles.{field} deleted")
    print("DONE")


if __name__ == "__main__":
    main()
