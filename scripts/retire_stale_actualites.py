#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""User-confirmed (2026-08-27): delete actualites_testimonials_highlight (+
its junction actualites_testimonials_highlight_testimonials) and
actualites_documents_list -- both 0 rows, no counterpart in the real Figma
design file for the Actualites page."""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
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


def revoke_public_read(token, collection):
    status, resp = api("GET", "/policies?filter[name][_eq]=$t:public_label&fields=id", token)
    policy_id = resp["data"][0]["id"]
    status, resp = api("GET", f"/permissions?filter[policy][_eq]={policy_id}&filter[collection][_eq]={collection}", token)
    for p in resp.get("data") or []:
        api("DELETE", f"/permissions/{p['id']}", token)
        print(f"  - permission removed on {collection} ({p['action']})")


def remove_m2a_allows(token, collection):
    status, resp = api("GET", "/relations/pages_sections/item", token)
    meta = resp["data"]["meta"]
    allowed = list(meta.get("one_allowed_collections") or [])
    if collection not in allowed:
        return
    allowed.remove(collection)
    status, resp = api("PATCH", "/relations/pages_sections/item", token, {"meta": {"one_allowed_collections": allowed}})
    if status >= 400:
        print(json.dumps(resp, indent=2)); sys.exit(1)
    print(f"  - {collection} removed from pages_sections.item one_allowed_collections")


def retire_collection(token, collection):
    status, _ = api("GET", "/collections/" + collection, token)
    if status >= 400:
        print(f"  = {collection} already gone")
        return
    status, resp = api("GET", f"/items/{collection}?limit=-1&fields=id", token)
    rows = resp.get("data") or []
    if rows:
        print(f"  !! {collection} has {len(rows)} row(s), refusing to auto-delete -- check manually")
        sys.exit(1)
    revoke_public_read(token, collection)
    remove_m2a_allows(token, collection)
    status, resp = api("DELETE", f"/collections/{collection}", token)
    if status >= 400:
        print(json.dumps(resp, indent=2)); sys.exit(1)
    print(f"  - collection {collection} deleted (was 0 rows, no counterpart in real Figma design)")


def main():
    token = login()
    print("login OK")
    retire_collection(token, "actualites_testimonials_highlight_testimonials")
    retire_collection(token, "actualites_testimonials_highlight")
    retire_collection(token, "actualites_documents_list")
    print("\nDONE")


if __name__ == "__main__":
    main()
