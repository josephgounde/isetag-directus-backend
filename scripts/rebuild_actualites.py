#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builds the Actualites page (dev first) from the real Figma design file
(node-id=6-461, frame "Actualites - Desktop"), not the old prototype-based
guess. Real structure: hero (title+subtitle+photo) -> "A la Une" (the single
featured news article, full-width) -> "Lire Aussi" (paginated grid of the
other news articles, 9/page, up to 7 pages in the mock) -> same shared CTA
banner as every other page -> sitewide footer.

"A la Une" and "Lire Aussi" are NOT page-builder blocks: they're a live
listing driven by the `news` collection itself (filter[featured][_eq]=true
for "A la Une" -- see scripts/add_news_featured_status.py, a manual editorial
choice, not just "whatever is most recent" -- rest sorted by date_published
for "Lire Aussi"), same pattern as poles/programs listings elsewhere in this
project. No new collection needed for them.

Also retires actualites_testimonials_highlight and actualites_documents_list:
both were created earlier from an OLDER prototype review, both still at 0
rows, and neither has any counterpart in this design file (no testimonials
carousel, no documents/ressources library on this page). Same precedent as
the 2026-08-03 accueil_news_preview/accueil_programs_highlight cleanup:
retire what doesn't exist in the real design rather than leave it as dead
schema someone might build against."""
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
    status, _ = api("GET", "/collections/actualites_hero", token)
    if status < 400:
        print("= collection actualites_hero already exists")
        return
    body = {
        "collection": "actualites_hero",
        "meta": {"note": "Section hero de la page Actualites.", "group": "Actualités", "icon": "newspaper"},
        "schema": {},
        "fields": [
            {"field": "id", "type": "integer", "meta": {"hidden": True, "interface": "input"}, "schema": {"is_primary_key": True, "has_auto_increment": True}},
        ],
    }
    status, resp = api("POST", "/collections", token, body)
    if status >= 400:
        print(json.dumps(resp, indent=2)); sys.exit(1)
    print("+ collection actualites_hero created")


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


def revoke_public_read(token, collection):
    status, resp = api("GET", "/policies?filter[name][_eq]=$t:public_label&fields=id", token)
    policy_id = resp["data"][0]["id"]
    status, resp = api("GET", f"/permissions?filter[policy][_eq]={policy_id}&filter[collection][_eq]={collection}", token)
    for p in resp.get("data") or []:
        api("DELETE", f"/permissions/{p['id']}", token)
        print(f"  - permission removed on {collection} ({p['action']})")


def ensure_m2a_allows(token, collection):
    # NB: for an M2A field, one_allowed_collections lives on the RELATION
    # (/relations/pages_sections/item), not on the field's own meta -- see
    # directus_singleton_gotcha.md (memory) for the full story.
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


# Deleting actualites_testimonials_highlight(_testimonials) and
# actualites_documents_list (0 rows, no counterpart in the real design) is a
# separate, destructive step -- see scripts/retire_stale_actualites.py,
# run only after explicit user confirmation.


def main():
    token = login()
    print("login OK")

    print("\n== 1. Collection + fields ==")
    ensure_collection(token)
    ensure_field(token, "actualites_hero", "title_fr", "string", {"interface": "input"})
    ensure_field(token, "actualites_hero", "title_en", "string", {"interface": "input"})
    ensure_field(token, "actualites_hero", "subtitle_fr", "text", {"interface": "input-multiline"})
    ensure_field(token, "actualites_hero", "subtitle_en", "text", {"interface": "input-multiline"})
    ensure_field(token, "actualites_hero", "image", "uuid", {"interface": "file-image", "special": ["file"]})

    print("\n== 2. Relation for the image field ==")
    status, resp = api("GET", "/relations/actualites_hero/image", token)
    if status >= 400:
        status, resp = api("POST", "/relations", token, {
            "collection": "actualites_hero", "field": "image", "related_collection": "directus_files",
            "schema": {"on_delete": "SET NULL"}, "meta": {"one_deselect_action": "nullify"},
        })
        if status >= 400:
            print(json.dumps(resp, indent=2)); sys.exit(1)
        print("  + relation actualites_hero.image -> directus_files created")
    else:
        print("  = relation actualites_hero.image already exists")

    print("\n== 3. Permissions ==")
    grant_public_read(token, "actualites_hero")

    print("\n== 4. M2A allowlist (pages_sections.item) ==")
    ensure_m2a_allows(token, "actualites_hero")

    print("\n== 5. Content (idempotent upsert on id=1; no hero image yet -- none provided) ==")
    upsert_row(token, "actualites_hero", 1, {
        "title_fr": "Actualités ISETAG",
        "subtitle_fr": (
            "Découvrez les événements, les filières, les portraits, les partenariats et "
            "les dispositifs de bourse qui font vivre l'ISETAG. Cette rubrique met en "
            "lumière les expériences proposées aux étudiants, les collaborations de "
            "l'Institut et les parcours qui incarnent ses valeurs."
        ),
    })

    print("\n== 6. Wire Actualites page sections ==")
    status, resp = api("GET", "/items/pages?filter[key][_eq]=actualites&fields=id", token)
    pages_id = resp["data"][0]["id"]
    ensure_page_section(token, pages_id, "actualites_hero", 1, 1)
    ensure_page_section(token, pages_id, "accueil_cta_banner", 2, 2)

    print("\nDONE (run scripts/retire_stale_actualites.py separately to remove the stale collections)")


if __name__ == "__main__":
    main()
