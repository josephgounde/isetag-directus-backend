# ISETAG — Contexte Projet (pour Claude Code)

## Client
- **ISETAG** — Institut Évangélique des Technologies Appliquées et de Gestion
- Campus de Yassa, Douala, Cameroun
- Refonte complète du site web institutionnel
- Développeur : Djo — Geomatics Engineer & Full-Stack Dev, Yaoundé
- Langue principale : français (bilinguisme FR/EN requis sur le site)
- Budget total signé : 505 000 FCFA · délai contractuel : 61 jours (voir proposition technique)

## Stack technique (VALIDÉE ET SIMPLIFIÉE — ne pas proposer d'alternatives)

```
Frontend         : Angular 18 (Standalone APIs + SSR via Angular Universal)
CMS              : Directus 11 (Headless — REST + GraphQL + Admin UI)
Base de données  : PostgreSQL 16
Stockage médias  : local (Directus STORAGE_LOCATIONS=local) — PAS de MinIO
Cache            : mémoire interne Directus (CACHE_STORE=memory) — PAS de Redis
Reverse Proxy    : Nginx (TLS, Gzip, HSTS, CSP)
Conteneurs       : Docker + Docker Compose — un seul VPS, PAS de Swarm
CI/CD            : GitHub Actions (build → ghcr.io → SSH deploy vers le VPS unique)
Monitoring       : aucun outil dédié (pas de Grafana/Loki/Prometheus) — logs Docker + alertes VPS du provider
```

**Pourquoi simplifié :** la proposition technique signée ne mentionne qu'un seul
"Hébergement Web Premium (Cloud/VPS)" (75 000 FCFA/an), sans cluster ni monitoring
dédié. Le budget et le délai (505 000 FCFA / 61 jours) ne couvrent pas la maintenance
d'une stack Swarm + observabilité complète. Ne pas réintroduire Swarm, MinIO, Redis,
ou Grafana/Loki/Prometheus sauf demande explicite de Djo.

## Structure du monorepo

```
isetag/
├── docker/dev/   docker/staging/   docker/prod/
├── frontend/          ← Angular 18 SSR
│   └── src/app/features/
│       ├── home/          programmes/     admissions/
│       ├── campus-life/   news-events/    resources/
├── cms/               ← Directus 11 (extensions + snapshots/)
├── nginx/             ← nginx.conf + conf.d/
├── scripts/           ← seed.sh  backup.sh  deploy.sh
├── .github/workflows/ ← ci.yml  deploy.yml
├── .env               ← jamais commité (voir .gitignore)
└── Makefile           ← make dev | make seed | make deploy-prod
```

Commandes clés :
```bash
make dev          # Lance Postgres + Directus + (Angular + Nginx à venir)
make dev-logs     # Suit les logs
make snapshot     # Génère cms/snapshots/current.yaml depuis Directus actuel
make seed         # Peuple les 5 pôles + 27 filières
make deploy-prod  # Déploiement SSH vers le VPS unique
```

Ports (dev) : Angular 4200 · Angular SSR 4000 · Directus Admin 8055 · Nginx 80.

## Sitemap définitif (7 pages + fiche filière dynamique)

```
isetag-univ.net/
├── /                    → Home
├── /choisir-isetag/     → À propos
├── /formations/         → Catalogue filières (filtres pôle + horaires + HND)
│   └── /formations/{slug}/  → Fiche filière dynamique
├── /admissions/         → Pré-inscription + chatbot d'orientation
├── /vie-campus/         → Services campus + ateliers
├── /actualites/         → News + agenda
└── /ressources/         → Alumni + bibliothèque numérique
```
Règles URL : minuscules, tirets, slash final, mots-clés dans le slug, max 3 niveaux,
préfixe `/en/` pour l'anglais, `hreflang` + `canonical` sur chaque page.

## Schéma Directus — 8 collections (ordre de création à respecter)

1. **poles** (aucune dépendance) — slug, name_fr, name_en, icon, color, display_order
2. **programs** (→ poles) — slug, name_fr, name_en, pole (M2O), level, is_hnd, schedule
   (enum jour/soir/jour_soir), seo_title_fr, seo_description_fr, cover_image, status
3. **admission_applications** — champs alignés 1:1 sur `formulaire_preinscription_ISETAG.html`
   (voir section « Formulaire de pré-inscription » plus bas pour le détail et le circuit
   de soumission) : nom, prenom, date_naissance, lieu_naissance, nationalite, sexe,
   telephone, whatsapp, email, ville, pays, dernier_diplome, annee_obtention,
   etablissement, cycle, domaine, filiere, specialite, regime, commentaire_orientation,
   besoin_logement, accompagnement_orientation, accompagnement_financement,
   piece_identite/diplome_releve/photo_identite (fichiers, M2O → directus_files),
   autres_documents (M2M → directus_files via `admission_applications_files`),
   commentaire_services, certification, consentement_donnees, source, annee_academique,
   desired_program (M2O → programs, optionnel, lien interne posé par le service
   admissions après étude du dossier), status (interne, défaut `nouveau`)
