#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""User-confirmed (2026-08-27): seed a few PLACEHOLDER news articles so
"Lire Aussi" isn't empty during dev/QA. No real source content exists for
these (no contenu_actualites folder like other pages had) -- titles reused
from the Figma mock itself (the 3 distinct card titles it repeats to fill
the grid), content_fr is honestly labelled as placeholder, no invented facts
about real people/events. status=draft so they NEVER show up on public reads
(news read permission already filters status=published) -- these exist for
admin-side/dev grid testing only, to be replaced with real content+photos
later."""
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

PLACEHOLDER_NOTE = (
    "[Contenu provisoire -- titre repris de la maquette Figma, texte et "
    "photo réels à fournir par l'équipe communication. Ne pas publier tel "
    "quel.] "
)

ARTICLES = [
    {
        "slug": "renforcement-des-capacites-a-l-isetag",
        "title_fr": "Renforcement des capacités à l'ISETAG",
        "category": "academique",
        "content_fr": PLACEHOLDER_NOTE + (
            "Un aperçu à venir d'une session de renforcement des capacités "
            "organisée à l'ISETAG."
        ),
        "date_published": "2026-02-25",
    },
    {
        "slug": "moment-de-detente-a-kribi",
        "title_fr": "Moment de detente à Kribi",
        "category": "vie_campus",
        "content_fr": PLACEHOLDER_NOTE + (
            "Un aperçu à venir d'une sortie étudiante à Kribi."
        ),
        "date_published": "2026-02-25",
    },
    {
        "slug": "l-isetag-au-feminin",
        "title_fr": "L'ISETAG au féminin",
        "category": "evenement",
        "content_fr": PLACEHOLDER_NOTE + (
            "Un aperçu à venir d'un portrait ou d'un événement mettant en "
            "avant les étudiantes/le personnel féminin de l'ISETAG."
        ),
        "date_published": "2026-02-25",
    },
]


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


def ensure_article(token, article):
    status, resp = api("GET", f"/items/news?filter[slug][_eq]={article['slug']}&fields=id", token)
    if resp.get("data"):
        print(f"  = news '{article['slug']}' already exists (id={resp['data'][0]['id']})")
        return
    body = {**article, "status": "draft", "featured": False}
    status, resp = api("POST", "/items/news", token, body)
    if status >= 400:
        print(json.dumps(resp, indent=2)); sys.exit(1)
    print(f"  + news '{article['slug']}' created (id={resp['data']['id']}, status=draft)")


def main():
    token = login()
    print("login OK")
    print("\n== Seeding placeholder news articles (status=draft) ==")
    for article in ARTICLES:
        ensure_article(token, article)
    print("\nDONE")


if __name__ == "__main__":
    main()
