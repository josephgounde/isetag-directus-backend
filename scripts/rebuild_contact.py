#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builds the Contact page (dev first): contact_hero collection (hero heading
+ subtitle above the contact form -- no image, no CTA, matching the Figma
design at https://www.figma.com/design/kEkYbSJe16rNaEnZRwOTZE), makes
contact_messages.email required (form field, decided with user since the
Figma form itself has no email field but replies need one), and wires the
Contact page's sections: contact_hero (new) + the SAME shared
accueil_cta_banner id=2 row already used by Accueil's bottom CTA (confirmed
identical banner reused across Accueil/Programmes/Actualites/Contact, not a
new page-scoped collection)."""
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


def ensure_collection(token):
    status, _ = api("GET", "/collections/contact_hero", token)
    if status < 400:
        print("= collection contact_hero already exists")
        return
    body = {
        "collection": "contact_hero",
        "meta": {"note": "Section hero de la page Contact (au-dessus du formulaire).", "group": "Contact", "icon": "mail"},
        "schema": {},
        "fields": [
            {"field": "id", "type": "integer", "meta": {"hidden": True, "interface": "input"}, "schema": {"is_primary_key": True, "has_auto_increment": True}},
        ],
    }
    status, resp = api("POST", "/collections", token, body)
    if status >= 400:
        print(json.dumps(resp, indent=2)); sys.exit(1)
    print("+ collection contact_hero created")


def ensure_field(token, collection, field, ftype, meta=None, schema=None):
    status, _ = api("GET", f"/fields/{collection}/{field}", token)
    if status < 400:
        return
    status, resp = api("POST", f"/fields/{collection}", token,
                        {"field": field, "type": ftype, "meta": meta or {}, "schema": schema or {}})
    if status >= 400:
        print(json.dumps(resp, indent=2)); sys.exit(1)
    print(f"  + field {collection}.{field} created")


def grant_public_read(token, collection):
    status, resp = api("GET", "/policies?filter[name][_eq]=$t:public_label&fields=id", token)
    policy_id = resp["data"][0]["id"]
    status, resp = api("GET", f"/permissions?filter[policy][_eq]={policy_id}&filter[collection][_eq]={collection}&filter[action][_eq]=read", token)
    if resp.get("data"):
        print(f"  = public read already granted on {collection}")
        return
    body = {"policy": policy_id, "collection": collection, "action": "read", "fields": ["*"], "permissions": {}, "validation": {}}
    status, resp = api("POST", "/permissions", token, body)
    if status >= 400:
        print(json.dumps(resp, indent=2)); sys.exit(1)
    print(f"  + public read granted on {collection}")


def ensure_m2a_allows(token, collection):
    # NB: for an M2A field, one_allowed_collections lives on the RELATION
    # (/relations/pages_sections/item), not on the field's own meta. PATCHing
    # /fields/pages_sections/item silently does not persist it (found the hard
    # way rebuilding Contact 2026-08-27 -- see ISETAG_project_instructions.md).
    status, resp = api("GET", "/relations/pages_sections/item", token)
    if status >= 400:
        print(json.dumps(resp, indent=2)); sys.exit(1)
    meta = resp["data"]["meta"]
    allowed = list(meta.get("one_allowed_collections") or [])
    if collection in allowed:
        print(f"  = {collection} already in pages_sections.item one_allowed_collections")
        return
    allowed.append(collection)
    status, resp = api("PATCH", "/relations/pages_sections/item", token, {"meta": {"one_allowed_collections": allowed}})
    if status >= 400:
        print(json.dumps(resp, indent=2)); sys.exit(1)
    print(f"  + {collection} added to pages_sections.item one_allowed_collections")


def upsert_row(token, collection, row_id, body):
    status, _ = api("GET", f"/items/{collection}/{row_id}", token)
    if status < 400:
        status, resp = api("PATCH", f"/items/{collection}/{row_id}", token, body)
    else:
        body = {**body, "id": row_id}
        status, resp = api("POST", f"/items/{collection}", token, body)
    if status >= 400:
        print(json.dumps(resp, indent=2)); sys.exit(1)
    print(f"  = {collection}/{row_id} upserted")
    return resp["data"]


def ensure_page_section(token, pages_id, collection, item, sort):
    q = urllib.parse.urlencode({
        "filter[pages_id][_eq]": pages_id,
        "filter[collection][_eq]": collection,
        "filter[item][_eq]": str(item),
        "fields": "id",
    })
    status, resp = api("GET", f"/items/pages_sections?{q}", token)
    if resp.get("data"):
        print(f"  = pages_sections {collection}/{item} already wired to page {pages_id}")
        return
    body = {"pages_id": pages_id, "collection": collection, "item": str(item), "sort": sort}
    status, resp = api("POST", "/items/pages_sections", token, body)
    if status >= 400:
        print(json.dumps(resp, indent=2)); sys.exit(1)
    print(f"  + pages_sections {collection}/{item} wired to page {pages_id} (sort={sort})")


def main():
    token = login()
    print("login OK")

    print("\n== 1. Collection + fields ==")
    ensure_collection(token)
    ensure_field(token, "contact_hero", "title_fr", "string", {"interface": "input"})
    ensure_field(token, "contact_hero", "title_en", "string", {"interface": "input"})
    ensure_field(token, "contact_hero", "subtitle_fr", "string", {"interface": "input"})
    ensure_field(token, "contact_hero", "subtitle_en", "string", {"interface": "input"})

    print("\n== 2. Permissions ==")
    grant_public_read(token, "contact_hero")

    print("\n== 3. M2A allowlist (pages_sections.item) ==")
    ensure_m2a_allows(token, "contact_hero")

    print("\n== 4. Content (idempotent upsert on id=1) ==")
    upsert_row(token, "contact_hero", 1, {
        "title_fr": "Une question ou préoccupation ?",
        "subtitle_fr": "Ecrivez-nous directement",
    })

    print("\n== 5. contact_messages.email -> required ==")
    status, resp = api("PATCH", "/fields/contact_messages/email", token, {"meta": {"required": True}})
    if status >= 400:
        print(json.dumps(resp, indent=2)); sys.exit(1)
    print("  = contact_messages.email now required")

    print("\n== 6. Wire Contact page sections ==")
    status, resp = api("GET", "/items/pages?filter[key][_eq]=contact&fields=id", token)
    pages_id = resp["data"][0]["id"]
    ensure_page_section(token, pages_id, "contact_hero", 1, 1)
    ensure_page_section(token, pages_id, "accueil_cta_banner", 2, 2)

    print("\nDONE")


if __name__ == "__main__":
    main()
