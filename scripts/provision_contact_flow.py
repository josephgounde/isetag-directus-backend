#!/usr/bin/env python3
"""Provisionne le Flow du formulaire de contact public et ses permissions.

Idempotent : si le Flow ou une permission existe déjà (identifié par nom /
policy+collection+action), il est mis à jour plutôt que dupliqué.

Nécessaire car `directus schema snapshot` ne capture ni les flows/opérations,
ni les rôles/policies/permissions : ce script doit être rejoué après chaque
`directus schema apply` sur un environnement neuf (staging/prod).

Contrairement au formulaire de pré-inscription, pas de pièces jointes ici :
un simple POST JSON direct vers le Flow suffit (pas de circuit en 2 étapes).
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

FLOW_NAME = "Contact — Formulaire public"

PUBLIC_WRITABLE_FIELDS = ["nom", "email", "fonction", "message"]

EMAIL_BODY = (
    "<h2>Nouveau message de contact — {{$trigger.body.nom}}</h2>"
    "<p><strong>Fonction :</strong> {{$trigger.body.fonction}}<br>"
    "<strong>Email :</strong> {{$trigger.body.email}}</p>"
    "<h3>Message</h3>"
    "<p>{{$trigger.body.message}}</p>"
    "<p><a href=\"{{$env.PUBLIC_URL}}/admin/content/contact_messages/{{$last.id}}\">Voir le message dans Directus</a></p>"
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
    # Rattaché à Service Communication (déjà responsable des contenus publics
    # news/testimonials/partners) — à revoir si un service dédié est créé.
    service_communication = get_policy_id(token, "Service Communication")
    public_policy = get_public_policy_id(token)

    for action in ("create", "read", "update", "delete"):
        ensure_permission(token, service_communication, "contact_messages", action)

    ensure_permission(token, public_policy, "contact_messages", "create", PUBLIC_WRITABLE_FIELDS)

    print("== Flow ==")
    flow_id = find_flow(token)
    if flow_id:
        print(f"  Flow '{FLOW_NAME}' existe déjà ({flow_id}), synchronisation de l'opération mail...")
        status, ops = api("GET", f"/operations?filter[flow][_eq]={flow_id}&filter[key][_eq]=notify_contact&fields=id", token)
        for op in ops.get("data", []):
            api("PATCH", f"/operations/{op['id']}", token, {
                "options": {
                    "to": ["{{$env.CONTACT_EMAIL}}"],
                    "subject": "Nouveau message de contact — {{$trigger.body.nom}}",
                    "type": "wysiwyg",
                    "body": EMAIL_BODY,
                }
            })
            print(f"  = opération mail {op['id']} mise à jour")
        print(f"  URL de déclenchement : {BASE}/flows/trigger/{flow_id}")
        return

    status, flow = api("POST", "/flows", token, {
        "name": FLOW_NAME,
        "icon": "mail",
        "color": "#2E7D51",
        "description": "Reçoit un message du formulaire de contact (JSON direct, pas de fichiers), crée l'item contact_messages, puis notifie le service communication par email.",
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
        "name": "Créer le message",
        "key": "create_message",
        "type": "item-create",
        "position_x": 19, "position_y": 1,
        "options": {"collection": "contact_messages", "payload": "{{$trigger.body}}", "emitEvents": True},
        "flow": flow_id,
    })
    if status >= 400:
        print(json.dumps(op1, indent=2))
        sys.exit(1)
    op1_id = op1["data"]["id"]

    status, op2 = api("POST", "/operations", token, {
        "name": "Notifier le service communication",
        "key": "notify_contact",
        "type": "mail",
        "position_x": 39, "position_y": 1,
        "options": {
            "to": ["{{$env.CONTACT_EMAIL}}"],
            "subject": "Nouveau message de contact — {{$trigger.body.nom}}",
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
