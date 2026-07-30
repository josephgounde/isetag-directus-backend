#!/usr/bin/env python3
"""Peuple les collections poles et programs avec les 5 poles et 27 filieres.

Idempotent : chaque enregistrement est identifie par son slug ; s'il existe
deja, il est mis a jour plutot que duplique.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("DIRECTUS_PUBLIC_URL", "http://localhost:8055").rstrip("/")
EMAIL = os.environ["DIRECTUS_ADMIN_EMAIL"]
PASSWORD = os.environ["DIRECTUS_ADMIN_PASSWORD"]


def api(method, path, token, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def login():
    status, resp = api("POST", "/auth/login", None, {"email": EMAIL, "password": PASSWORD})
    if status >= 400:
        print(json.dumps(resp, indent=2))
        sys.exit(1)
    return resp["data"]["access_token"]


def clear_cache(token):
    # CACHE_ENABLED=true peut renvoyer des listes obsolètes juste après une
    # écriture ; on vide le cache avant de relire l'état existant.
    api("POST", "/utils/cache/clear", token)


def existing_slugs(token, collection):
    # Directus caches filtered GETs (CACHE_ENABLED=true), which made per-item
    # "filter[slug][_eq]=..." lookups return stale empty results right after
    # a create. Fetching the full list once and matching locally sidesteps that.
    query = urllib.parse.urlencode({"fields": "id,slug", "limit": -1})
    status, resp = api("GET", f"/items/{collection}?{query}", token)
    if status >= 400:
        return {}
    return {item["slug"]: item["id"] for item in resp.get("data", [])}


def upsert(token, collection, slug, payload, slug_map):
    existing_id = slug_map.get(slug)
    if existing_id:
        status, resp = api("PATCH", f"/items/{collection}/{existing_id}", token, payload)
        verb = "updated"
    else:
        status, resp = api("POST", f"/items/{collection}", token, payload)
        verb = "created"
    ok = status < 400
    print(f"  [{collection}:{slug}] {verb} -> {status}{'' if ok else ' ' + json.dumps(resp)[:300]}")
    return resp.get("data", {}).get("id") if ok else None


POLES = [
    {
        "slug": "industriel-techno",
        "name_fr": "Pôle Industriel & Technologique",
        "name_en": "Industrial & Technology Pole",
        "icon": "precision_manufacturing",
        "color": "#2E7D51",
        "display_order": 1,
    },
    {
        "slug": "maritime-logistique",
        "name_fr": "Pôle Maritime & Logistique",
        "name_en": "Maritime & Logistics Pole",
        "icon": "directions_boat",
        "color": "#2E7D51",
        "display_order": 2,
    },
    {
        "slug": "gestion-commerce",
        "name_fr": "Pôle Gestion & Commerce",
        "name_en": "Management & Commerce Pole",
        "icon": "business_center",
        "color": "#2E7D51",
        "display_order": 3,
    },
    {
        "slug": "communication-digital",
        "name_fr": "Pôle Communication & Digital",
        "name_en": "Communication & Digital Pole",
        "icon": "campaign",
        "color": "#2E7D51",
        "display_order": 4,
    },
    {
        "slug": "sante-paramedical",
        "name_fr": "Pôle Santé & Paramédical",
        "name_en": "Health & Paramedical Pole",
        "icon": "medical_services",
        "color": "#2E7D51",
        "display_order": 5,
    },
]

# (slug, name_fr, name_en, pole_slug, level, is_hnd, schedule)
PROGRAMS = [
    ("froid", "BTS Froid & Climatisation", "Refrigeration & Air Conditioning", "industriel-techno", "HND", True, "jour_soir"),
    ("electro", "Électrotechnique", "Electrical Engineering", "industriel-techno", "HND", True, "jour"),
    ("mecatro", "Mécatronique", "Mechatronics", "industriel-techno", None, False, "jour"),
    ("btp", "Bâtiment TP", "Building & Public Works", "industriel-techno", None, False, "jour_soir"),
    ("menuiserie", "Menuiserie Ébénisterie", "Carpentry & Cabinetmaking", "industriel-techno", None, False, "soir"),
    ("chaudro", "Chaudronnerie", "Boilermaking", "industriel-techno", None, False, "jour"),
    ("install", "Installation Sanitaire", "Sanitary Installation", "industriel-techno", None, False, "jour"),
    ("soudure", "Soudure & Structures Métalliques", "Welding & Metal Structures", "industriel-techno", None, False, "jour"),
    ("electro2", "Électronique", "Electronics", "industriel-techno", None, False, "jour"),

    ("shipping", "Shipping Management", "Shipping Management", "maritime-logistique", "HND", True, "jour"),
    ("douane", "Douane & Transit", "Customs & Transit", "maritime-logistique", None, False, "jour_soir"),
    ("logist", "Transport & Logistique", "Transport & Logistics", "maritime-logistique", "HND", True, "jour"),
    ("portu", "Logistique Maritime & Portuaire", "Maritime & Port Logistics", "maritime-logistique", None, False, "jour"),

    ("cge", "Comptabilité & Gestion", "Accounting & Management", "gestion-commerce", "HND", True, "jour_soir"),
    ("mcv", "Marketing-Commerce-Vente", "Marketing, Trade & Sales", "gestion-commerce", None, False, "jour_soir"),
    ("grh", "Gestion RH", "HR Management", "gestion-commerce", None, False, "soir"),
    ("banque", "Banque & Finance", "Banking & Finance", "gestion-commerce", "HND", True, "jour"),
    ("assurance", "Assurance", "Insurance", "gestion-commerce", None, False, "jour"),
    ("manag", "Management de Projet", "Project Management", "gestion-commerce", None, False, "jour_soir"),
    ("compta2", "Comptabilité Publique", "Public Accounting", "gestion-commerce", None, False, "soir"),

    ("commorg", "Communication des Organisations", "Organizational Communication", "communication-digital", None, False, "soir"),
    ("journa", "Journalisme", "Journalism", "communication-digital", None, False, "jour"),
    ("infog", "Infographie & Web Design", "Graphic Design & Web Design", "communication-digital", None, False, "jour"),

    ("infirm", "Sciences Infirmières", "Nursing Sciences", "sante-paramedical", None, False, "jour"),
    ("sagef", "Sage-femme", "Midwifery", "sante-paramedical", None, False, "jour"),
    ("kine", "Kinésithérapie", "Physiotherapy", "sante-paramedical", None, False, "jour"),
    ("labo", "Techniques Laboratoire", "Laboratory Techniques", "sante-paramedical", None, False, "jour"),
]


def main():
    token = login()
    clear_cache(token)

    pole_slugs = existing_slugs(token, "poles")
    pole_ids = {}
    print(f"Seeding {len(POLES)} poles...")
    for pole in POLES:
        pole_ids[pole["slug"]] = upsert(token, "poles", pole["slug"], pole, pole_slugs)

    program_slugs = existing_slugs(token, "programs")
    print(f"Seeding {len(PROGRAMS)} programs...")
    for slug, name_fr, name_en, pole_slug, level, is_hnd, schedule in PROGRAMS:
        pole_id = pole_ids.get(pole_slug)
        if pole_id is None:
            print(f"  [programs:{slug}] SKIPPED - pole '{pole_slug}' introuvable")
            continue
        payload = {
            "slug": slug,
            "name_fr": name_fr,
            "name_en": name_en,
            "pole": pole_id,
            "level": level,
            "is_hnd": is_hnd,
            "schedule": schedule,
            "status": "published",
        }
        upsert(token, "programs", slug, payload, program_slugs)

    print("DONE")


if __name__ == "__main__":
    main()
