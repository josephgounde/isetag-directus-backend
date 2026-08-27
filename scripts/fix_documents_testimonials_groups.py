#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fixes the Content-nav folder placement of `documents` and `testimonials`
-- caught 2026-08-27 by direct user question ("why did you put a file field
type in actualite Document collection??"). Both predate this session and
were left grouped under "Actualites", a leftover from an old "Ressources"
folder merge -- their actual content has nothing to do with the Actualites
page (confirmed: it has no documents library or testimonials carousel).

Real usage: documents feeds the Admissions downloadable-documents section
(filter[category][_eq]=admission); testimonials feeds the Accueil news
carousel and per-filiere testimonials on Fiche filiere.

meta.group only -- no data touched. Idempotent."""
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

FIXES = {
    "documents": "Admissions",
    "testimonials": "Accueil & Global",
}


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


def main():
    token = login()
    print("login OK")
    for collection, group in FIXES.items():
        status, resp = api("GET", f"/collections/{collection}", token)
        if status >= 400:
            print(f"  !! {collection} not found, skipping")
            continue
        current = (resp["data"]["meta"] or {}).get("group")
        if current == group:
            print(f"  = {collection} already in '{group}'")
            continue
        status, resp = api("PATCH", f"/collections/{collection}", token, {"meta": {"group": group}})
        if status >= 400:
            print(json.dumps(resp, indent=2)); sys.exit(1)
        print(f"  {collection}: '{current}' -> '{group}'")
    print("DONE")


if __name__ == "__main__":
    main()
