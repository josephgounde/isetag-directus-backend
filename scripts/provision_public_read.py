#!/usr/bin/env python3
"""Provisionne l'accès public en lecture pour le site public (frontend Angular).

Idempotent : permissions identifiées par policy+collection+action, dossier
"Public" identifié par son nom.

Contexte : le rôle Public n'avait jusqu'ici QUE des droits d'écriture (formulaire
de pré-inscription). Sans ce script, aucune page publique ne peut rien afficher.

Modèle de sécurité pour les fichiers : allowlist par dossier plutôt que blocklist.
Seuls les fichiers rangés dans le dossier "Public" sont lisibles publiquement
(`directus_files` en lecture, filtré par `folder`). Tout fichier hors de ce
dossier (en particulier les pièces jointes RGPD-sensibles du formulaire de
pré-inscription, jamais rangées dans un dossier) reste invisible côté public,
même si son UUID venait à fuiter. C'est un choix "fail closed" délibéré : un
champ fichier oublié dans le mauvais dossier reste privé par défaut, jamais
l'inverse.

Les champs fichiers des collections publiques (programs.cover_image,
news.cover_image, partners.logo, testimonials.photo, documents.file) ont leur
option d'interface "folder" pré-réglée sur ce dossier "Public", pour que
l'upload via l'Admin UI y range les fichiers par défaut.

À rejouer après chaque `directus schema apply` sur un environnement neuf
(staging/prod) — dossier et permissions ne sont pas capturés par le snapshot
de schéma (les permissions ne le sont jamais ; le dossier techniquement si,
mais son id changerait, donc on le recherche par nom à chaque exécution).
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

PUBLIC_FOLDER_NAME = "Public"

# (collection, filter_permissions, fields)
READ_COLLECTIONS = [
    ("poles", {}, ["*"]),
    ("programs", {"status": {"_eq": "published"}}, ["*"]),
    ("news", {}, ["*"]),
    ("campus_services", {}, ["*"]),
    ("partners", {}, ["*"]),
    ("stats_counters", {}, ["*"]),
    ("testimonials", {}, ["*"]),
    ("tuition_plans", {"status": {"_eq": "published"}}, ["*"]),
    ("scholarships", {"status": {"_eq": "published"}}, ["*"]),
    ("documents", {"status": {"_eq": "published"}}, ["*"]),
    # Pages composées de sections (page-builder) — voir "Organisation en pages/sections"
    # dans ISETAG_project_instructions.md. Chaque page a ses propres collections
    # de blocs (ex. admissions_hero vs accueil_hero) : plus de collection block_*
    # partagée entre plusieurs pages.
    ("pages", {"status": {"_eq": "published"}}, ["*"]),
    ("pages_sections", {}, ["*"]),
    ("admissions_hero", {}, ["*"]),
    ("admissions_richtext", {}, ["*"]),
    ("admissions_feature", {}, ["*"]),
    ("admissions_cta_banner", {}, ["*"]),
    ("admissions_steps", {}, ["*"]),
    ("admissions_steps_items", {}, ["*"]),
    ("accueil_news_preview", {}, ["*"]),
    ("accueil_programs_highlight", {}, ["*"]),
    ("accueil_programs_highlight_programs", {}, ["*"]),
    ("accueil_hero", {}, ["*"]),
    ("accueil_poles_highlight", {}, ["*"]),
    ("accueil_reasons", {}, ["*"]),
    ("accueil_reasons_items", {}, ["*"]),
    ("accueil_cta_banner", {}, ["*"]),
    ("accueil_partners_highlight", {}, ["*"]),
    ("accueil_partners_highlight_partners", {}, ["*"]),
    ("accueil_testimonials_highlight", {}, ["*"]),
    ("accueil_testimonials_highlight_testimonials", {}, ["*"]),
    ("accueil_vie_campus_teaser", {}, ["*"]),
    ("actualites_testimonials_highlight", {}, ["*"]),
    ("actualites_testimonials_highlight_testimonials", {}, ["*"]),
    ("actualites_documents_list", {}, ["*"]),
]

# (collection, file_field) dont l'upload par défaut doit viser le dossier "Public"
PUBLIC_FILE_FIELDS = [
    ("programs", "cover_image"),
    ("news", "cover_image"),
    ("partners", "logo"),
    ("testimonials", "photo"),
    ("documents", "file"),
    ("admissions_hero", "image"),
    ("admissions_feature", "image"),
    ("admissions_richtext", "image"),
    ("accueil_hero", "image"),
    ("accueil_reasons_items", "image"),
    ("accueil_vie_campus_teaser", "image"),
    ("poles", "image"),
    ("scholarships", "image"),
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


def get_public_policy_id(token):
    status, resp = api("GET", "/policies?limit=-1&fields=id,name", token)
    for p in resp.get("data", []):
        if p["name"] == "$t:public_label":
            return p["id"]
    print("  !! policy Public introuvable")
    sys.exit(1)


def ensure_permission(token, policy, collection, action, fields, perm_filter):
    query = urllib.parse.urlencode({
        "filter[policy][_eq]": policy,
        "filter[collection][_eq]": collection,
        "filter[action][_eq]": action,
        "fields": "id",
    })
    status, resp = api("GET", f"/permissions?{query}", token)
    existing = resp.get("data") or []
    body = {"policy": policy, "collection": collection, "action": action,
            "fields": fields, "permissions": perm_filter}
    if existing:
        pid = existing[0]["id"]
        api("PATCH", f"/permissions/{pid}", token, body)
        print(f"  = {collection} {action} déjà présent, mis à jour")
    else:
        api("POST", "/permissions", token, body)
        print(f"  + {collection} {action} créé")


def ensure_public_folder(token):
    query = urllib.parse.urlencode({"filter[name][_eq]": PUBLIC_FOLDER_NAME, "fields": "id"})
    status, resp = api("GET", f"/folders?{query}", token)
    data = resp.get("data") or []
    if data:
        return data[0]["id"]
    status, folder = api("POST", "/folders", token, {"name": PUBLIC_FOLDER_NAME})
    if status >= 400:
        print(json.dumps(folder, indent=2))
        sys.exit(1)
    return folder["data"]["id"]


def main():
    token = login()
    public_policy = get_public_policy_id(token)

    print("== Dossier Public ==")
    public_folder_id = ensure_public_folder(token)
    print(f"  dossier 'Public' : {public_folder_id}")

    print("== Options des champs fichiers publics (dossier par défaut) ==")
    for collection, field in PUBLIC_FILE_FIELDS:
        status, current = api("GET", f"/fields/{collection}/{field}", token)
        meta = current.get("data", {}).get("meta", {}) if status < 400 else {}
        options = dict(meta.get("options") or {})
        options["folder"] = public_folder_id
        api("PATCH", f"/fields/{collection}/{field}", token, {"meta": {"options": options}})
        print(f"  = {collection}.{field} -> dossier par défaut réglé")

    print("== Permissions de lecture publique ==")
    for collection, perm_filter, fields in READ_COLLECTIONS:
        ensure_permission(token, public_policy, collection, "read", fields, perm_filter)

    print("== Lecture publique des fichiers (dossier 'Public' uniquement) ==")
    ensure_permission(token, public_policy, "directus_files", "read", ["*"],
                       {"folder": {"_eq": public_folder_id}})

    print("DONE")


if __name__ == "__main__":
    main()