4. **testimonials** (→ programs) — student_name, program (M2O), graduation_year,
   quote_fr, quote_en, photo, video_url, featured
5. **news** — slug, title_fr/en, category (enum), content_fr, date_published, cover_image
6. **campus_services** — name_fr/en, icon, category, display_section
7. **partners** — name, logo, type, website_url, featured, display_order
8. **stats_counters** — label_fr/en, value, suffix, icon, display_order

Note : 3 collections supplémentaires ajoutées après revue de la maquette Figma
(`tuition_plans`, `scholarships`, `documents`), voir « État d'avancement ».

## Organisation du menu Content (dossiers)

Les collections sont regroupées dans des dossiers (purement de navigation, aucun
impact sur le schéma — capturé par `directus schema snapshot`, contrairement aux
flows/permissions) pour que le service admissions/communication retrouve les
choses par section du site plutôt que par ordre alphabétique de table :

- **Programmes** (ex-"Formations", renommé — voir plus bas) — `poles`,
  `programs` (données de référence de la page Programmes uniquement)
- **Admissions** — `admission_applications`, `tuition_plans`, `scholarships`,
  `admissions_hero`, `admissions_richtext`, `admissions_feature`,
  `admissions_steps` (guide "Comment s'inscrire"), `admissions_cta_banner`
