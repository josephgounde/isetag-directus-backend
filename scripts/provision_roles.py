#!/usr/bin/env python3
"""Provisionne les rôles/policies internes "Service Admissions" et
"Service Communication".

Idempotent : identifiés par nom, créés seulement s'ils n'existent pas déjà.

Nécessaire car `directus schema snapshot` ne capture ni les rôles ni les
policies (uniquement les collections/champs/relations) : ces deux rôles ont
été créés manuellement via l'Admin UI en dev, jamais scriptés jusqu'ici — donc
absents sur tout environnement neuf (staging/prod). `provision_admissions_flow.py`
et `provision_contact_flow.py` s'appuient sur ces policies déjà présentes
("Service Admissions" / "Service Communication" introuvable" sinon) : ce
script doit tourner AVANT eux sur un environnement neuf.

Ne crée aucune permission (droits RW sur les collections) — celles-ci restent
gérées par `provision_admissions_flow.py` / `provision_contact_flow.py`, qui
les attachent à la policy une fois celle-ci garantie présente ici.
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

ROLES = [
    {"name": "Service Admissions", "icon": "assignment_ind"},
    {"name": "Service Communication", "icon": "campaign"},
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
        print(json.dumps(resp, indent=2))
        sys.exit(1)
    return resp["data"]["access_token"]


def find_by_name(token, endpoint, name):
    query = urllib.parse.urlencode({"filter[name][_eq]": name, "fields": "id"})
    status, resp = api("GET", f"/{endpoint}?{query}", token)
    data = resp.get("data") or []
    return data[0]["id"] if data else None


def ensure_role_and_policy(token, name, icon):
    role_id = find_by_name(token, "roles", name)
    if role_id:
        print(f"  = rôle '{name}' déjà présent ({role_id})")
        return role_id

    policy_id = find_by_name(token, "policies", name)
    if not policy_id:
        status, resp = api("POST", "/policies", token, {
            "name": name, "icon": icon, "admin_access": False, "app_access": True,
        })
        if status >= 400:
            print(json.dumps(resp, indent=2))
            sys.exit(1)
        policy_id = resp["data"]["id"]
        print(f"  + policy '{name}' créée ({policy_id})")
    else:
        print(f"  = policy '{name}' déjà présente ({policy_id})")

    status, resp = api("POST", "/roles", token, {
        "name": name, "icon": icon,
        "policies": {"create": [{"policy": policy_id}], "update": [], "delete": []},
    })
    if status >= 400:
        print(json.dumps(resp, indent=2))
        sys.exit(1)
    role_id = resp["data"]["id"]
    print(f"  + rôle '{name}' créé ({role_id}), lié à la policy {policy_id}")
    return role_id


def main():
    token = login()
    print("== Rôles internes ==")
    for role in ROLES:
        ensure_role_and_policy(token, role["name"], role["icon"])
    print("DONE")


if __name__ == "__main__":
    main()
