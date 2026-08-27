#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Copies files from dev's Directus to prod's, by dev file id, into prod's
"Public" folder, deduped by title. Written 2026-08-27 to push the images
manually uploaded to dev during the Contact/Actualites work (hero photo,
the real GAP Motors article photo, and 3 placeholder "Lire Aussi" photos) --
edit IMAGES below and re-run for the next batch, or import ensure_image_on_prod.

Prod is reached with a resilient retry wrapper: isetag-directus-prod was
observed flapping ~50/50 between a stale/fresh in-memory schema cache on
EVERY request right after schema writes (2026-08-27) -- not normal cache-lag
(waiting longer didn't help), and a container restart is blocked by the
Claude Code classifier for a prod service. Retrying is the working fix.

Usage:
    TARGET_BASE_URL=http://31.207.34.25 \\
    DIRECTUS_ADMIN_EMAIL=... DIRECTUS_ADMIN_PASSWORD=... \\
    python scripts/copy_images_dev_to_prod.py
"""
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

DEV_BASE = os.environ.get("DEV_BASE_URL", "http://localhost:8055").rstrip("/")
DEV_EMAIL = os.environ.get("DEV_ADMIN_EMAIL", "admin@isetag-univ.net")
DEV_PASSWORD = os.environ.get("DEV_ADMIN_PASSWORD", "isetag_dev_admin_pw")

PROD_BASE = os.environ["TARGET_BASE_URL"].rstrip("/")
PROD_EMAIL = os.environ["DIRECTUS_ADMIN_EMAIL"]
PROD_PASSWORD = os.environ["DIRECTUS_ADMIN_PASSWORD"]

# (dev_file_id, filename, title) -- edit per batch
IMAGES = [
    ("c443e1dc-0cc1-4137-b336-398fc5170046", "actualites_hero.png", "Actualités Hero"),
    ("e5a73755-6f79-4ee2-b3d2-62ee66c5d0f5", "alumni_image.png", "Immersion professionnelle chez GAP Motors (prod re-upload)"),
    ("7c9f0305-537e-4039-8c25-ada61eca12dd", "63227 4.png", "63227 4"),
    ("a2b21378-b1f6-49cc-942d-dacc4262723b", "63227 5.png", "63227 5"),
    ("b1b30f80-2be3-41b0-859b-5e0b4626dc1d", "63227 6.png", "63227 6"),
]


def _api(base, method, path, token, body=None):
    url = base + path
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


def dev_api(method, path, token, body=None):
    return _api(DEV_BASE, method, path, token, body)


def prod_api(method, path, token, body=None):
    """Retries transient 403/400s from prod's flapping schema cache."""
    s, r = None, None
    for attempt in range(8):
        s, r = _api(PROD_BASE, method, path, token, body)
        if s < 400:
            return s, r
        if "exist" in json.dumps(r) and attempt < 7:
            time.sleep(1)
            continue
        return s, r
    return s, r


def download_from_dev(dev_token, file_id):
    req = urllib.request.Request(f"{DEV_BASE}/assets/{file_id}")
    req.add_header("Authorization", f"Bearer {dev_token}")
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def upload_to_prod(prod_token, folder_id, filename, title, file_bytes):
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    boundary = uuid.uuid4().hex

    def field(name, value):
        return f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()

    parts = [field("folder", folder_id), field("title", title)]
    parts.append(
        (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
         f"Content-Type: {mime}\r\n\r\n").encode() + file_bytes + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)

    for attempt in range(8):
        req = urllib.request.Request(PROD_BASE + "/files", data=body, method="POST")
        req.add_header("Authorization", f"Bearer {prod_token}")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            code = e.code
            parsed = json.loads(e.read())
            if code in (400, 403) and "exist" in json.dumps(parsed) and attempt < 7:
                time.sleep(1)
                continue
            return code, parsed


def ensure_image_on_prod(prod_token, dev_token, folder_id, dev_file_id, filename, title):
    """Dedupe by title, same convention as ensure_image() used elsewhere."""
    q = urllib.parse.urlencode({"filter[title][_eq]": title, "fields": "id"})
    s, r = prod_api("GET", f"/files?{q}", prod_token)
    existing = r.get("data") or []
    if existing:
        print(f"  = '{title}' already on prod ({existing[0]['id']})")
        return existing[0]["id"]
    file_bytes = download_from_dev(dev_token, dev_file_id)
    s, r = upload_to_prod(prod_token, folder_id, filename, title, file_bytes)
    if s >= 400:
        print(json.dumps(r, indent=2))
        sys.exit(1)
    print(f"  + '{title}' uploaded to prod ({r['data']['id']}, {len(file_bytes)} bytes)")
    return r["data"]["id"]


def main():
    _, r = dev_api("POST", "/auth/login", None, {"email": DEV_EMAIL, "password": DEV_PASSWORD})
    dev_token = r["data"]["access_token"]
    _, r = prod_api("POST", "/auth/login", None, {"email": PROD_EMAIL, "password": PROD_PASSWORD})
    prod_token = r["data"]["access_token"]
    print("logged into dev and prod")

    _, r = prod_api("GET", "/folders?filter[name][_eq]=Public&fields=id", prod_token)
    public_folder_id = r["data"][0]["id"]
    print("prod Public folder:", public_folder_id)

    ids = {}
    for dev_id, filename, title in IMAGES:
        prod_id = ensure_image_on_prod(prod_token, dev_token, public_folder_id, dev_id, filename, title)
        ids[title] = prod_id

    print("\nDONE\n", json.dumps(ids, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
