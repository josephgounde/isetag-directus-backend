#!/usr/bin/env python3
"""Provisionne le Flow de pré-inscription publique et ses permissions.

Idempotent : si le Flow ou une permission existe déjà (identifié par nom /
policy+collection+action), il est mis à jour plutôt que dupliqué.

Nécessaire car `directus schema snapshot` ne capture ni les flows/opérations,
ni les rôles/policies/permissions : ce script doit être rejoué après chaque
`directus schema apply` sur un environnement neuf (staging/prod), une fois les
policies "Service Admissions"/"Service Communication" déjà créées (schéma).

Voir la section "Formulaire de pré-inscription" de ISETAG_project_instructions.md
pour le circuit complet (upload des fichiers un par un avec id généré côté
client, puis un seul POST JSON vers /flows/trigger/<FLOW_ID>).
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

FLOW_NAME = "Pré-inscription — Formulaire public"

PUBLIC_WRITABLE_FIELDS = [
    "nom", "prenom", "date_naissance", "lieu_naissance", "nationalite", "sexe",
    "telephone", "whatsapp", "email", "ville", "pays",
    "dernier_diplome", "annee_obtention", "etablissement", "cycle", "domaine",
    "filiere", "specialite", "regime", "commentaire_orientation",
    "besoin_logement", "accompagnement_orientation", "accompagnement_financement",
    "piece_identite", "diplome_releve", "photo_identite", "autres_documents",
    "commentaire_services", "certification", "consentement_donnees",
    "source", "annee_academique",
]

EMAIL_BODY = (
    "<h2>Nouvelle pré-inscription — {{$trigger.body.prenom}} {{$trigger.body.nom}}</h2>"
    "<p><strong>Dossier n°</strong> {{$last.id}}</p>"
    "<h3>Identité</h3>"
    "<p>Né(e) le {{$trigger.body.date_naissance}} à {{$trigger.body.lieu_naissance}} — "
    "{{$trigger.body.nationalite}} — {{$trigger.body.sexe}}<br>"
    "{{$trigger.body.ville}}, {{$trigger.body.pays}}</p>"
    "<h3>Contacts</h3>"
    "<p>Téléphone : {{$trigger.body.telephone}}<br>"
    "WhatsApp : {{$trigger.body.whatsapp}}<br>"
    "Email : {{$trigger.body.email}}</p>"
    "<h3>Parcours & formation souhaitée</h3>"
    "<p>Dernier diplôme : {{$trigger.body.dernier_diplome}} ({{$trigger.body.annee_obtention}}) — "
    "{{$trigger.body.etablissement}}<br>"
    "Cycle : {{$trigger.body.cycle}} — Domaine : {{$trigger.body.domaine}}<br>"
    "Filière : {{$trigger.body.filiere}} — Spécialité : {{$trigger.body.specialite}}<br>"
    "Régime : {{$trigger.body.regime}}</p>"
    "<h3>Services demandés</h3>"
    "<p>Logement : {{$trigger.body.besoin_logement}} — "
    "Orientation : {{$trigger.body.accompagnement_orientation}} — "
    "Financement : {{$trigger.body.accompagnement_financement}}</p>"
    "<h3>Documents</h3>"
    "<p>"
    "<a href=\"{{$env.PUBLIC_URL}}/assets/{{$trigger.body.piece_identite}}\">Pièce d'identité</a><br>"
    "<a href=\"{{$env.PUBLIC_URL}}/assets/{{$trigger.body.diplome_releve}}\">Diplôme / relevé</a><br>"
    "<a href=\"{{$env.PUBLIC_URL}}/assets/{{$trigger.body.photo_identite}}\">Photo d'identité</a>"
    "</p>"
    "<p><em>(nécessite d'être déjà connecté à Directus dans ce navigateur)</em></p>"
    "<p><a href=\"{{$env.PUBLIC_URL}}/admin/content/admission_applications/{{$last.id}}\">Voir le dossier complet</a></p>"
)


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


def get_policy_id(token, name):
    query = urllib.parse.urlencode({"filter[name][_eq]": name, "fields": "id"})
    status, resp = api("GET", f"/policies?{query}", token)
    data = resp.get("data") or []
    if not data:
        print(f"  !! policy '{name}' introuvable (le schéma a-t-il bien été appliqué ?)")
        sys.exit(1)
    return data[0]["id"]


def get_public_policy_id(token):
    # Le policy système Public n'a pas de nom stable en base ; on le repère par
    # son libellé de traduction ($t:public_label), identique à travers les environnements.
    status, resp = api("GET", "/policies?limit=-1&fields=id,name", token)
    for p in resp.get("data", []):
        if p["name"] == "$t:public_label":
            return p["id"]
    print("  !! policy Public introuvable")
    sys.exit(1)


def ensure_permission(token, policy, collection, action, fields=None):
    query = urllib.parse.urlencode({
        "filter[policy][_eq]": policy,
        "filter[collection][_eq]": collection,
        "filter[action][_eq]": action,
        "fields": "id",
    })
    status, resp = api("GET", f"/permissions?{query}", token)
    existing = resp.get("data") or []
    body = {"policy": policy, "collection": collection, "action": action,
            "fields": fields or ["*"], "permissions": {}}
    if existing:
        pid = existing[0]["id"]
        api("PATCH", f"/permissions/{pid}", token, body)
        print(f"  = {collection} {action} (policy {policy}) déjà présent, mis à jour")
    else:
        api("POST", "/permissions", token, body)
        print(f"  + {collection} {action} (policy {policy}) créé")


def find_flow(token):
    query = urllib.parse.urlencode({"filter[name][_eq]": FLOW_NAME, "fields": "id"})
    status, resp = api("GET", f"/flows?{query}", token)
    data = resp.get("data") or []
    return data[0]["id"] if data else None


def main():
    token = login()

    print("== Permissions ==")
    service_admissions = get_policy_id(token, "Service Admissions")
    public_policy = get_public_policy_id(token)

    for action in ("create", "read", "update", "delete"):
        ensure_permission(token, service_admissions, "admission_applications_files", action)
    ensure_permission(token, service_admissions, "directus_files", "read")
    ensure_permission(token, service_admissions, "directus_files", "create")
    ensure_permission(token, service_admissions, "directus_files", "update")
    # Requis par l'app Directus pour afficher la page fichier (arborescence de dossiers),
    # même en accès direct par lien — sans ce read, la page /admin/files/<uuid> renvoie
    # FORBIDDEN sur "directus_folders" avant même d'afficher le fichier demandé.
    ensure_permission(token, service_admissions, "directus_folders", "read")

    ensure_permission(token, public_policy, "admission_applications", "create", PUBLIC_WRITABLE_FIELDS)
    ensure_permission(token, public_policy, "directus_files", "create")
    ensure_permission(token, public_policy, "admission_applications_files", "create")

    print("== Flow ==")
    flow_id = find_flow(token)
    if flow_id:
        print(f"  Flow '{FLOW_NAME}' existe déjà ({flow_id}), synchronisation de l'opération mail...")
        status, ops = api("GET", f"/operations?filter[flow][_eq]={flow_id}&filter[key][_eq]=notify_admissions&fields=id", token)
        for op in ops.get("data", []):
            api("PATCH", f"/operations/{op['id']}", token, {
                "options": {
                    "to": ["{{$env.ADMISSIONS_EMAIL}}"],
                    "subject": "Nouvelle pré-inscription — {{$trigger.body.prenom}} {{$trigger.body.nom}}",
                    "type": "wysiwyg",
                    "body": EMAIL_BODY,
                }
            })
            print(f"  = opération mail {op['id']} mise à jour")
        print(f"  URL de déclenchement : {BASE}/flows/trigger/{flow_id}")
        return

    status, flow = api("POST", "/flows", token, {
        "name": FLOW_NAME,
        "icon": "send",
        "color": "#2E7D51",
        "description": ("Reçoit la candidature (JSON) après upload individuel des fichiers "
                        "vers /files, crée l'enregistrement admission_applications, puis "
                        "notifie le service des admissions par email."),
        "status": "active",
        "trigger": "webhook",
        "accountability": "all",
        "options": {"method": "POST"},
    })
    if status >= 400:
        print(json.dumps(flow, indent=2))
        sys.exit(1)
    flow_id = flow["data"]["id"]
    print(f"  Flow créé : {flow_id}")

    status, op1 = api("POST", "/operations", token, {
        "name": "Créer la candidature",
        "key": "create_application",
        "type": "item-create",
        "position_x": 19, "position_y": 1,
        "options": {"collection": "admission_applications", "payload": "{{$trigger.body}}", "emitEvents": True},
        "flow": flow_id,
    })
    if status >= 400:
        print(json.dumps(op1, indent=2))
        sys.exit(1)
    op1_id = op1["data"]["id"]

    status, op2 = api("POST", "/operations", token, {
        "name": "Notifier le service des admissions",
        "key": "notify_admissions",
        "type": "mail",
        "position_x": 39, "position_y": 1,
        "options": {
            "to": ["{{$env.ADMISSIONS_EMAIL}}"],
            "subject": "Nouvelle pré-inscription — {{$trigger.body.prenom}} {{$trigger.body.nom}}",
            "type": "wysiwyg",
            "body": EMAIL_BODY,
        },
        "flow": flow_id,
    })
    if status >= 400:
        print(json.dumps(op2, indent=2))
        sys.exit(1)
    op2_id = op2["data"]["id"]

    api("PATCH", f"/flows/{flow_id}", token, {"operation": op1_id})
    api("PATCH", f"/operations/{op1_id}", token, {"resolve": op2_id})

    print(f"  Opérations créées et chaînées ({op1_id} -> {op2_id})")
    print(f"  URL de déclenchement : {BASE}/flows/trigger/{flow_id}")
    print("DONE")


if __name__ == "__main__":
    main()
