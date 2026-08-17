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
- [x] **Contenu dev migré vers prod** (2026-07-30) : les 17 sections
      Admissions (avec leurs 8 fichiers image) + `poles` (5), `programs` (27),
      `tuition_plans` (10) copiés de dev vers prod via un script one-off
      (IDs entiers préservés pour garder les FK cohérentes, séquences Postgres
      resynchronisées après coup). Le seul `testimonials` de dev ("Test
      Etudiant") a été volontairement **exclu** — donnée de test, pas du
      contenu réel. Fichiers re-rattachés au dossier "Public" après migration
      (sinon 403 sur `/assets/<uuid>` malgré la ligne DB présente — le modèle
      de lecture publique des fichiers est un allowlist par dossier, voir
      `scripts/provision_public_read.py`).
- [x] **Accès temporaire prod pour le développeur frontend (Djo)**, avant que
      `cms.isetag-univ.net` n'existe en DNS : port `8055` direct s'est révélé
      **injoignable de l'extérieur** malgré un `ufw allow` correct — LWS
      applique un pare-feu réseau en amont de la VM qui bloque silencieusement
      les ports non standards (confirmé : aucune trace, ni autorisée ni
      bloquée, dans les logs noyau `ufw` pour ce port, contrairement au port 80
      qui répond bien avec un "connection refused" propre). Contournement :
      un conteneur `nginx:alpine` autonome (`isetag-nginx-temp`, hors compose
      pour éviter la dépendance au service `frontend` inexistant) proxifie le
      port 80 vers `isetag-directus-prod:8055` en interne ; `ufw` restreint le
      port 80 à l'IP publique du développeur uniquement. `CORS_ORIGIN` élargi
      pour inclure `http://localhost:4200`/`4201`. **Marqué TEMP** dans
      `docker/prod/docker-compose.yml` — à retirer une fois Nginx/TLS réel en
      place (voir point DNS ci-dessus).
- [x] **Dépôt GitHub créé** (2026-07-30) : le projet n'était versionné nulle
      part avant (pas de `.git` local, aucun dépôt distant) — tout le
      déploiement VPS avait été fait à la main par SSH jusqu'ici. Dépôt public
      [`josephgounde/isetag-directus-backend`](https://github.com/josephgounde/isetag-directus-backend),
      `.env` et secrets correctement exclus (vérifié par `git grep` avant push
      vu la visibilité publique). **Reste à faire** : ajouter les secrets
      `VPS_HOST`/`VPS_USER`/`VPS_PORT`/`VPS_SSH_KEY` dans les paramètres du
      dépôt pour que `deploy.yml` fonctionne réellement (actuellement no-op
      tant que `frontend/Dockerfile` n'existe pas).
- [x] **Page Admissions comparée au prototype Figma** (2026-07-30) : le
      prototype montre une structure bien plus simple (hero → 2 étapes avec
      formulaire intégré → tarifs/bourses → newsletter) que les 17 sections
      actuelles (10 `admissions_richtext`, 4 `admissions_feature`). Plan de
      consolidation théorique établi (quel contenu va où) mais **pas encore
      appliqué** — l'équipe design retravaille le prototype pour l'aligner sur
      le cahier éditorial, la consolidation attendra cette version à jour.
      Deux blocs contiennent par ailleurs des notes éditoriales internes
      ("à valider avant publication") qui ne devraient jamais être publiques :
      `admissions_richtext` #8 (note sur une photo manquante) et #10 (note
      entière, à supprimer) — à corriger indépendamment de la consolidation.
- [x] **Page Accueil construite** (2026-07-30) depuis
      `contenuç_accueil/Texte Page Accueil Site ISETAG.docx` (texte) +
      `contenuç_accueil/CHOISIR L'ISETAG/*.jpeg` (images uniquement — le texte
      de ce dossier a été explicitement écarté, c'est le contenu d'une page
      différente). Comparée au prototype Figma d'abord : alignement structurel
      bon, les 9 sections du docx correspondent 1:1 aux sections du prototype
      (contrairement à Admissions, aucune restructuration nécessaire).
      7 nouvelles collections créées (`accueil_hero`, `accueil_poles_highlight`,
      `accueil_reasons`+`_items`, `accueil_cta_banner` [2 lignes],
      `accueil_partners_highlight`+jonction, `accueil_testimonials_highlight`
      +jonction, `accueil_vie_campus_teaser`) plus `description_fr/en` ajoutés
      à `poles` (les 5 pôles avaient déjà nom/slug mais pas de texte de
      présentation). `partners` rempli avec les 8 vrais partenaires du docx
      (Port Autonome de Douala, Université de Douala, ENSP Douala, UMT Tunis,
      IAHF, EEMI, IHECF Paris, Regional Maritime University Ghana) — **logos
      pas encore fournis**, champ `logo` laissé vide. 1 vrai témoignage alumni
      ajouté à `testimonials`. Sur les 6 images fournies, seules 3 avaient une
      correspondance évidente avec les 5 "raisons" du docx (ateliers, cité
      universitaire, bilinguisme) ; les 2 restantes (partenariats académiques,
      cadre rigoureux) ont reçu une image de réemploi choisie par
      approximation, **à valider/remplacer** si de meilleures photos arrivent.
      Contenu vérifié par deep-fetch anonyme sur dev, puis **migré vers prod**
      le jour même (schéma appliqué via `directus schema apply` + redémarrage
      du conteneur requis pour que l'API vive recharge son cache de schéma —
      sans ça, les nouvelles collections restent invisibles même après un
      apply réussi ; contenu recréé directement sur prod plutôt que copié avec
      IDs préservés, plus simple ici puisqu'aucune collection accueil_* ne
      pré-existait). Revérifié par deep-fetch anonyme sur prod : les 8
      sections et les 6 images se chargent correctement.
- [x] (2026-07-31) Corrections section pôles Accueil, demandées après relecture du
      prototype Figma : `accueil_poles_highlight.heading_fr` était "Pôles de
      formation" (texte générique choisi faute de mieux dans le docx éditorial) —
      remplacé par "Choisis le pôle qui te valorise", le vrai titre du prototype,
      sur dev et prod. Champ `image` (uuid → directus_files) ajouté à `poles`
      (schéma appliqué sur prod + conteneur redémarré, cf. gotcha ci-dessus ;
      `provision_public_read.py` mis à jour et rejoué dev+prod pour le dossier
      Public par défaut du champ). 4 images sur 5 déposées par l'utilisateur et
      attachées (industriel-techno, gestion-commerce, communication-digital,
      sante-paramedical) sur dev et prod, vérifiées publiquement servables
      (200) — **il manque l'image du pôle maritime-logistique** (`image: null`),
      à fournir plus tard. Note pour le frontend : chaque carte pôle du
      carrousel affiche aussi une liste de programmes courte
      (ex. "Shipping Management | Douane et Transit | ...") — ce n'est PAS un
      champ de `poles`, il faut requêter `programs?filter[pole][_eq]=<id>`
      séparément ; les libellés du prototype sont parfois plus courts que
      `programs.name_fr` (ex. "Portuaire" vs "Logistique Maritime & Portuaire"),
      à réconcilier avec l'équipe design si besoin.
- [x] (2026-08-01) Comparaison structurelle du prototype Figma **v2** d'Admissions
      (mis à jour par l'équipe design) vs le contenu Directus actuel (17 sections) :
      nouvelle maquette bien plus courte — hero (titre changé en "Comment
      S'inscrire ?"), 2 étapes narratives + formulaire de pré-inscription (4
      onglets, inchangé), section Tarifs en cartes "Cycle BTS/Licence/Master",
      section Bourses en cartes (Bourse SNK, Bourse Université Montplaisir
      Tunis). Disparaissent de la v2 (encore en ligne aujourd'hui) : "Modalités
      d'admission", détail pièces par cycle, "Conditions pratiques" (EPI/
      logement), FAQ, CTA final "Prêt à commencer ?", et les 2 blocs de notes
      internes éditoriales (`admissions_richtext` #8 et #10) — pas d'action
      prise, en attente de confirmation de l'équipe design que ces sections
      sont bien abandonnées et pas juste absentes de cette itération Figma.
      Découverte importante : `tuition_plans` (10 lignes réelles, jamais
      utilisée par la page) correspond presque exactement aux cartes Tarifs —
      pas de carte Maritime dans la maquette malgré 2 lignes Maritime en base,
      laissées de côté sans action sur demande explicite de l'utilisateur (pas
      un problème, à traiter quand le design ajoutera cette carte).
      `scholarships` (0 ligne) avait un schéma incomplet pour les cartes
      Bourses — champs `image`, `cta_label_fr/en`, `cta_url` ajoutés (structure
      seulement, sur demande explicite : "laisse le contenu vide, assure-toi
      que la structure soit là"), appliqué sur dev et prod. Contenu réel des 2
      bourses (texte, images) toujours à fournir par l'équipe design/contenu —
      la maquette elle-même n'affiche que du texte de remplissage identique
      sur les deux cartes.
- [x] (2026-08-01) Hero Accueil : nouvelle image fournie (façade + blason
      ISETAG sur socle) remplace l'ancienne, convertie en WebP (1,58 Mo → 111
      Ko) avant upload ; ancien fichier supprimé de la bibliothèque sur dev et
      prod pour ne rien laisser d'orphelin.
      Section "Vie sur nos Campus" (Accueil) : image de fond fournie (façade
      de nuit, enseigne ISETAG illuminée — confirmée identique à l'image du
      prototype Figma v2) attachée à `accueil_vie_campus_teaser.image`.
      Champs `cta_label_fr/en` + `cta_url` ajoutés à cette collection (n'existaient
      pas) et remplis avec du contenu réel cette fois (pas juste la structure,
      contrairement à `scholarships`) : label "Découvrez notre campus" trouvé
      dans le prototype Figma, URL `/vie-campus/` déduite de la convention de
      routage déjà vue ailleurs dans le contenu — à confirmer avec le
      frontend si la route réelle diffère.
- [x] (2026-08-01) `accueil_vie_campus_teaser_gallery` créée (O2M, même
      schéma que `accueil_reasons`/`accueil_reasons_items` : champ alias
      `gallery` côté parent, `image`+`sort` côté enfant) pour la mosaïque de
      photos vue dans le prototype Figma v2 de cette section — le prototype
      montre ~5-6 photos en plus du fond déjà en place, plus une citation
      d'étudiant incrustée (Charles Mengue) volontairement non modélisée
      (décision explicite : attendre le contenu réel avant de choisir
      `testimonials` vs champs dédiés). `heading_fr` volontairement laissé
      inchangé malgré l'écart avec Figma ("La Vie sur nos Campus" vs "Un
      cadre d'études structuré à Yassa" en base) — décision explicite de
      l'utilisateur. Structure appliquée dev+prod, permissions publiques
      provisionnées, collection vide (`gallery: []`), aucune photo fournie.
- [x] (2026-08-01) Retour sur la citation étudiant (Charles Mengue) de la
      section Vie sur nos Campus : décision finale de l'utilisateur — construire
      la structure quand même (contrairement à la décision précédente de tout
      sauter), juste sans contenu. 4 champs ajoutés à `accueil_vie_campus_teaser`
      (`quote_text_fr/en`, `quote_author`, `quote_program`), dédiés plutôt
      qu'un lien vers `testimonials` (un seul témoignage affiché ici, pas une
      liste). Appliqué dev+prod, tous `null`, aucune permission à toucher
      (champs texte simples sur une collection déjà publique).
- [x] (2026-08-03) Comparaison structurelle + contenu du prototype Figma
      **v2** de la page **Accueil** (le prototype a maintenant du contenu réel
      partout, plus des blocs de test) contre le schéma/contenu Directus
      existant, frame par frame (frame "Accueil - Desktop", node-id 4116:1344).
      Résultat :
      - `poles.description_fr` (5 pôles) et `accueil_reasons.items` (5
        raisons) concordaient déjà mot pour mot avec Figma — aucune action.
      - Champs manquants ajoutés (structure seulement, sur dev puis appliqué
        sur prod) : `accueil_cta_banner.eyebrow_fr/en` +
        `cta2_label_fr/en`/`cta2_url` (le prototype a 2 boutons par bandeau,
        pas 1) ; `accueil_testimonials_highlight.eyebrow_fr/en` +
        `cta_label_fr/en`/`cta_url` (même pattern que
        `actualites_testimonials_highlight`) ; `accueil_vie_campus_teaser.eyebrow_fr/en`.
      - Contenu réécrit pour coller au texte finalisé du prototype (remplace
        une copie plus ancienne, rédigée avant que le texte on-page soit
        arrêté) : `accueil_hero` (title/subtitle/2 CTA), les 2 lignes
        `accueil_cta_banner` (teaser Admissions + bandeau final),
        `accueil_partners_highlight.heading_fr`.
      - Contenu réel enfin disponible pour des champs laissés vides le
        2026-08-01 : `accueil_vie_campus_teaser.quote_text_fr/quote_author/quote_program`
        remplis ("On se sent bien dans les logments" — coquille d'origine
        conservée telle quelle —, "Charles Mengue", "L3 Banques et Finance") ;
        `accueil_testimonials_highlight.eyebrow_fr` rempli ("Les Alumnis de
        ISETAG" — confirme que c'est un second niveau de titre, pas un
        heading_fr à remplacer). Ceci confirme aussi que la décision du
        2026-08-01 de ne pas toucher `accueil_vie_campus_teaser.heading_fr`
        était correcte : "La Vie sur nos Campus" est un eyebrow au-dessus, pas
        un remplacement.
      - Décision explicite : **`poles.image`** (5 photos réelles fournies par
        l'utilisateur, uploadées le 2026-07-31) n'a **pas** été remplacée par
        les photos du prototype Figma v2, qui utilise des silhouettes stock
        génériques par métier (casque de chantier, tenue militaire, blouse
        médicale, etc.) plutôt que les vraies photos institutionnelles — les
        photos réelles restent préférables, sauf demande contraire explicite
        de l'équipe design.
      - Logos partenaires et photos Vie Campus non extractibles de Figma dans
        cette passe (voir juste au-dessus) — **résolu le jour même** : voir
        entrée suivante, l'utilisateur a fourni les fichiers réels directement.
- [x] (2026-08-03) Logos partenaires + galerie Vie Campus fournis par
      l'utilisateur dans `contenuç_accueil` (8 fichiers `part1.png`…`part8.png`
      + `vie campus1/2/3`), identifiés visuellement et attachés : `partners.logo`
      rempli sur les 8 lignes (Port Autonome de Douala, Université de Douala,
      ENSP Douala, Université Montplaisir Tunis, IAHF, EEMI, IHECF Paris,
      Regional Maritime University) ; `accueil_vie_campus_teaser_gallery` rempli
      avec 3 lignes (`sort` 1-3). Nouvelle règle projet appliquée pour la
      première fois : toute image dépassant 1 Mo est convertie en WebP (et
      redimensionnée à ~2000px de large si nécessaire) avant upload — deux des
      trois photos Vie Campus (17,5 Mo et 27,7 Mo en JPEG) ont été converties
      ainsi (175 Ko / 435 Ko en sortie) ; la troisième (339 Ko) et les 8 logos
      (tous < 10 Ko) sont restés dans leur format d'origine. Appliqué dev+prod,
      vérifié via `/assets/<uuid>`.
      - Trouvé par accident (image préchargée par Figma pendant l'audit
        Accueil) : un visuel réel "Bourse Académique d'Innovation" de la
        **SNK Foundation** (bourse pour bacheliers scientifiques, dépôt via
        snk-foundation.org, deadline 15 août 2026). **Correction** : ce
        visuel appartient bien à la page Admissions (frame "Admissions -
        Desktop", carte "Bourse SNK"), pas à une page hors périmètre comme
        supposé le 2026-08-03 au moment de la trouvaille — utilisé le jour
        même dans l'audit Admissions ci-dessous.
- [x] (2026-08-03) Comparaison structurelle + contenu du prototype Figma
      **v2** de la page **Admissions** (frame "Admissions - Desktop") contre
      le schéma/contenu Directus existant. Le contenu réel du prototype a
      confirmé deux angles morts identifiés le 2026-07-31 (`tuition_plans`
      jamais branchée, `scholarships` toujours vide) :
      - **Nouvelles collections de bloc** créées et appliquées dev+prod :
        `admissions_tuition_highlight` et `admissions_scholarships_highlight`
        (heading_fr/en uniquement, même pattern que
        `accueil_poles_highlight` — pas de sélection curatée, le frontend
        requête `tuition_plans`/`scholarships` directement, triés par
        `display_order`). Ajoutées à `pages_sections.item.one_allowed_collections`
        et à `provision_public_read.py`.
      - **`tuition_plans`** (10 lignes réelles) branchée à la page (nouvelle
        section, sort=11, juste après l'intro "Tarifs & Bourses"). Écart de
        montant trouvé et corrigé sur confirmation explicite de
        l'utilisateur : `id=6` ("Licence — Sciences de gestion appliquée")
        était à 500 000 FCFA, corrigé à **395 000 FCFA** (valeur confirmée
        par l'utilisateur, conforme au prototype).
      - **`scholarships`** (0 ligne) rempli avec 2 lignes réelles (nouvelle
        section, sort=12) : "Bourse SNK" (description/conditions/CTA tirés du
        vrai flyer SNK Foundation trouvé la veille, image attachée,
        `cta_url` = `https://www.snk-foundation.org`) et "Bourse de
        l'Université Montplaisir Tunis" (texte honnête repris de
        `admissions_richtext` — conditions "en cours de confirmation", pas
        d'image dans le prototype, `cta_url` laissé `null`).
      - `pages_sections` de la page Admissions renumérotée en conséquence :
        17 → **19 sections** (les sections sort 11-17 d'origine décalées à
        13-19 pour faire de la place aux 2 nouvelles en position 11-12).
      - **Décision explicite de l'utilisateur** : `admissions_hero.title_fr`
        **reste** "Construisez votre parcours à l'ISETAG" — le prototype
        Figma v2 affiche "Comment s'inscrire ?" mais l'utilisateur a choisi
        de ne pas aligner ce champ. Écart connu, volontaire, ne pas
        "corriger" sans nouvelle instruction.
      - Reste non résolu (inchangé depuis le 2026-07-30) : le texte
        "cérémonie de lauréats" apparaît deux fois dans le prototype sans
        section dédiée dans les 19 actuelles — pas d'action prise.
- [x] (2026-08-03) **Bug schéma corrigé** : plusieurs champs fichier
      (`type: uuid`, `meta.special: ["file"]`, interface `file-image`) étaient
      configurés comme des champs fichier **sans la relation FK réelle** vers
      `directus_files` derrière. Résultat concret constaté par l'utilisateur :
      les champs affichaient bien la vraie valeur (UUID) via l'API, le fichier
      existait et était servi correctement par `/assets/<uuid>`, **mais
      l'Admin UI affichait "Choose File from Library" comme si le champ était
      vide** — le composant file-picker ne peut pas résoudre/afficher la
      vignette sans la relation. `fields=*,champ.*` en deep-fetch API
      retournait aussi juste la valeur brute sans jamais faire l'expansion.
      Audit systématique des 17 champs fichier de tout le schéma
      (`GET /fields` puis `GET /relations/<collection>/<field>` pour chacun) :
      **6 champs touchés**, corrigés en créant la relation manquante via
      `POST /relations` (dev, puis snapshot/apply/restart vers prod) :
      - `accueil_vie_campus_teaser_gallery.image` — introduit par erreur dans
        cette session (2026-08-01, script `add_vie_campus_gallery.py`) : la
        relation O2M parent↔enfant avait été créée, mais pas la relation M2O
        `image` → `directus_files` elle-même.
      - `partners.logo`, `documents.file`, `news.cover_image`,
        `programs.cover_image`, `testimonials.photo` — gap **préexistant**,
        antérieur à ce projet Directus (pas introduit par le travail de cette
        session), présent depuis la création initiale de ces collections de
        base. Explique pourquoi l'utilisateur ne voyait aucune image sur
        `partners`/`accueil_vie_campus_teaser_gallery` dans l'Admin malgré des
        uploads réussis (logos partenaires et galerie Vie Campus faits plus
        tôt le même jour).
      Les 17 champs fichier du schéma ont été vérifiés un par un après coup —
      tous ont désormais une relation FK réelle vers `directus_files`, sur dev
      et prod.
- [x] (2026-08-03) Revue section par section de la page Admissions contre le
      prototype Figma **v2** mis à jour (frame "Admissions - Desktop"), pour
      confirmer que tout le contenu du prototype a bien sa place dans Directus.
      Trois écarts trouvés et corrigés, dev + prod :
      - **`admissions_brochure`** (nouvelle collection) — le bloc "Brochure
        admissions" / "Télécharger notre brochure" du prototype n'avait aucune
        collection dans le schéma. Créée (`heading_fr/en`, `text_fr/en`,
        `cta_label_fr/en`, `file` → relation réelle vers `directus_files`,
        interface `file` et non `file-image` car c'est un PDF), ajoutée à
        `pages_sections.item.one_allowed_collections` et à
        `provision_public_read.py` (lecture publique + dossier "Public" par
        défaut sur `file`). Contenu texte rempli, **`file` laissé vide** : le
        PDF de la brochure n'a pas été fourni — structure prête, à remplir dès
        réception. Insérée en section 6 (juste après les 3 cartes
        Pré-inscription/Tarifs/Modalités).
      - **Texte "cérémonie de lauréats" — FAUSSE PISTE, corrigée le jour
        même**. Ce texte, présent deux fois dans le prototype et sans section
        dédiée depuis le 2026-07-31, avait été traité comme un contenu
        manquant : une nouvelle ligne `admissions_richtext` avait été créée et
        insérée avant la carte "Prêt à commencer ?". En revérifiant
        visuellement le prototype Figma (scroll réel dans le frame, pas
        seulement le texte brut extrait), il s'est avéré que ce texte est en
        réalité le **texte de remplacement (placeholder) que Figma affiche
        comme description sur les deux cartes Bourses** ("Bourse SNK" et
        "Bourse de l'Université Montplaisir Tunis") — déjà noté comme tel dès
        le 2026-08-01 ("Figma affiche un texte de test"). Ce n'est donc pas un
        contenu distinct à ajouter : les vraies descriptions (`scholarships.description`,
        remplies le 2026-08-03) remplacent déjà correctement ce placeholder.
        La section ajoutée par erreur a été retirée de `pages_sections` et la
        ligne `admissions_richtext` supprimée, sur dev et prod, le jour même.
      - **Notes éditoriales internes exposées publiquement** (bug trouvé
        pendant cette revue, pas un écart Figma) : la dernière section de la
        page (`admissions_richtext` id=10, "points signalés par l'équipe
        éditoriale, à valider avant publication") n'a jamais dû être publique
        — `admissions_richtext` a une lecture publique inconditionnelle, donc
        ces notes internes ("date 29 février 2027 impossible", "intitulé
        manquant ligne 02", etc. — voir l'entrée du 2026-08-01 ci-dessus où
        elles sont déjà archivées in extenso) étaient lisibles par n'importe
        qui via l'API publique et potentiellement affichées sur le site en
        production. Section retirée de `pages_sections` et ligne supprimée de
        `admissions_richtext` (contenu déjà conservé dans ce fichier, aucune
        perte).
      Page Admissions : 19 sections avant comme après (une section retirée —
      notes internes —, une ajoutée — brochure — après correction de la fausse
      piste ci-dessus). Vérifié via l'API publique anonyme (page complète,
      `admissions_brochure`, confirmation 403 sur l'ancien id=10 et sur la
      ligne cérémonie corrigée) sur dev et prod. `docs/frontend-api-guide.md`
      et `docs/openapi-public.json` mis à jour en conséquence.
      **Confirmé bon à ce jour** : hero (titre volontairement divergent du
      prototype, décision utilisateur du 2026-08-03 inchangée), les 4 étapes
      de pré-inscription, tous les tableaux de tarifs/dates/pièces communes, et
      les tarifs maritimes — absents d'une version antérieure du prototype
      Figma, désormais bien présents dans la v2 et déjà couverts par
      `tuition_plans`.
      **Revu en détail** : les 3 cartes d'intro `admissions_feature`
      (Pré-inscription/Tarifs & Bourses/Modalités), la FAQ, "Conditions
      pratiques" (EPI/logement), le détail "Dossier par cycle" par
      filière/niveau, la carte "Prêt à commencer ?" et le bandeau CTA final —
      revérifiés un par un en scrollant réellement le frame Figma (pas
      seulement le texte brut) : aucun ne correspond à un élément visuel du
      prototype v2 actuel. Suite donnée juste en dessous (sanitization
      demandée explicitement par l'utilisateur, "strict is strict").
- [x] (2026-08-03) **Sanitization stricte contre le prototype Figma v2**,
      demandée explicitement par l'utilisateur ("removing all what is unused
      respecting the figma prototype" ; scope confirmé = Accueil + Admissions
      seulement ; niveau confirmé = strict 1:1, pertes de contenu réel
      acceptées en connaissance de cause après avertissement explicite).
      - **Admissions — 8 sections supprimées** (contenu + lien `pages_sections`,
        pas seulement masquées) : les 3 cartes `admissions_feature`
        (Pré-inscription id=1, Tarifs & Bourses id=2, Modalités id=3, Prêt à
        commencer id=4 — donc la collection `admissions_feature` est
        aujourd'hui vide), `admissions_richtext` id=7 (Dossier par cycle),
        id=8 (Conditions pratiques EPI/logement), id=9 (FAQ complète), et
        `admissions_cta_banner` id=1 (bandeau final — collection aujourd'hui
        vide aussi). Page passée de 19 à **11 sections**. Collections
        `admissions_feature`/`admissions_cta_banner` **conservées dans le
        schéma** (vides mais non supprimées — seul le contenu a été
        sanitizé ; suppression de collection non demandée pour celles-ci).
      - **Accueil — 2 collections supprimées du schéma** (pas seulement
        vidées) : `accueil_news_preview` et `accueil_programs_highlight` +
        sa jonction `accueil_programs_highlight_programs` — vides depuis
        leur création, jamais branchées à la page, aucun équivalent dans le
        prototype (qui met en avant les pôles, pas des programmes
        individuels). Retirées de `pages_sections.item.one_allowed_collections`
        avant suppression ; permissions publiques nettoyées automatiquement
        par Directus à la suppression (vérifié, aucun résidu).
      - **Auto-correction en cours de route** : la "cérémonie de lauréats"
        ajoutée par erreur plus haut a été retirée avant cette passe (c'était
        du texte de remplacement Figma sur les cartes Bourses, pas un contenu
        manquant — voir la correction dans l'entrée ci-dessus).
      - **Piège technique rencontré et documenté** : sur cet environnement,
        `DELETE /items/<collection>/<id>` répond `204` (succès) et une
        relecture immédiate via l'API peut encore renvoyer l'ancien contenu
        pendant un temps indéterminé (pas juste quelques secondes — un
        `sleep 5` n'a pas suffi), alors que la ligne est déjà réellement
        supprimée en base. Seule une requête Postgres directe
        (`docker exec isetag-postgres-<env> psql -U isetag -d isetag -c
        "SELECT ..."`) donne un état fiable immédiatement ; un redémarrage du
        conteneur Directus (`docker restart isetag-directus-<env>`) fait
        ensuite revenir l'API sur le même état que la base. **Pour toute
        vérification post-suppression future sur cet environnement, vérifier
        en base directement, ne jamais se fier à une lecture API immédiate.**
      Vérifié de bout en bout via l'API publique anonyme sur dev et prod
      après redémarrage des deux conteneurs Directus (page Admissions à 11
      sections, page Accueil inchangée à 8 sections, 403 sur les 2 collections
      Accueil supprimées). `scripts/provision_public_read.py` et
      `docs/frontend-api-guide.md` mis à jour en conséquence.
- [x] (2026-08-04) Accueil — collage image manquant sur le bandeau CTA final
      (`accueil_cta_banner` id=2, "Commence ton chemin aujourd'hui / Inscris-toi
      dès maintenant"). Le prototype Figma v2 montre une composition (carte
      d'identité camerounaise + 2 relevés de notes superposés + stylo, en
      arrangement pivoté/superposé), mais la collection n'avait **aucun champ
      image** — pas juste vide, absent du schéma.
      - Champ `image` ajouté (`uuid`, `special: file`, interface `file`) +
        relation FK réelle vers `directus_files` (même piège que documenté plus
        haut pour `admissions_brochure.file` : les métadonnées de champ seules
        ne suffisent pas, il faut le `POST /relations` explicite).
      - Les 4 visuels sources exacts utilisés par Figma pour ce collage ont été
        retrouvés dans `contenuç_accueil/` (`image 2.png` = carte d'identité,
        `image 3.png` + `image 4.png` = les 2 relevés de notes, `pngwing.com
        (54) 1.png` = le stylo) et composités en une seule image PNG (fond
        transparent, rotation + chevauchement reproduisant l'arrangement du
        prototype) via un script Pillow, ~786 Ko (sous le seuil 1 Mo — pas de
        conversion WebP nécessaire).
      - Uploadée dans le dossier "Public" et assignée à `accueil_cta_banner/2`
        sur dev et prod (prod via script Python exécuté directement sur le VPS,
        `cms.isetag-univ.net` n'étant pas joignable depuis l'environnement de
        dev pour l'upload multipart — voir note infra ci-dessous).
      - `scripts/provision_public_read.py` (`PUBLIC_FILE_FIELDS`) et
        `docs/frontend-api-guide.md` mis à jour ; schéma appliqué sur prod puis
        conteneur redémarré ; vérifié via lecture anonyme sur dev et prod.
      - **Note infra découverte en passant (hors périmètre de cette tâche,
        signalée mais non corrigée)** : le reverse proxy prod actuel est
        `isetag-nginx-temp` (HTTP:80 uniquement, `server_name _` catch-all,
        pas de conteneur TLS/443 publié malgré la doc qui mentionne "Nginx TLS
        pour prod"). Le domaine public reste peut-être servi en HTTPS par un
        autre chemin (proxy externe/Cloudflare) non vérifié ici ; à
        investiguer si des uploads/requêtes externes vers `cms.isetag-univ.net`
        échouent de façon inattendue.
      - **Corrigé le même jour, après retour utilisateur avec captures du
        prototype Figma v2** : deux erreurs dans la première passe.
        1. Le collage n'avait été posé que sur `accueil_cta_banner` id=2 (le
           bandeau final) — le prototype montre en fait le **même collage sur
           les deux lignes** (id=1 teaser "Admissions" inclus). Corrigé : les
           deux lignes pointent maintenant vers le même fichier.
        2. La disposition/l'agencement du premier collage ne correspondait
           pas au prototype (ordre d'empilement et échelle incorrects).
           Recomposé avec le bon ordre (arrière vers avant : relevé de notes 1
           → relevé de notes 2 → stylo → carte d'identité au premier plan,
           carte d'identité plus petite et moins chevauchante) confirmé par
           comparaison directe avec les captures fournies par l'utilisateur.
        Ancien fichier supprimé de `directus_files` sur dev et prod pour
        éviter un résidu orphelin ; nouveau fichier (~795 Ko) réuploadé et
        revérifié via lecture anonyme sur les deux lignes, dev et prod.
- [x] (2026-08-04) `accueil_cta_banner.image` — la composition recréée à la
      main ci-dessus a été **remplacée par le visuel officiel** fourni par
      l'équipe design dans `contenuç_accueil/CTA image.png`, converti en WebP
      (326 Ko → 118 Ko, conversion systématique >1 Mo appliquée même sous le
      seuil ici car demandée explicitement) et assigné aux deux lignes
      (id=1, id=2) sur dev et prod ; anciens fichiers composés supprimés de
      `directus_files` sur les deux environnements. Vérifié via lecture
      anonyme (`type: image/webp`, `filesize: 117682` identique sur les deux
      lignes, dev et prod).
      - **Vérification demandée sur les boutons des 2 bandeaux** : les 4
        champs (`button_url`/`cta2_url` sur id=1 et id=2) pointent bien vers
        des routes internes réelles et distinctes (`/admissions#pre-inscription`,
        `/admissions#modalites`, `/programmes`) — aucun champ vide ni
        placeholder. Le code frontend Angular n'est pas dans ce dépôt
        (`frontend/` est un squelette de dossiers vide, développement séparé
        par Djo) : impossible de vérifier depuis ce dépôt si le rendu final
        utilise une balise `<button type="button">` plutôt qu'un `<a>` stylé
        — à confirmer côté frontend si c'est bien ce qui était demandé.
- [x] (2026-08-04) Deux manques signalés par l'équipe éditoriale sur la page
      Admissions, section "La Scolarité / Tarifs et Frais d'Inscription" :
      1. **3 collections orphelines dans la nav Directus** —
         `admissions_brochure`, `admissions_scholarships_highlight` et
         `admissions_tuition_highlight` avaient `meta.group: null` au lieu de
         `"Admissions"`, donc invisibles dans le dossier "Admissions" du
         menu de contenu (elles existaient bien, juste mal rangées — d'où le
         signalement "je ne vois pas le bloc brochure"). Corrigé sur dev et
         prod, capturé dans le snapshot de schéma.
      2. **3 cartes "Cycle X" (BTS/Licence/Master) sans contenu Directus** —
         le prototype Figma v2 affiche, au-dessus du tableau de tarifs, une
         carte par cycle avec niveau requis, date de rentrée et mode
         d'admission ; rien de tout ça n'existait dans le schéma (probablement
         codé en dur côté frontend). Nouvelle collection autonome
         `admissions_tuition_cycles` (3 lignes, une par cycle, `level` sert de
         clé de correspondance avec `tuition_plans.level` côté frontend) ;
         **la filière Maritime n'a pas de carte dédiée dans le prototype**,
         confirmé par extraction complète du texte de la frame Figma — ses 2
         lignes de tarifs restent uniquement dans le tableau `tuition_plans`.
         Contenu repris mot pour mot du prototype (mêmes 3 champs identiques
         pour les 3 cycles : rentrée "11 septembre 2026", mode "Concours
         et/ou étude de dossier.", seul le niveau requis varie).
      Schéma appliqué sur prod, contenu inséré séparément sur dev et prod
      (non capturé par le snapshot), permissions publiques mises à jour,
      vérifié via lecture anonyme sur les deux environnements.
      - **Note à part, non corrigée (hors périmètre de cette demande)** : les
        tarifs (`tuition_plans`) distinguent déjà "Scolarité" (`total_amount`)
        et "Frais complémentaires" dans le prototype Figma, mais côté Directus
        le montant des frais complémentaires n'est pas un champ structuré —
        il est actuellement noyé dans le texte libre de `installments[0].label`
        (ex. "Inscription : 30 000 FCFA"). Pas de quoi bloquer l'affichage,
        mais si le frontend a besoin de ce montant séparément et de façon
        fiable, ça vaudra un champ dédié plus tard.
- [x] (2026-08-04) Logo Université Montplaisir Tunis (`contenu_admission/
      ADMISSION/UnivMonPlaisir.png`) ajouté à la 2e carte publiée de
      `scholarships` ("Bourse de l'Université Montplaisir Tunis", la carte
      qui accompagne "Bourse SNK" sur la page Admissions). Converti en WebP
      (89 Ko → 63 Ko, cohérent avec le format déjà utilisé sur le flyer
      "Bourse SNK").
      - **Piège rencontré : dérive d'ID entre dev et prod.** Sur dev,
        `scholarships` a 5 lignes (3 brouillons "partenariat Université
        Montplaisir Tunis" jamais publiées + 2 lignes publiées réelles,
        id=4 SNK / id=5 UMT). Sur prod, seules les 2 lignes publiées existent,
        mais avec des id différents (id=1 SNK / id=2 UMT) — les 3 brouillons
        n'ont jamais été créés côté prod. Un premier `PATCH
        /items/scholarships/5` sur prod (en copiant l'id de dev sans
        vérifier) a renvoyé un `200` avec les données du fichier uploadé en
        écho **sans rien modifier en base** (la ligne 5 n'existe pas sur
        prod) — pas d'erreur explicite, juste un no-op silencieux. Détecté en
        relisant anonymement et en obtenant `data: []`. Corrigé en ciblant le
        bon id (2) après vérification directe du contenu prod via un token
        admin. **Leçon : ne jamais supposer qu'un id de contenu (par
        opposition à un id de schéma/collection) est identique entre dev et
        prod — toujours relire la collection cible sur l'environnement visé
        avant un PATCH/DELETE par id.**
      Vérifié via lecture anonyme sur dev (id=5) et prod (id=2).
- [x] (2026-08-04) **Tentative de mise à jour Directus 11.17.4 → 12.2.0 sur
      dev, abandonnée et annulée** — investiguée pour tenter de corriger le
      bug du widget "Sections" (M2A) sur `Pages` dans l'Admin UI ("The
      relationship is not configured properly or you don't have permission to
      access it"), bug bloquant pour le personnel ISETAG non technique censé
      gérer le contenu directement via l'interface, sans script.
      - Mise à jour testée sur dev (image `directus/directus:12.2.0`,
        migrations appliquées sans erreur). Résultat : **le bug du widget
        Sections est identique sur 11.17.4 et 12.2.0** — persiste même avec
        la modale de licence fermée et un compte admin plein accès. Ce n'est
        donc pas un problème de version, la mise à jour ne le corrige pas.
      - **Régression découverte en testant** : Directus 12 sans licence
        (palier "Core" gratuit) ignore silencieusement toute permission
        comportant une condition de filtre (`{"status":{"_eq":"published"}}`,
        le filtre par dossier sur `directus_files`) — les lignes existent
        toujours en base (vérifié directement en Postgres) mais l'API les
        exclut, provoquant un `403` sur `pages`, `tuition_plans`,
        `scholarships`, `documents`, `programs` et l'accès public aux
        fichiers. Confirmé correspondre à la limitation documentée
        "custom permission rules ignored" du palier Core. Comme la mise à
        jour ne corrige pas le bug initial, **acheter une licence n'aurait
        aucun intérêt ici**.
      - **Annulé proprement** : image redescendue à `directus/directus:11`
        sur `docker/dev/docker-compose.yml`, base dev restaurée depuis une
        sauvegarde prise juste avant la tentative (`pg_dump` avant migration)
        plutôt qu'un simple retour d'image (les migrations 12.x avaient déjà
        modifié le schéma système). Contenu, les 2 Flows et l'API publique
        revérifiés identiques à l'état d'avant tentative. `IP_TRUST_PROXY:
        "true"` laissé dans `docker/dev/docker-compose.yml` (sans effet sur
        11.x, deviendra nécessaire si une mise à jour est retentée un jour —
        le défaut passe de `true` à `false` en v12, et on est derrière nginx).
      - **Solution retenue pour le personnel non technique** : le bug
        n'affecte que le widget "Sections" (réorganiser/ajouter/retirer un
        bloc sur une page) — modifier le *contenu* d'un bloc existant
        (textes, prix, images) fonctionne normalement en cliquant
        directement sur sa collection dédiée dans la barre latérale
        (ex. "Accueil Hero"), sans jamais passer par "Pages > Sections".
        C'est la quasi-totalité des mises à jour de contenu courantes.
        Les changements structurels (ajouter/retirer/réordonner un bloc)
        restent à faire via script en attendant soit un correctif amont chez
        Directus, soit la mise en place d'un accès de secours sur la
        collection `pages_sections` (actuellement masquée, champs sans
        interface) pour un usage occasionnel par quelqu'un de plus à l'aise
        techniquement — pas une solution pour le personnel le moins technique.
- [x] (2026-08-04) `admissions_tuition_cycles` — champ manquant repéré par
      l'équipe éditoriale : la liste "Pièces communes" (pièces justificatives
      à fournir) affichée sur chaque carte Cycle sur la page Admissions
      n'existait dans aucune collection. Ajouté comme `common_documents_fr/en`
      (WYSIWYG) sur `admissions_tuition_highlight` plutôt que dupliqué sur les
      3 lignes de `admissions_tuition_cycles` — texte vérifié identique mot
      pour mot sur les 3 cartes (BTS/Licence/Master) par extraction complète
      du texte de la frame Figma, donc contenu réellement partagé.
      - **Piège rencontré et corrigé** : un premier envoi du contenu via
        `curl -d` en ligne de commande a corrompu les caractères accentués
        (mojibake — `Pièces` devenu `Pi?ces`) à cause de l'encodage du shell
        Git Bash sur Windows, silencieusement stocké tel quel en base (pas
        d'erreur HTTP). Détecté en relisant le contenu via un fichier
        (`Read` direct, pas un `print()` shell qui masque le problème avec le
        même souci d'encodage de la console Windows). Corrigé en renvoyant le
        contenu via un script Python (`urllib`, payload encodé explicitement
        en UTF-8), qui contourne le shell entièrement. **Leçon : ne jamais
        passer de texte accentué en argument `curl -d` inline sur cet
        environnement Windows/Git Bash — toujours via un script Python qui
        encode explicitement en UTF-8, et vérifier via lecture de fichier,
        jamais via un `print()` terminal qui peut masquer une vraie
        corruption sous un simple problème d'affichage.**
      Corrigé et vérifié (contenu correct, lecture anonyme) sur dev et prod.
- [x] (2026-08-04) Nouvelle revue Accueil + Admissions contre le prototype
      Figma v2, deux écarts trouvés et corrigés :
      1. `admissions_tuition_highlight` et `admissions_scholarships_highlight`
         n'avaient pas de champ `eyebrow_fr/en` — le prototype affiche
         "La Scolarité" au-dessus des deux titres. Champs ajoutés, valeur
         renseignée sur les deux.
      2. `admissions_steps` (heading "Le parcours de pré-inscription") et son
         item 1 ("Choisir sa formation") ne correspondaient plus au texte
         actuel du prototype, qui affiche "Comment s'inscrire ?" avec un item
         1 "Je constitue mon dossier d'inscription" (contenu proche de
         l'ancien `admissions_richtext` id=1, probablement une réécriture).
         Heading et item 1 mis à jour mot pour mot sur le contenu visible ;
         items 2 à 4 laissés tels quels (le lecteur Figma n'a pas permis
         d'accéder aux étapes suivantes malgré plusieurs tentatives — défilement
         horizontal jusqu'aux deux bords, clic sur le badge numéroté, boutons
         "Previous/Next frame" qui naviguent en fait entre sections de la page
         et non entre étapes de ce widget — donc pas de contenu Figma pour
         confirmer ou corriger les items 2-4).
      Vérifié via lecture anonyme sur dev et prod.
- [x] (2026-08-05) **Restriction d'accès réseau à Directus prod (port 80)
      corrigée — la règle ufw ne servait à rien** — en vérifiant qui peut
      atteindre Directus prod sur le VPS (`31.207.34.25`), découverte que la
      règle ufw existante (`80/tcp ALLOW IN 102.67.200.184`, commentaire
      "temp Directus proxy for Djo+Joseph") **n'était pas réellement
      appliquée** : Docker gère son propre `iptables` indépendamment d'ufw,
      et insère pour tout port publié par un conteneur (ici `isetag-nginx-temp`
      sur `0.0.0.0:80`) une règle `ACCEPT` dans la chaîne `DOCKER` qui
      s'applique **avant** qu'ufw n'ait la main — donc port 80 était en
      réalité ouvert à tout Internet. Confirmé via les logs d'accès nginx
      montrant une IP non-listée (`160.154.233.222`, IP courante de Joseph)
      atteignant l'admin sans blocage.
      - **Correctif appliqué** : règles ajoutées directement dans la chaîne
        `DOCKER-USER` (seule chaîne que Docker ne réécrit jamais, prévue
        justement pour ce genre de restriction utilisateur) :
        `ACCEPT` pour chaque IP autorisée puis `DROP` en catch-all sur
        `tcp dport 80`. Cette chaîne est évaluée par le kernel au niveau du
        VPS, avant que le paquet n'atteigne le conteneur — c'est donc bien
        une sécurité "au portail du VPS", même si elle est invisible dans
        `ufw status`.
      - **Incident pendant la mise en place** : l'installation du paquet
        `iptables-persistent` (pour tenter de persister les règles au
        redémarrage) a silencieusement **désinstallé le paquet `ufw`**
        (conflit de dépendances), ce qui a fait basculer la policy par
        défaut de la chaîne `INPUT` de `DROP` à `ACCEPT` — VPS temporairement
        exposé sur tous les ports le temps de la correction. Détecté
        immédiatement en revérifiant `iptables -L INPUT` après l'install,
        corrigé en réinstallant `ufw` et en le réactivant (`ufw --force
        enable`), ce qui a aussi désinstallé `iptables-persistent` en retour
        (conflit dans les deux sens). **Leçon : ne jamais installer
        `iptables-persistent` sur une machine qui utilise déjà `ufw` — les
        deux se marchent dessus.**
      - **Persistance retenue (sans passer par `iptables-persistent`)** :
        script `/usr/local/sbin/docker-user-firewall.sh` sur le VPS (flush +
        réapplique les 3 règles) + unité systemd
        `docker-user-firewall.service` (`After=docker.service`,
        `RemainAfterExit=yes`, activée via `systemctl enable --now`) — ne
        touche à aucun fichier ufw, aucun conflit de paquet.
      - **Vérifier qui a accès** : `ufw status verbose` ne montre **jamais**
        cette restriction (ufw n'a aucune visibilité sur `DOCKER-USER`).
        Commande correcte :
        `iptables -L DOCKER-USER -n -v --line-numbers` (montre les IP
        autorisées + compteurs paquets/octets prouvant le filtrage actif).
      - **Mettre à jour une IP** (ex. changement de connexion) : éditer
        `/usr/local/sbin/docker-user-firewall.sh` sur le VPS (remplacer
        l'ancienne IP par la nouvelle sur la ligne `-s ...`), puis
        `systemctl restart docker-user-firewall.service`, puis vérifier avec
        la commande ci-dessus. Le SSH (port 22) reste ouvert à tous (auth par
        clé uniquement) donc aucun risque de perdre l'accès VPS pendant
        l'opération — seul l'accès à l'admin Directus est concerné.
      IP actuellement autorisées : `102.67.200.184` (Djo) et `160.154.233.222`
      (Joseph, sujette à changement — IP résidentielle/mobile dynamique).
- [x] (2026-08-05) `admissions_steps_items` id=2 mis à jour mot pour mot
      d'après une capture d'écran fournie par l'utilisateur (étape "2" du
      prototype Figma v2, non accessible via le navigateur Figma jusqu'ici) :
      `title_fr` = "Je remplis ma fiche de Pré-Inscription",
      `description_fr` = sous-titre + 4 puces combinés en texte continu
      (même convention que l'item 1 : ce champ n'est pas un WYSIWYG, pas de
      puces réelles stockées). Corrigé sur dev puis sur prod (script copié
      sur le VPS, exécuté par l'utilisateur lui-même avec le mot de passe
      admin prod — hors de mon contexte, jamais recherché ni affiché).
      Vérifié identique sur les deux environnements via lecture anonyme.
      Items 3 et 4 toujours non confirmés (captures pas encore fournies).
- [x] (2026-08-05) **Directus prod passé en HTTPS (mixed content) + CORS
      corrigé — l'équipe frontend ne pouvait plus rien charger** — rapporté
      via la console du navigateur : `Mixed Content` sur tous les
      `assets/...` et un `NetworkError` bloquant sur `/items/poles` etc.
      Cause : `https://isetag.web.app` (frontend Angular hébergé sur
      Firebase) appelait Directus en `http://31.207.34.25` — les navigateurs
      bloquent ce genre de requête active depuis une page HTTPS. Un second
      bug indépendant a été trouvé en vérifiant : `CORS_ORIGIN` sur prod ne
      contenait pas `https://isetag.web.app`, donc même après correction du
      HTTPS, ces appels auraient continué à échouer (bloqués côté navigateur
      par la policy CORS, faute d'en-tête `Access-Control-Allow-Origin`).
      - **Pas d'accès au panneau DNS LWS pour l'instant** → solution sans
        dépendre du DNS : hostname public `31-207-34-25.sslip.io` (service
        wildcard DNS public, résout automatiquement vers l'IP embarquée dans
        le nom, zéro configuration DNS nécessaire), certificat Let's Encrypt
        réel et validé par le navigateur obtenu dessus. À terme, migrer vers
        `cms.isetag-univ.net` (config déjà prête dans
        `nginx/conf.d/isetag-prod.conf`) dès l'accès au panneau LWS obtenu —
        remplacement du hostname + ré-émission du certificat uniquement, rien
        à jeter de ce qui suit.
      - **`isetag-nginx-temp` remplacé par `isetag-nginx-prod`** (nginx
        `1.27-alpine`, config dans `/opt/isetag/nginx-prod/conf.d/`) :
        sert le challenge ACME + proxy sur port 80, et un vrai bloc HTTPS
        (port 443, cert Let's Encrypt) sur `31-207-34-25.sslip.io`.
        `isetag-nginx-temp` laissé arrêté (pas supprimé) comme filet de
        sécurité.
      - **`CORS_ORIGIN` et `PUBLIC_URL` mis à jour sur `isetag-directus-prod`**
        — a nécessité de **recréer le conteneur** (pas un simple
        `docker compose up`, aucune valeur d'env ne peut être changée sur un
        conteneur déjà démarré) :
        - **Découverte importante en cours de route** : le fichier
          `docker/prod/docker-compose.yml` de ce repo n'est **pas** ce qui a
          réellement lancé le conteneur en prod (pas de `.env` dans
          `/opt/isetag/docker/prod/`, et il référence un service `frontend`
          jamais déployé). Un premier essai de `docker compose up -d
          directus` a été interrompu à temps par une erreur de validation
          (service `frontend` sans image) — sinon le conteneur aurait
          redémarré avec tous les secrets vides (mot de passe DB, clés de
          chiffrement, mot de passe admin).
        - Approche retenue à la place : script clonant la config exacte du
          conteneur actif (`docker inspect` — image, toutes les variables
          d'env, tous les points de montage, les deux réseaux Docker,
          `restart: always`) et ne changeant que la variable ciblée,
          avec renommage (pas suppression) de l'ancien conteneur comme point
          de rollback immédiat.
        - **Deux bugs shell rencontrés et corrigés pendant la mise au point**
          (repérés en mode `--dry-run`, sans toucher au conteneur réel avant
          d'être sûr) : une ligne vide dans la sortie de `docker inspect`
          provoquant un argument `-e ""` invalide, et surtout
          `IFS= read -r src dst rw` qui désactive complètement la césure par
          espace (bug classique) — corrigé en `read -r src dst rw` (sans
          `IFS=` pour cette lecture à 3 variables). Une coupure de service
          d'environ une minute a eu lieu lors du tout premier essai (avant
          les corrections), immédiatement suivie d'un rollback vers l'ancien
          conteneur puis nouvel essai après correction — chaque étape
          ultérieure a été revérifiée fonctionnelle (ping, lecture de
          contenu, connexion admin) avant de continuer.
      - **Pare-feu `DOCKER-USER` rouvert sur les ports 80 et 443** — la
        restriction Djo+Joseph mise en place plus tôt (voir entrée
        précédente) n'avait de sens que tant que Directus était en HTTP
        simple (risque d'admin en clair). Une fois le HTTPS réel en place,
        le port 443 doit rester ouvert à tous : c'est par là que **tout
        visiteur du site public** lit le contenu (`/items`, `/files`), pas
        seulement l'admin. Le port 80 doit rester ouvert en continu pour le
        renouvellement automatique du certificat (les serveurs de validation
        Let's Encrypt appellent depuis des IP arbitraires, non prévisibles).
        La protection de l'admin repose désormais sur l'authentification
        Directus elle-même (comme la quasi-totalité des déploiements Directus
        réels), plus seulement sur un filtrage réseau.
        Script `/usr/local/sbin/docker-user-firewall.sh` mis à jour en
        conséquence.
      - **Renouvellement automatique du certificat** : timer systemd
        `certbot-renew.timer` (vérification quotidienne, `certbot renew`
        + `nginx -s reload` via `/usr/local/sbin/certbot-renew.sh`) — le
        certificat expire le 2026-11-03, aucune action manuelle requise tant
        que le renouvellement automatique tourne.
      - **URL à communiquer à Djo pour le frontend** :
        `https://31-207-34-25.sslip.io` (remplace `http://31.207.34.25`
        partout dans la config du frontend). L'ancien accès HTTP simple
        reste actif en parallèle pour l'instant (transition en douceur,
        aucun consommateur existant cassé), à retirer une fois le frontend
        confirmé migré.
      Vérifié : ping, lecture de contenu, en-tête CORS correct pour l'origine
      `https://isetag.web.app`, connexion admin — tous testés en HTTPS après
      chaque changement.
- [x] (2026-08-05) **Bug critique trouvé et corrigé : le formulaire de
      pré-inscription en prod perdait silencieusement les candidatures** —
      demande explicite de vérifier toute la chaîne jusqu'à la réception de
      l'email. Test de bout en bout (upload des 3 fichiers requis + trigger
      du Flow, exactement le circuit attendu côté frontend) : la requête
      renvoie `HTTP 204` (succès) comme prévu, **mais les logs Directus
      révèlent que l'envoi d'email échoue silencieusement** :
      `Email connection failed: connect ECONNREFUSED 127.0.0.1:587`.
      `EMAIL_SMTP_HOST`/`EMAIL_SMTP_USER` étaient vides sur prod — jamais
      renseignés depuis le déploiement initial du 2026-07-30. Le Flow ne
      renvoyant volontairement aucune confirmation détaillée (design
      RGPD-friendly voir plus haut), l'échec est **invisible côté frontend
      ET côté visiteur** : une vraie candidature aurait été enregistrée en
      base (l'opération de création s'exécute avant l'opération d'email) mais
      **le service des admissions n'aurait jamais été notifié**.
      - **Corrigé en 2 temps**, chaque fois via le même script de recréation
        de conteneur que pour `CORS_ORIGIN`/`PUBLIC_URL` (clone de la config
        exacte + une seule variable modifiée, ancien conteneur renommé comme
        point de rollback) :
        1. `EMAIL_SMTP_HOST/PORT/USER/PASSWORD/FROM` alignés sur les
           identifiants Gmail personnels déjà utilisés en dev (mesure
           provisoire assumée, à remplacer par de vrais identifiants SMTP
           institutionnels dès qu'ils seront fournis — même logique que le
           certificat `sslip.io` : débloquer maintenant, migrer proprement
           plus tard). Le mot de passe applicatif Gmail n'a **jamais transité
           par moi** : extrait du conteneur dev directement par
           l'utilisateur dans son propre terminal PowerShell et injecté dans
           l'appel SSH côté VPS.
        2. `ADMISSIONS_EMAIL` (`admissions@isetag-univ.net`, une adresse à
           laquelle personne n'a accès pour l'instant) changé vers
           `djopiano@gmail.com` pour permettre une vérification réelle de
           réception — **à remplacer par la vraie adresse institutionnelle
           du service des admissions** une fois disponible.
      - **Vérifié de bout en bout, deux fois** (avant/après chaque fix) :
        upload des 3 fichiers placeholder → trigger du Flow → absence
        d'erreur dans les logs Directus → **email effectivement reçu et
        confirmé par l'utilisateur** sur `djopiano@gmail.com`.
      - **Données de test laissées dans `admission_applications`** (2 lignes
        "TEST-AUTOMATISE / NePasTraiter" + 6 fichiers placeholder liés) — à
        supprimer manuellement via l'admin (`/admin/content/admission_applications`),
        le rôle Public n'ayant pas de droit de lecture/suppression dessus.
      **Reste à faire** : remplacer les identifiants SMTP Gmail temporaires
      par les identifiants institutionnels définitifs, et `ADMISSIONS_EMAIL`
      par la vraie adresse du service des admissions, dès qu'ils seront
      fournis (mécanisme de remplacement déjà en place, changement trivial).
- [x] (2026-08-10) **Nouvelle mise à jour du prototype Figma (Accueil +
      Admissions uniquement, périmètre confirmé par l'utilisateur) — revue
      complète et synchronisation Directus**, en plusieurs passes après que
      deux écarts aient d'abord été manqués lors d'une première revue
      superficielle (carte "Cycle Maritime" ajoutée, carte "Bourse SNK"
      retirée) et signalés directement par l'utilisateur. Reprise systématique
      en confrontant le contenu réellement stocké (lecture API, pas seulement
      le souvenir des entrées précédentes) au prototype scrollé image par
      image, à deux largeurs de viewport différentes pour éviter de manquer
      une colonne coupée à l'écran. Cinq écarts confirmés et corrigés,
      appliqués sur dev puis sur prod avec le même script Python idempotent
      (login admin, une fonction par écart, vérifiable/rejouable
      indépendamment) :
      1. **Ajout — carte "Cycle Maritime"** dans `admissions_tuition_cycles`
         (4e ligne, `level: "Maritime"` — même clé que les lignes maritimes
         déjà existantes dans `tuition_plans`, id 9-10, pour que la
         correspondance frontend continue de fonctionner sans changement).
         Contenu identique aux 3 autres cartes (rentrée "11 septembre 2026",
         mode "Concours et/ou étude de dossier.", même niveau requis affiché
         par Figma sur les 4 cartes — voir note plus bas).
      2. **Retrait — carte "Bourse SNK"** : ligne `scholarships` id=4 (dev) /
         id=1 (prod) passée de `status: published` à `status: draft` —
         **désactivée, pas supprimée**, récupérable en un `PATCH` si le
         partenariat revient. Seule la carte "Bourse de l'Université
         Montplaisir Tunis" reste publique.
      3. **Correction de titre** — `admissions_tuition_highlight.heading_fr`
         changé de "Tarifs et Frais d'Inscription" à "Nos différents Cycles",
         qui est le texte affiché par le prototype actuel pour cette section.
         Indice qui a mené à l'écart suivant : le titre stocké parlait encore
         de tarifs alors qu'aucun montant ne s'affiche plus nulle part sur
         ou autour des cartes Cycle dans le prototype.
      4. **Retrait — 6 blocs `admissions_richtext`** (calendrier "Repères
         2026-2027", liste exhaustive des filières par cycle, paragraphe
         "Tarifs & Bourses 2026-2027", bloc "Bourses, aides et facilités" en
         doublon avec `admissions_scholarships_highlight`, tableau "Modalités
         d'admission" avec pièces communes) — après relecture attentive et
         répétée du prototype du début à la fin, aucun de ces six blocs ne
         correspond plus à un élément visible : la page a été simplifiée à
         hero+étapes → bannière brochure → cartes Cycle sans tarif → une
         seule carte Bourse → footer. Les 6 liens `pages_sections`
         (`admissions_richtext`, sorts 2/4/5/7/8/11) et les 6 lignes de
         contenu correspondantes ont été supprimés (collection
         `admissions_richtext` conservée dans le schéma, vide — même
         convention que `admissions_feature`/`admissions_cta_banner` depuis
         la sanitization du 2026-08-03). **C'est le changement le plus
         important en volume de contenu réel retiré** (dates d'inscription,
         montants, listes de filières) — confirmation explicite demandée et
         obtenue avant exécution, contrairement aux 4 autres points qui
         suivaient un écart déjà bien identifié.
      5. **Ajout — nouvelle section Accueil "Bienvenue à l'ISETAG / Le mot du
         promoteur"**, absente de tout schéma ou contenu existant (recherche
         du texte et de "promoteur"/"PAMEN" dans tout ce fichier :
         aucune occurrence avant cette entrée). Nouvelle collection
         `accueil_promoter_message` créée (`heading_fr/en`, `subheading_fr/en`,
         `body_fr/en` en WYSIWYG, `author`), ajoutée à
         `pages_sections.item.one_allowed_collections` (relation M2A),
         permission de lecture publique créée, contenu français inséré
         (essai retranscrit du prototype, signé "Pasteur PAMEN FLAUBERT") —
         **`_en` laissés vides**, structure prête, traduction à fournir.
         Section insérée dans `pages_sections` de la page Accueil à `sort=4`
         (entre la bannière CTA admissions et "5 Raisons de choisir
         ISETAG", position exacte du prototype), les sections suivantes
         décalées de +1 (`accueil_reasons` 4→5, `accueil_partners_highlight`
         5→6, `accueil_testimonials_highlight` 6→7,
         `accueil_vie_campus_teaser` 7→8, 2e `accueil_cta_banner` 8→9).
      - **Note non corrigée, signalée mais volontairement laissée telle
        quelle** : le prototype affiche le même "Baccalauréat, GCE Advanced
        Level ou équivalent" comme niveau requis sur les 4 cartes Cycle
        (BTS/Licence/Master/Maritime), alors que Directus a des valeurs
        correctement différenciées par cycle (Licence exige BTS/DUT/HND,
        Master exige une Licence) — probable artefact de duplication de
        composant côté Figma plutôt qu'un changement voulu ; les valeurs
        Directus, plus exactes, n'ont pas été alignées sur ce texte.
      - **Gestion des identifiants admin prod** : script exécuté localement
        contre `https://31-207-34-25.sslip.io`, credentials lus depuis un
        fichier `.env.prod` temporaire (hors dépôt, dans le répertoire de
        travail temporaire de la session) que l'utilisateur a rempli
        lui-même après extraction directe depuis les variables d'environnement
        du conteneur prod en cours d'exécution (`docker exec
        isetag-directus-prod env`) via sa propre session SSH — mot de passe
        jamais tapé ni affiché dans mon contexte. Fichier supprimé après
        usage. **Piège rencontré** : `Set-Content -Encoding utf8` de
        PowerShell écrit un BOM UTF-8 en tête de fichier, ce qui empêchait la
        toute première clé (`DIRECTUS_ADMIN_EMAIL`) d'être reconnue par un
        parseur `utf-8` strict côté script (`grep`/Python) — corrigé en
        lisant le fichier en `utf-8-sig` plutôt qu'en renvoyant l'utilisateur
        régénérer le fichier.
      Vérifié : lecture anonyme complète sur dev puis sur prod pour chacun
      des 5 points (contenu, encodage des accents, ordre des sections),
      script rejoué sans effet de bord une fois les changements déjà en
      place (idempotent).
- [x] (2026-08-13) **Descripteurs de champs du formulaire d'admission — endpoint
      dédié `/admission-fields-descriptor`.** Le front recopiait à la main les
      listes de choix (sexe, dernier_diplome, cycle, domaine, regime — 6 champs,
      ~30 valeurs) depuis un export ponctuel du schéma livré le 27/07 : tout
      ajout/retrait d'une valeur ou d'un champ dans Directus restait invisible
      côté front — même défaut que la copie figée des cycles de formation
      (2026-08-03).
      - **Pistes essayées et rejetées, dans l'ordre, chacune vérifiée en direct
        (pas supposée)** :
        1. Opération de Flow `item-read` sur `directus_fields` — bloqué en dur :
           `/items/directus_fields` renvoie 403 même pour un token admin complet
           (les collections système ne passent jamais par la route générique
           `/items/*`, permissions ou pas).
        2. Permission `read` sur `directus_fields` filtrée à
           `collection={_eq: admission_applications}`, accordée à un rôle de
           service dédié — inutile : le test a montré que l'autorisation de
           `/fields/:collection` ne regarde jamais `directus_fields` mais exige
           un `read` sur la collection **cible** elle-même
           (`admission_applications` a seulement `create` côté Public → 403 ;
           `programs` a `read` → 200, vérifié sur les deux).
        3. Auto-appel du Flow vers `http://localhost:8055/fields/...` — bloqué
           par la protection SSRF native de Directus (`localhost` toujours
           refusé par défaut pour les opérations `request`, quel que soit
           `IMPORT_IP_DENYLIST`, non modifié pour ne pas affaiblir cette
           protection pour tous les Flows de l'instance).
        4. `read` + `fields: []` sur `admission_applications` (permission
           présente mais aucune colonne exposée, pour passer la porte du
           point 2 sans risque a priori) — la réponse de
           `/fields/admission_applications` s'est retrouvée vide
           (`"data": []`) : Directus lie strictement la visibilité de
           `/fields/:collection` à la liste `fields` de la permission `read`
           sur les données elles-mêmes. Conclusion : **aucune permission,
           aussi étroite soit-elle, ne peut exposer les descripteurs sans
           exposer les mêmes champs de données réelles** via ce même octroi.
        5. Spec OpenAPI publique (`/server/specs/oas`) — `admission_applications`
           totalement absente malgré le `create` de Public, confirmant la même
           règle une 3e fois.
      - **Solution retenue : extension Directus "endpoint"**
        (`cms/extensions/admission-fields-descriptor/`), qui lit le schéma
        directement en mémoire process (`FieldsService`, `accountability: null`)
        au lieu de repasser par une route soumise aux permissions — aucune
        permission touchée, aucun compte de service. Portée figée dans le code
        (`COLLECTION = "admission_applications"`, champs de gestion exclus en
        dur : `status`, `source`, `annee_academique`, `desired_program`, plus
        tout champ `meta.hidden=true`) — jamais dérivée d'un paramètre de
        requête. Structure Directus 11 (nesting par type déprécié depuis la
        10.3, supprimé en 11.0) : `extensions/<nom>/package.json` +
        `extensions/<nom>/dist/index.js`, à plat.
      - **Réponse** : `GET /admission-fields-descriptor` (public, sans auth) →
        `{"data": [{field, type, interface, required, sort, note, choices}, ...]}`,
        30 champs, triés par `sort`.
      - **Déploiement prod — découverte en cours de route** : le workflow
        `.github/workflows/deploy.yml` suppose un checkout git à `~/isetag` sur
        le VPS ; en réalité `/opt/isetag` (chemin confirmé via
        `docker inspect isetag-directus-prod --format '{{range .Mounts}}...'`)
        **n'est pas un dépôt git du tout** (`git pull` → "not a git
        repository") — le déploiement automatique CI/CD ne fonctionnerait donc
        pas tel que configuré pour ce VPS. Contournement pour ce changement :
        `scp -r` direct du dossier de l'extension vers
        `/opt/isetag/cms/extensions/`, puis `docker restart
        isetag-directus-prod` (pas de `schema apply` ni de script de
        provisioning nécessaire — aucun changement de schéma/permissions).
        **Sujet à reprendre séparément** : soit cloner un vrai dépôt git dans
        `/opt/isetag`, soit corriger le chemin dans `deploy.yml`.
      - **Ancien brouillon abandonné et nettoyé sur dev** : rôle/policy/
        utilisateur "Introspection Formulaire (interne)" et le Flow
        correspondant (pistes 2-3 ci-dessus), tous supprimés une fois
        l'approche par extension confirmée fonctionnelle.
      Vérifié : lecture anonyme sur dev puis sur prod (30 champs, choix
      identiques, encodage des accents correct en octets UTF-8 — pas seulement
      à l'écran), `status`/`source`/`annee_academique`/`desired_program`/`id`
      absents des deux, `/items/admission_applications` et
      `/fields/admission_applications` toujours 403 sur prod après déploiement
      (aucune régression sur la fermeture d'accès aux candidatures).
- [x] (2026-08-13) **Fix du checkout git de `/opt/isetag` sur le VPS prod.**
      Découvert en déployant `admission-fields-descriptor` (entrée ci-dessus) :
      `/opt/isetag` (chemin réel, confirmé via `docker inspect
      isetag-directus-prod --format '{{range .Mounts}}...'`) n'était **pas un
      dépôt git** (`git pull` → "not a git repository"), alors que
      `.github/workflows/deploy.yml` suppose `~/isetag`. Avant de remplacer le
      dossier, comparaison complète du contenu réel du VPS (tar récupéré via
      `scp`, jamais collé en clair) contre `main` pour ne rien perdre :
      - **Corrections faites en direct sur le VPS, jamais commitées, rapatriées
        dans le dépôt** :
        - `nginx-prod/conf.d/directus.conf` — la config nginx **réellement
          active** (conteneur `isetag-nginx-prod`, démarré manuellement, hors
          compose) : HTTPS réel sur `31-207-34-25.sslip.io` avec vrais certs
          Let's Encrypt, mise en place le 2026-08-05 (voir entrée "Directus
          prod passé en HTTPS") mais jamais versionnée.
        - `nginx-temp/default.conf` — l'ancien stopgap HTTP-only
          (`isetag-nginx-temp`, arrêté mais conservé comme filet de sécurité).
        - `docker/prod/docker-compose.yml` — `CORS_ORIGIN` sur le fichier VPS
          listait déjà `isetag.web.app` et l'origine sslip.io en plus de ce
          que git avait (version pré-HTTPS, avec un commentaire "TEMP"
          obsolète) ; retenu comme source de vérité unique et copié dans git,
          commentaire "TEMP" retiré (HTTPS/nginx est maintenant la vraie
          entrée). `container_name` du service `nginx` corrigé `isetag-nginx`
          → `isetag-nginx-prod` pour matcher ce qui tourne vraiment ;
          commentaire ajouté précisant que ce service compose reste la cible
          **future** (once DNS basculé vers `nginx/conf.d/isetag-prod.conf`),
          pas ce qui sert aujourd'hui.
      - **Fausse alerte corrigée en cours de route** : un premier diagnostic
        (`docker inspect ... | tr ',' '\n' | grep CORS`) avait semblé montrer
        un 3e `CORS_ORIGIN` divergent sur le conteneur réellement en cours
        d'exécution (`https://isetag-univ.net` seul). C'était un artefact de
        la commande elle-même : `tr ','` coupait aussi les virgules
        *à l'intérieur* de la valeur `CORS_ORIGIN` (qui est une liste
        séparée par virgules), et `grep` ne gardait que le premier fragment.
        Un nouveau relevé propre (`{{range .Config.Env}}{{println .}}...`,
        un env var par ligne) a montré que le conteneur avait déjà la liste
        complète — donc seulement 2 sources en désaccord (fichier VPS vs
        git), pas 3, et aucune recréation de conteneur n'a été nécessaire.
      - **Fichiers simplement obsolètes côté VPS (git plus à jour, écrasement
        sans risque)** : `scripts/deploy.sh` (antérieur à l'ajout de
        `provision_roles.py` au pipeline), `scripts/provision_public_read.py`
        (antérieur à la refonte Accueil — référençait encore
        `accueil_news_preview`/`accueil_programs_highlight`, des collections
        depuis remplacées). `cms/snapshots/current.yaml` et le reste de
        `nginx/` déjà identiques, aucun écart.
      - **`deploy.yml` corrigé** : `cd ~/isetag` → `cd /opt/isetag`.
      - **`.gitignore`** : ajout de `/certbot/` (certs + clés privées réelles
        pour `31-207-34-25.sslip.io`, ne doivent jamais être commités).
      - **Échange du dossier, sans interruption de service** : ancien
        `/opt/isetag` renommé en `/opt/isetag.bak` (filet de sécurité, pas
        supprimé), `git clone` frais à sa place, puis recopie de
        `.env.prod` + `cms/uploads/` (115 Mo de fichiers réels, RGPD) +
        `certbot/` (certs + clés privées) depuis `.bak` — vérifié identique
        par `diff -rq` avant et après. Aucun conteneur redémarré (leurs bind
        mounts pointent sur des chemins absolus `/opt/isetag/...` déjà figés
        à leur création — repeupler le même chemin ne les perturbe pas) :
        `isetag-directus-prod`/`isetag-nginx-prod`/`isetag-postgres-prod`
        sont restés `Up` sans interruption tout du long. `git pull` fonctionne
        désormais proprement depuis `/opt/isetag`.
      Vérifié après coup : site + `/admission-fields-descriptor` +
      `/items/pages` toujours 200 en HTTPS, `git status` propre à
      `/opt/isetag`, `.env.prod` restauré avec permissions `600`.
- [x] (2026-08-13) **`tuition_plans` dépublié (10 lignes, dev + prod).**
      Question posée en parcourant l'admin Directus : cette collection avec
      les tarifs (montants, échéanciers) a-t-elle encore une utilité alors
      qu'`admissions_tuition_cycles` + `admissions_tuition_highlight`
      couvrent déjà le nouveau format à 4 cartes ? Vérification directe sur
      le prototype Figma à jour (node-id=4182-950) : chaque carte de cycle
      (BTS, Licence, Master, Maritime) affiche seulement Rentrée, Niveau
      requis, Mode d'admission, Pièces communes — aucun tarif, aucun
      échéancier, nulle part entre les cartes et la section "Bourses, Aides
      et facilités" qui suit. Retrait confirmé, même famille que la carte
      Bourse SNK et les 6 blocs richtext retirés le 2026-08-10 — la donnée
      existait toujours mais la maquette ne l'affiche plus. Dépublication
      (`status` → `draft`, pas de suppression, réversible) plutôt que
      suppression pour rester cohérent avec le traitement de Bourse SNK.
      Vérifié : `/items/tuition_plans` renvoie `200` avec `0` ligne en lecture
      anonyme sur dev et prod (la collection reste lisible, filtrée à
      `status=published`), `/items/admissions_tuition_cycles` inchangé.
- [x] (2026-08-13) **`accueil_testimonials_highlight` repensé en carrousel
      d'actualités (dev + prod).** Question
      posée en parcourant l'admin : "la section Alumni a une nouvelle image
      de fond, le texte a peut-être changé aussi". Vérification sur le
      prototype Figma à jour : la section n'a pas juste un nouveau fond,
      **son contenu a changé de nature** — l'ancien "Les Alumnis de ISETAG"
      (témoignages d'anciens étudiants) est devenu "Actualités de ISETAG"
      (carrousel d'actualités réelles, ex. "Immersion professionnelle chez
      GAP Motors", visite d'étudiants MAVA/MKA chez ce partenaire en février
      2026).
      - Collection **conservée** (`accueil_testimonials_highlight`, pour ne
        pas casser la clé `sections.item:accueil_testimonials_highlight.*`
        déjà documentée côté front) mais repurposée : `eyebrow_fr` → "Actualités
        de ISETAG", `cta_label_fr` → "Découvrez nos actualités", `cta_url` →
        `/actualites` (au lieu de `/actualites#success-stories`, ancre
        obsolète), `heading_fr/en` → `null` (le titre affiché vient
        désormais de chaque actualité, pas d'un heading statique du bloc).
      - Ancienne relation `testimonials` (champ alias + jonction
        `accueil_testimonials_highlight_testimonials`) **supprimée** — plus
        utilisée par ce bloc. La collection `testimonials` elle-même et
        `actualites_testimonials_highlight` (page Actualités, distincte) ne
        sont pas affectées.
      - Nouvelle relation M2M **`news`** créée (jonction
        `accueil_testimonials_highlight_news`, même mécanique que `partners`
        sur `accueil_partners_highlight`) — sélection manuelle et ordonnée
        (`sort`) d'actualités à mettre en avant, plutôt que les N dernières
        automatiquement, pour rester cohérent avec le reste du page-builder.
      - Première actualité créée dans la collection `news` (jusque-là vide,
        0 ligne) : slug `immersion-professionnelle-gap-motors`, `category`
        = `vie_campus` (le plus proche des 5 choix existants — à ajuster si
        l'équipe éditoriale préfère `partenariat`, GAP Motors étant
        l'entreprise hôte), `date_published` = 2026-02-01 (le prototype dit
        seulement "en février 2026", jour exact non précisé), image fournie
        par l'utilisateur (`contenuç_accueil/alumni_image.png`, 697 Ko —
        sous le seuil de 1 Mo, conservée en PNG sans conversion WebP) uploadée
        dans le dossier Public.
      - **Piège rencontré** : le cache Directus (`CACHE_ENABLED=true` en dev)
        a fait rater la vérification d'idempotence de la création `news` au
        premier re-run après un bug corrigé en cours de route (mauvais point
        de terminaison `/fields` au lieu de `/fields/:collection` pour créer
        les champs de la jonction) — une ligne `news` dupliquée créée puis
        supprimée manuellement après coup.
      Vérifié en lecture anonyme sur dev et prod : carrousel renvoie bien
      l'actualité GAP Motors avec accents corrects, `heading_fr` vide comme
      prévu, ancienne jonction `testimonials` bien absente,
      `/items/accueil_testimonials_highlight_testimonials` renvoie `403`
      (collection supprimée). Script prod exécuté sans accroc au premier
      passage (bug `/fields` déjà corrigé) ; seul `cta_url` avait été fixé à
      la main sur dev après coup sans être reporté dans le script — rattrapé
      séparément sur prod par un second passage de credentials.
- [x] (2026-08-13) **`admissions_scholarships_highlight.intro_text_fr/en`
      ajouté (dev + prod).** Signalé via capture d'écran : un paragraphe sous
      le titre "Bourses, aides et facilités" ("Des avantages ou bourses
      peuvent être proposés dans le cadre de partenariats académiques et de
      campagnes spécifiques.") n'existait pas encore dans Directus — la
      collection n'avait jusqu'ici que `heading_fr/en` + `eyebrow_fr/en`
      (voir entrée admissions_tuition_highlight/scholarships du 2026-08-03).
      **Correction en cours de route** : première lecture avait fait
      confondre ce paragraphe de section avec le texte plus long de la carte
      "Bourse de l'Université Montplaisir Tunis" (`scholarships.description`,
      id=5 en dev / id=2 en prod) — modifié par erreur puis **immédiatement
      annulé** sur dev avant tout déploiement prod, sur indication explicite
      de l'utilisateur ("il n'y a rien à modifier là"). `scholarships.description`
      n'a donc subi aucun changement net, sur aucun environnement.
      Champs ajoutés : `intro_text_fr/en` (type `text`, interface
      `input-multiline`, même pattern que `accueil_partners_highlight.intro_text_fr`).
      Vérifié : lecture anonyme correcte sur dev et prod (accents corrects en
      octets UTF-8), `scholarships` (id=2 prod, published) inchangé.
- [ ] Front à adapter pour le nouveau circuit de soumission du formulaire de
      pré-inscription (upload des fichiers un par un avec id généré côté client, puis
      un seul POST JSON vers le Flow) — voir section dédiée ci-dessus
- [ ] Composants Angular (Home, Formations, Admissions) — hors périmètre, pris en charge par un autre développeur