- **Vie Campus** — `campus_services`
- **Actualités** — `news`, `actualites_testimonials_highlight` ("Success
  Stories"), `actualites_documents_list` (bibliothèque filtrable),
  `testimonials`, `documents` (données de référence, ex-dossier "Ressources"
  fusionné ici — voir plus bas)
- **Accueil & Global** — `partners`, `stats_counters`, `accueil_news_preview`
  (config du nombre d'actus affichées sur Accueil), `accueil_programs_highlight`
  (formations mises en avant sur Accueil)
- **Contact** — `contact_messages`
- **`pages`** — hors de tout dossier, au premier niveau du menu Content : cette
  collection gère les 6 pages (Accueil, Programmes, Admissions, Vie Campus,
  Actualités, Contact), donc la ranger dans un dossier au nom d'une page en
  particulier (ex. "Accueil & Global") serait trompeur.

**Règle de rangement (revue après un second retour utilisateur)** : les
dossiers "Formations" et "Ressources" n'ont jamais existé comme pages réelles
du site (le prototype Figma n'a que 6 pages : Accueil, Programmes, Admissions,
Vie Campus, Actualités, Contact) — mais en tant que dossiers de premier niveau
dans le menu Content, ils apparaissaient au même niveau que "Admissions" ou
"Contact", ce qui les faisait *lire* comme des pages fantômes. Corrigé : le
dossier "Formations" a été **renommé "Programmes"** (`poles`/`programs` ne
servent qu'à la page Programmes) ; le dossier "Ressources" a été **fusionné
dans "Actualités"** (`testimonials`/`documents` n'alimentent que les sections
"Success Stories" et "ressources" de la page Actualités, aucune page
"Ressources" séparée n'existe). Règle générale qui en découle : chaque
collection de bloc de page-builder (voir section suivante) et chaque
collection de référence liée à une seule page vivent dans le dossier **du nom
exact de cette page**, jamais un nom de domaine interne (ex. "Formations",
"Ressources") qui ne correspond à rien dans la nav réelle. Seules les
collections référencées par *plusieurs* pages (`partners`, `stats_counters`)
restent dans "Accueil & Global". Historique des essais abandonnés (contexte
complet) : un dossier séparé "Pages & Sections" regroupant tout le
page-builder (faisait apparaître "Admissions"/"Actualités" en double dans le
menu), puis avoir mis `pages` lui-même dans "Accueil & Global" (trompeur),
puis avoir rangé les blocs par la collection brute qu'ils curatent plutôt que
par la page qui les affiche (ex. `block_programs_highlight` dans "Formations"
même si affiché sur Accueil) — d'où le statut actuel de `pages` hors dossier
et la règle "un dossier = une page" ci-dessus.

`admission_applications_files` et les jonctions techniques M2M/M2A
(`pages_sections`, `accueil_programs_highlight_programs`,
`admissions_steps_items`, `actualites_testimonials_highlight_testimonials`)
restent hors menu : `hidden: true`, l'édition se fait via le champ alias de la
collection parente, jamais directement.

## Organisation en pages/sections (page-builder)

**Révision importante** : la première version de cette section (3 pages :
Accueil/À propos/Admissions) reposait sur l'ancien sitemap écrit dans ce
document, pas sur une revue réelle de la maquette Figma. Après avoir
effectivement ouvert le prototype Figma fourni par l'utilisateur
(https://www.figma.com/proto/Vu712j6MNLuyLgrzMgN47c/Test-1), la nav réelle du
site est : **Accueil, Programmes, Admissions, Vie Campus, Actualités
(actuellement labellisée "Ressources" dans la nav — renommage prévu),
Contact**. Chacune de ces 6 pages a une section hero/intro composée
éditorialement, pas seulement Accueil/Admissions. "À propos" n'existe plus
comme page séparée : son contenu ("Choisir l'ISETAG") est dans le hero
Accueil. Programmes et Actualités se terminent tous les deux par le même
bandeau CTA ("Commence ton chemin aujourd'hui", `block_cta_banner`). Le
"sitemap verrouillé à 7 routes" mentionné dans les instructions
plus bas est **obsolète** — ne plus s'y référer.

Modèle **many-to-any (M2A)**, standard Directus — **révisé** suite à un retour
utilisateur explicite : le modèle initial faisait des collections de blocs
(`block_hero`, `block_feature`, etc.) des tables **partagées entre plusieurs
pages** (une ligne accueil et une ligne admissions dans le même `block_hero`).
Aucune donnée n'était réellement mélangée (chaque ligne reste liée à une seule
page via la jonction), mais l'utilisateur a rejeté cette forme à deux reprises :
il veut qu'une collection de bloc appartienne à **une seule page**, pas qu'elle
soit un « pot commun » réutilisable. Convention retenue désormais :
**`<page_key>_<type_de_bloc>`** (`admissions_hero`, `accueil_hero` seraient deux
collections distinctes si les deux existaient — voir plus bas, seule Admissions
a du contenu aujourd'hui).

- **`pages`** — une ligne par page composée (`key` unique : `accueil`,
  `programmes`, `admissions`, `vie_campus`, `actualites`, `contact` — + `a_propos`
  conservée mais probablement inutile), + `title` (repère admin), `status`
  (published/draft), `sections` (alias M2A). Reste une collection partagée —
  légitime, ce sont des métadonnées de page (clé, titre, statut), pas du
  contenu éditorial.
- **`pages_sections`** — jonction M2A (`pages_id`, `collection`, `item`,
  `sort`) — invisible dans le menu (jonction technique), l'édition se fait via
  le champ `sections` sur `pages`. Reste partagée elle aussi (jonction
  technique jamais parcourue directement par un éditeur) ;
  `one_allowed_collections` liste les collections de blocs page-scopées
  existantes.
- **Collections de blocs** (une par page × type de section, uniquement là où
  une configuration/curation éditoriale a du sens). Créées à ce jour :
  - `admissions_hero` — title_fr/en, subtitle_fr/en, image, cta_label_fr/en, cta_url
  - `admissions_feature` — image, heading_fr/en, tag_label_fr/en (pill
    optionnel, ex. "Transport Maritime"), body_fr/en (WYSIWYG), cta_label_fr/en
    + cta_url optionnels — mise en avant d'une filière/modalité
  - `admissions_steps` — heading_fr/en, `items` (O2M ordonné via
    `admissions_steps_items` : title_fr/en, description_fr/en) — guide "Comment
    s'inscrire"
  - `admissions_richtext` — content_fr/en (WYSIWYG, texte libre), image optionnelle
  - `admissions_cta_banner` — heading_fr/en, text_fr/en, button_label_fr/en, button_url
  - `accueil_news_preview` — heading_fr/en, limit (nb d'actus à afficher sur
    Accueil, pas de sélection manuelle : toujours les N plus récentes) — vide,
    pas encore de contenu Accueil
  - `accueil_programs_highlight` — heading_fr/en, `programs` (M2M ordonné,
    sélection manuelle) — vide
  - `actualites_testimonials_highlight` — heading_fr/en, cta_label_fr/en +
    cta_url optionnels, `testimonials` (M2M ordonné via
    `actualites_testimonials_highlight_testimonials`) — section "Success
    Stories" de la page Actualités — vide
  - `actualites_documents_list` — heading_fr/en, intro_fr/en, category_filter
    optionnel (filtre sur `documents.category`) — section "ressources" à
    l'intérieur de la page Actualités — vide

  Programmes, Vie Campus et Contact n'ont pas encore de collections de blocs
  propres (hero/richtext/cta_banner) : à créer au moment de saisir leur
  contenu, en copiant le schéma de champs des collections `admissions_*`
  ci-dessus comme référence, jamais en réutilisant une collection existante
  d'une autre page.

Les pages qui restent de simples listings filtrés sans composition éditoriale
(Fiche filière) **ne passent pas** par ce modèle.

Exemple de requête frontend (deep-fetch en un seul appel, testé anonyme, y
compris relations O2M/M2M imbriquées) :
```
GET /items/pages?filter[key][_eq]=admissions&fields=*,sections.collection,sections.sort,sections.item:admissions_hero.*,sections.item:admissions_steps.items.*
```

Lecture publique accordée sur `pages` (filtrée `status: published`) et
l'ensemble des collections de blocs page-scopées + leurs jonctions M2M/M2A via
`scripts/provision_public_read.py` — vérifié par requête anonyme réelle après
la restructuration. Contenu des 6 pages seedé vide à l'origine (`status:
published`, `sections: []`) ; Admissions a depuis été rempli (voir plus bas),
les 5 autres restent vides, à remplir par l'équipe communication/admissions
via l'Admin UI.

### Formulaire de contact (page Contact)

Nouvelle page identifiée uniquement via la revue Figma, absente du schéma
jusqu'ici. Mêmes principes que le formulaire de pré-inscription mais sans
fichiers, donc un seul `POST` JSON direct suffit (pas de circuit en 2 étapes) :

- Collection **`contact_messages`** : nom, email, fonction, message, status
  (nouveau/traité), date_created.
- Flow « Contact — Formulaire public » (`scripts/provision_contact_flow.py`,
  même schéma que le Flow d'admission : webhook → `item-create` → `mail` vers
  `{{$env.CONTACT_EMAIL}}`) — testé de bout en bout en dev (item créé,
  déclenchement sans erreur).
- Permissions : Public en `create` uniquement sur `contact_messages` (champs
  `nom`, `email`, `fonction`, `message`) ; rattaché à la policy **Service
  Communication** en lecture/écriture (choix par défaut — à revoir si un
  service "accueil/standard" dédié doit exister à la place).
- `CONTACT_EMAIL` ajouté aux `.env*` (placeholder `contact@isetag-univ.net`,
  actuellement pointé sur la même boîte Gmail de test que les admissions) et à
  `FLOWS_ENV_ALLOW_LIST` des 3 `docker-compose.yml`.
- Les 4 champs (nom/email/fonction/message) sont une **hypothèse** basée sur ce
  qui est visible dans le prototype Figma — à confirmer avec Djo contre le
  vrai formulaire HTML une fois construit, comme cela avait été fait pour le
  formulaire de pré-inscription.

## Formulaire de pré-inscription (`formulaire_preinscription_ISETAG.html`)

Le formulaire déjà livré par le développeur front est un multipart POST unique
(champs + fichiers) vers une URL personnalisable (`action`). **Directus ne sait pas
parser un multipart mixte fichiers+champs** (vérifié empiriquement : ni `/items`,
ni un déclencheur Flow webhook ne peuplent les champs dans ce cas — `$trigger.body`
reste `{}`). Le circuit retenu (comportement demandé : les infos + documents sont
transmis au service des admissions par email, pas de consultation publique des
dossiers) :

1. **Le front amont doit être adapté** (2 requêtes au lieu d'une) :
   a. Générer un UUID par fichier côté client (`crypto.randomUUID()`), puis
      `POST {DIRECTUS_PUBLIC_URL}/files` en multipart pour **chaque fichier
      individuellement**, avec un champ `id=<uuid>` dans le form-data (Directus
      accepte un id fourni par le client — vérifié). Aucune lecture de retour
      n'est nécessaire ni possible (le rôle Public n'a pas de droit de lecture
      sur `directus_files`, volontairement — RGPD).
   b. `POST {DIRECTUS_PUBLIC_URL}/flows/trigger/<FLOW_ID>` en JSON (pas multipart)
      avec tous les champs texte du formulaire + les 3 UUID de fichiers obligatoires
      (`piece_identite`, `diplome_releve`, `photo_identite`) + `autres_documents` au
      format M2M attendu par Directus :
      `"autres_documents": {"create": [{"directus_files_id": "<uuid>"}, ...], "update": [], "delete": []}`
2. **Flow Directus** « Pré-inscription — Formulaire public » (trigger webhook,
   accountability `all`, configuré via l'API — pas encore dans le snapshot car les
   flows/opérations ne sont pas capturés par `directus schema snapshot`) :
   - Opération 1 `create_application` : crée l'item `admission_applications` avec
     `payload: "{{$trigger.body}}"`.
   - Opération 2 `notify_admissions` : envoie un email HTML à `{{$env.ADMISSIONS_EMAIL}}`
     avec le récapitulatif du dossier et des **liens sécurisés** vers les documents
     (`{{$env.PUBLIC_URL}}/admin/files/<uuid>` — ouverture nécessite une session
     Directus authentifiée ; pas de pièces jointes en clair, décision prise avec
     Djo pour protéger les données RGPD sensibles). Attention : la variable
     d'environnement exposée aux flows est `PUBLIC_URL` (nom interne utilisé par
     Directus lui-même), pas `DIRECTUS_PUBLIC_URL` (qui n'existe que dans nos
     fichiers `.env` — piège rencontré et corrigé : les liens renvoyaient
     `http://undefined/...` tant que `FLOWS_ENV_ALLOW_LIST` listait le mauvais nom).
   - Testé de bout en bout (upload avec id client → trigger JSON → item créé,
     fichiers liés, `autres_documents` lié via la table de jonction
     `admission_applications_files`, email correctement formé). L'envoi réel échoue
     tant que `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD` ne sont pas renseignés
     (actuellement vides, voir `.env`).
3. Permissions : rôle **Public** limité à `create` uniquement (aucune lecture) sur
   `admission_applications`, `directus_files`, `admission_applications_files`, avec
   la liste exacte des champs autorisés (pas de `status` ni `desired_program`,
   réservés au staff).
4. `ADMISSIONS_EMAIL` (adresse qui reçoit les notifications) ajouté aux `.env*`
   — actuellement un placeholder (`admissions@isetag-univ.net`), à confirmer.

Rôles & permissions à créer :
- **Service Admissions** : RW sur `admission_applications`, RO sur `programs`,
  aucun accès à `news`/`partners`.
- **Service Communication** : RW sur `news`, `testimonials`, `partners`,
  `stats_counters`, aucun accès à `admission_applications` (données RGPD sensibles).

## Les 27 filières à seeder

**Pôle Industriel & Technologique (9)** : froid (BTS Froid & Climatisation, HND, jour&soir),
electro (Électrotechnique, HND, jour), mecatro (Mécatronique, jour), btp (Bâtiment TP,
jour&soir), menuiserie (Menuiserie Ébénisterie, soir), chaudro (Chaudronnerie, jour),
install (Installation Sanitaire, jour), soudure (Soudure & Structures Métalliques, jour),
electro2 (Électronique, jour)

**Pôle Maritime & Logistique (4)** : shipping (Shipping Management, HND, jour),
douane (Douane & Transit, jour&soir), logist (Transport & Logistique, HND, jour),
portu (Logistique Maritime & Portuaire, jour)

**Pôle Gestion & Commerce (7)** : cge (Comptabilité & Gestion, HND, jour&soir),
mcv (Marketing-Commerce-Vente, jour&soir), grh (Gestion RH, soir),
banque (Banque & Finance, HND, jour), assurance (jour), manag (Management de Projet,
jour&soir), compta2 (Comptabilité Publique, soir)

**Pôle Communication & Digital (3)** : commorg (Communication des Organisations, soir),
journa (Journalisme, jour), infog (Infographie & Web Design, jour)

**Pôle Santé & Paramédical (4)** : infirm (Sciences Infirmières, jour),
sagef (Sage-femme, jour), kine (Kinésithérapie, jour), labo (Techniques Laboratoire, jour)

> ⚠️ **Conflit non résolu** : `CAHIER_EDITORIAL_ISETAG_RUBRIQUE_ADMISSIONS.docx`
> affirme explicitement *« L'ISETAG ne possède ni pôle Santé ni filière
> paramédicale »*. Signalé à l'utilisateur, qui a demandé de laisser les
> données telles quelles pour l'instant (pas de suppression) le temps de
> confirmer avec l'institution laquelle des deux sources est correcte — voir
> « État d'avancement » pour le contexte complet.

## Design System (Prototype V3 — référence finale, ne pas revenir dessus)

```css
--green: #2E7D51;    --green-l: #3A9D67;   --green-xl: #4BBF82;  --green-dim: #1B5C3A;
--black: #0D0D0D;    --dark: #111111;      --dark2: #181818;     --dark3: #1E1E1E;
--muted: rgba(255,255,255,.45);            --border: rgba(255,255,255,.08);
--ff-head: 'Playfair Display', serif;      --ff-body: 'Inter', sans-serif;
```
Composants signature : ruban vertical vert fixe à droite, hero full-bleed avec écusson
circulaire, 3 hero-cards translucides, bento news grid, bouton "READ NEWS" bicolore,
carte CTA verte pleine, calendar widget, navbar translucide avec crest.

## Variables d'environnement (.env — jamais commité)

```bash
DB_DATABASE=isetag
DB_USER=isetag
DB_PASSWORD=
DIRECTUS_SECRET=            # openssl rand -hex 32
DIRECTUS_ADMIN_EMAIL=admin@isetag-univ.net
DIRECTUS_ADMIN_PASSWORD=
DIRECTUS_PUBLIC_URL=http://localhost:8055
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=ISETAG <noreply@isetag-univ.net>
```

## Instructions pour Claude Code

1. **Stack figée et simplifiée** (voir plus haut) — ne jamais proposer React,
   WordPress, Strapi, Swarm, MinIO, Redis, ou un stack de monitoring dédié.
2. **Design V3 = référence finale** — ne pas revenir sur la palette ou la typo.
3. **Sitemap** — ~~7 routes verrouillées~~ **obsolète**, voir « Organisation en
   pages/sections » : la nav réelle (confirmée via le prototype Figma) est
   Accueil / Programmes / Admissions / Vie Campus / Actualités / Contact.
4. **Toujours du code prêt à l'emploi**, jamais de concepts génériques.
5. **Variables depuis `.env`** — jamais de valeurs hardcodées dans le code ou les
   fichiers commités.
6. **Commentaires en français** dans le code.
7. **Contexte local** : Cameroun, FCFA, bilinguisme FR/EN, réseau mobile parfois
   lent → images optimisées (WebP via Directus Assets), LCP < 2s prioritaire.
8. Avant toute commande destructive (`docker compose down -v`, `rm -rf`, reset de
   base de données), demander confirmation explicite.

## État d'avancement

- [x] Sitemap & cartographie URL (Livrable 1)
- [x] Proposition technique & financière signée (505 000 FCFA / 61 jours)
- [x] Schéma Directus conçu (11 collections, dont 3 ajoutées après revue de la maquette
      Figma : `tuition_plans`, `scholarships`, `documents`)
- [x] Stack simplifiée décidée (sans Swarm/MinIO/Redis)
- [x] `docker-compose.yml` dev placé et testé (`make dev`)
- [x] Collections Directus créées dans l'Admin UI
- [x] Rôles Admissions / Communication configurés
- [x] Snapshot généré (`cms/snapshots/current.yaml`)
- [x] Script de seed des 27 filières
- [x] Nginx (TLS, Gzip, HSTS, CSP) pour prod (`isetag-univ.net` / `cms.isetag-univ.net`)
      et staging (`staging.isetag-univ.net` / `cms-staging.isetag-univ.net`)
- [x] `docker-compose.yml` staging et prod (réseau `isetag_edge` partagé sur le VPS unique)
- [x] CI/CD GitHub Actions (`ci.yml` + `deploy.yml`, build frontend -> ghcr.io -> SSH deploy)
      — le job de déploiement reste inactif tant que `frontend/Dockerfile` n'existe pas
- [x] `scripts/backup.sh` et `scripts/deploy.sh` implémentés
- [x] Schéma `admission_applications` aligné sur `formulaire_preinscription_ISETAG.html`
      (34 champs, fichiers piece_identite/diplome_releve/photo_identite avec vraies
      contraintes FK, M2M `autres_documents` via `admission_applications_files`)
- [x] Flow Directus « Pré-inscription — Formulaire public » (webhook → création de
      l'item → email au service admissions avec liens sécurisés) — testé de bout en
      bout en dev avec de vrais fichiers (PDF/JPEG valides) et une vraie boîte Gmail,
      liens `{{$env.PUBLIC_URL}}/assets/<uuid>` cliquables, restriction par rôle
      vérifiée (Service Communication refusé, Service Admissions accepté)
- [x] Dossiers de navigation Content (Formations / Admissions / Vie Campus /
      Actualités / Ressources / Accueil & Global) — voir « Organisation du menu
      Content » ci-dessus
- [x] Lecture publique ouverte (`scripts/provision_public_read.py`) : rôle
      Public en lecture seule sur les 10 collections publiques (contenu
      `published` uniquement quand un champ `status` existe), dossier Directus
      "Public" comme allowlist pour les fichiers publiquement lisibles
      (`admission_applications` reste totalement invisible, vérifié via la spec
      OpenAPI anonyme)
- [x] Livrable pour l'équipe frontend : [`docs/frontend-api-guide.md`](docs/frontend-api-guide.md)
      (base URL, auth, correspondance pages Figma ↔ collections, circuit du
      formulaire de pré-inscription) + [`docs/openapi-public.json`](docs/openapi-public.json)
      (spec OpenAPI générée par Directus, à préférer en version live via
      `GET {PUBLIC_URL}/server/specs/oas`)
- [x] Modèle pages/sections (page-builder M2A) revu après ouverture réelle du
      prototype Figma — 6 pages (Accueil, Programmes, Admissions, Vie Campus,
      Actualités, Contact), 9 types de blocs dont 2 nouvelles relations O2M
      (étapes) et M2M (témoignages, formations mises en avant) — voir
      « Organisation en pages/sections » ci-dessus (**note** : les noms de
      collections cités ci-dessous ont depuis changé, voir l'entrée de
      restructuration plus bas — historique conservé tel quel). Bilinguisme
      FR/EN vérifié sur tous les champs éditoriaux
      (title/heading/subtitle/body/content/description en `_fr`/`_en`) ; un
      trou a été trouvé et corrigé après coup sur les champs CTA/bouton
      (`cta_label`, `button_label`, `tag_label` n'existaient qu'en `_fr` sur
      `block_hero`/`block_feature`/`block_testimonials_highlight`/`block_cta_banner`,
      devenus depuis `admissions_hero`/`admissions_feature`/
      `actualites_testimonials_highlight`/`admissions_cta_banner`).
      Décision produit : **pas de fallback FR si `_en` est vide** (champ
      affiché vide côté anglais, pas de filet de sécurité côté frontend) —
      voir « Bilinguisme FR/EN » dans `docs/frontend-api-guide.md`.
      Lecture publique vérifiée par requête anonyme, pages seedées
      vides (à remplir par l'équipe communication/admissions). Blocs répartis
      dans les dossiers Content existants (pas de dossier séparé — voir
      « Organisation du menu Content » ci-dessus pour le découpage retenu).
- [x] Page Contact (identifiée uniquement via la revue Figma, absente du
      schéma jusqu'ici) : collection `contact_messages`, Flow « Contact —
      Formulaire public » (`scripts/provision_contact_flow.py`), `CONTACT_EMAIL`
      ajouté aux `.env*` — testé de bout en bout en dev. Champs du formulaire
      (nom/email/fonction/message) à confirmer avec Djo contre le vrai HTML.
- [x] Contenu réel de la page Admissions rempli depuis
      `CAHIER_EDITORIAL_ISETAG_RUBRIQUE_ADMISSIONS.docx` (fourni par l'utilisateur,
      compression volontaire en 1 seule page — le document décrit en réalité 4
      pages N1/N2 distinctes, la scission a été reportée à plus tard avec
      l'équipe frontend) : 17 sections (`admissions_hero` ×1, `admissions_feature`
      ×4, `admissions_richtext` ×10 dont 2 avec image, `admissions_steps` à 4
      étapes, `admissions_cta_banner` ×1 — noms mis à jour après la
      restructuration ci-dessous, contenu inchangé), 7 photos uploadées dans le dossier "Public"
      (dont 1 `.HEIC` convertie en JPEG), `tuition_plans` rempli (10 grilles
      tarifaires, `status: published`), `scholarships` rempli en `status: draft`
      (3 bourses annoncées avec l'Université Montplaisir Tunis, **non
      publiées** tant que non confirmées pour 2026-2027). Nouveau champ
      `image` ajouté (optionnel, aujourd'hui sur `admissions_richtext`) après avoir détecté qu'une
      première version intégrait des URLs d'images à la main dans le HTML
      WYSIWYG (`{{$env.PUBLIC_URL}}/assets/...` — cette syntaxe ne fonctionne
      que dans les templates d'email des Flows, pas dans le contenu normal des
      items — corrigé avant publication).
      **Reste ouvert** (reporté tel quel depuis le document, à valider par
      l'ISETAG, voir aussi la dernière section de la page Admissions) : date
      exacte de la 3e tranche BTS/HND (29 février 2027 est impossible), intitulé
      manquant ligne n° 02 du tarif HND technique, dates limites Licence/Master,
      coordonnées de contact à harmoniser, confirmation des avantages maritimes
      (STCW 95 etc.), **conflit non résolu** sur le pôle Santé & Paramédical
      (voir plus haut, section Schéma Directus — laissé tel quel dans le
      catalogue `poles`/`programs` en attendant confirmation de l'utilisateur),
      et aucune photo maritime disponible dans le lot fourni pour illustrer
      l'accordéon "Modalités — Maritime".
- [x] **Restructuration des collections de blocs : de "partagées entre pages"
      à "une collection par page"**. Suite à un retour explicite de
      l'utilisateur (répété deux fois, en donnant l'exemple concret d'un
      `hero_block` qui devrait être différent entre Accueil et Admissions),
      les anciennes collections `block_hero`/`block_feature`/`block_richtext`/
      `block_cta_banner`/`block_steps`(+items)/`block_news_preview`/
      `block_programs_highlight`(+jonction)/`block_testimonials_highlight`
      (+jonction)/`block_documents_list` ont été supprimées et remplacées par
      des collections préfixées par page (`admissions_hero`,
      `accueil_news_preview`, `actualites_documents_list`, etc. — voir
      « Organisation en pages/sections » ci-dessus pour la liste complète et
      la convention `<page_key>_<type_de_bloc>`). Migration effectuée sans
      perte : les 17 sections réelles de la page Admissions ont été copiées
      vers les nouvelles collections (contenu, `sort`, UUID de fichiers
      inchangés) avant suppression des anciennes tables — vérifié par
      deep-fetch anonyme identique avant/après. `pages_sections.item.
      one_allowed_collections`, `scripts/provision_public_read.py`,
      `cms/snapshots/current.yaml`, `docs/openapi-public.json` et
      `docs/frontend-api-guide.md` mis à jour en conséquence. Au passage,
      correction d'une erreur d'attribution de page : `block_testimonials_highlight`
      ("Success Stories") a été rangé par erreur sous `accueil_*` alors que
      `docs/frontend-api-guide.md` (écrit lors d'une session précédente,
      relecture explicite du Figma) le place sur la page **Actualités** — recréé
      sous `actualites_testimonials_highlight` avant que quiconque ne s'appuie
      dessus (collection vide, aucune perte de données). Programmes/Vie
      Campus/Contact n'ont pas encore leurs collections de blocs dédiées
      (pas de contenu saisi) : à créer au moment voulu en copiant le schéma
      de champs de `admissions_*` comme référence, jamais en réutilisant une
      collection d'une autre page.
- [x] **Suite au retour ci-dessus** : deuxième correction de dossiers Content,
      cette fois signalée par l'utilisateur lui-même ("you still set the
      Ressource as a page" / "formations where does it comes from??"). Les
      dossiers "Formations" et "Ressources" n'étaient pas des pages du
      prototype Figma (6 pages réelles : Accueil, Programmes, Admissions, Vie
      Campus, Actualités, Contact) mais apparaissaient au même niveau que les
      vrais dossiers-pages dans le menu Content, ce qui prêtait à confusion.
      "Formations" renommé "Programmes" (`poles`/`programs`) ; "Ressources"
      fusionné dans "Actualités" (`testimonials`/`documents`, qui n'alimentent
      que les sections Success Stories/ressources de cette page). Vérifié :
      `pages` contient bien 6 pages composées + `a_propos` (conservée,
      probablement inutile — contenu absorbé dans le hero Accueil) ;
      l'utilisateur a confirmé garder Admissions comme page distincte malgré
      son omission dans un message listant "5 pages" (juste une omission,
      pas une demande de suppression).
- [x] **VPS commandé et Directus backend déployé dessus** (2026-07-30) — LWS
      "Pack VPS S", Ubuntu 24.04 LTS, IP `31.207.34.25` (`vps122706`, 4 Go RAM,
      98 Go disque). Accès root sécurisé par clé SSH dédiée uniquement
      (mot de passe désactivé côté `sshd` — `PasswordAuthentication no`,
      `PermitRootLogin prohibit-password` — root par mot de passe était exposé
      à internet avant ce durcissement) ; `ufw` actif, seuls 22/80/443 ouverts.
      Stack déployée dans `/opt/isetag/` (structure calquée sur le repo :
      `docker/prod/`, `cms/{uploads,extensions,snapshots}`, `nginx/`,
      `scripts/`, `.env.prod` avec secrets générés dédiés prod, `chmod 600`).
      **Scope volontairement partiel** : seuls les services `postgres` +
      `directus` tournent (pas `nginx`/`frontend`/`certbot`) — le service
      `frontend` du compose prod exige une image `FRONTEND_IMAGE` qui n'existe
      pas encore (`frontend/Dockerfile` toujours absent), et le sous-domaine
      `cms.isetag-univ.net` n'a pas encore de DNS pointé dessus (voir point
      ci-dessous sur le domaine). Schéma appliqué (`directus schema apply` via
      `docker exec`), et les 3 scripts de provisioning rejoués avec succès
      (vérifié par deep-fetch anonyme sur l'instance prod elle-même, retour
      `[]` attendu — schéma + permissions OK, aucun contenu encore saisi en
      prod, normal). **Gap découvert au passage** : les rôles/policies internes
      "Service Admissions"/"Service Communication" avaient été créés à la main
      via l'Admin UI en dev, jamais scriptés — absents sur tout environnement
      neuf, ce qui a fait échouer `provision_admissions_flow.py`/
      `provision_contact_flow.py` au premier essai sur prod ("policy
      introuvable"). Corrigé en ajoutant `scripts/provision_roles.py` (+
      wrapper `.sh` + cible Makefile `provision-roles`), à rejouer **avant**
      les deux scripts de Flow sur tout nouvel environnement — `scripts/deploy.sh`
      mis à jour pour l'appeler dans le bon ordre.
- [ ] **Domaine `isetag-univ.net` : un site WordPress réel et en production y
      tourne déjà**, hébergé sur l'ancienne formule d'hébergement mutualisé
      LWS ("Starter") liée au domaine — **information critique découverte
      tardivement**, après qu'un premier conseil de "passer en formule
      domaine" (sans hébergement) ait été donné par erreur suite à
      l'expiration de cette formule ; corrigé avant toute action destructive.
      Ne jamais toucher aux enregistrements DNS de l'apex (`isetag-univ.net`)
      ni de `www` sans confirmation explicite — ils pointent vers
      l'hébergement WordPress existant. Seuls des sous-domaines neufs
      (`cms.isetag-univ.net`, `staging.isetag-univ.net`,
      `cms-staging.isetag-univ.net`) doivent être ajoutés en DNS vers le VPS
      (`31.207.34.25`), sans toucher aux enregistrements existants. Le vrai
      basculement de l'apex vers le nouveau site (une fois prêt) est une
      étape délibérée à coordonner avec l'institution/Djo, pas un effet de
      bord de la configuration VPS. **Reste à faire** : renouveler/gérer la
      formule d'hébergement WordPress expirée (ne pas la laisser expirer
      définitivement — perte de données irréversible), ajouter le DNS
      `cms.isetag-univ.net` → `31.207.34.25` une fois l'accès à la zone DNS
      restauré, puis construire `frontend/Dockerfile` avant de pouvoir amener
      les services `nginx`/`frontend`/`certbot` du compose prod.
- [ ] `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD` de dev pointent actuellement vers une
      boîte Gmail personnelle utilisée pour les tests — à remplacer par les
      identifiants SMTP définitifs avant la mise en production, et `ADMISSIONS_EMAIL`
      par la vraie adresse du service des admissions (actuellement une adresse de test)
- [ ] Front à adapter pour le nouveau circuit de soumission du formulaire de
      pré-inscription (upload des fichiers un par un avec id généré côté client, puis
      un seul POST JSON vers le Flow) — voir section dédiée ci-dessus
- [ ] Composants Angular (Home, Formations, Admissions) — hors périmètre, pris en charge par un autre développeur
