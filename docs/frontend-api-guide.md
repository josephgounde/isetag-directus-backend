# Guide API pour l'équipe frontend (Angular 18 SSR)

Ce document est le point d'entrée pour construire les pages du site à partir de
Directus. Ne pas utiliser `cms/snapshots/current.yaml` — c'est un format
interne de schéma-as-code pour Directus lui-même, pas un contrat d'API.

## Base URL & authentification

| Environnement | URL |
|---|---|
| Dev (local) | `http://localhost:8055` |
| Staging | `https://cms-staging.isetag-univ.net` |
| Prod | `https://cms.isetag-univ.net` |

**Aucune authentification requise pour la lecture du contenu public** (rôle
Public, lecture seule, contenu publié uniquement). REST (`/items/<collection>`)
et GraphQL (`/graphql`) sont tous les deux disponibles ; REST suffit pour la
plupart des besoins.

## Spec OpenAPI — source de vérité

Directus génère une spec OpenAPI 3 **en direct**, reflétant exactement le
schéma actuel ET ce que le rôle courant (ici : Public, anonyme) a le droit de
voir :

```
GET {BASE_URL}/server/specs/oas
```

Une copie est versionnée dans [`docs/openapi-public.json`](openapi-public.json)
pour référence hors-ligne, mais **préférez toujours l'URL live** — elle change
si le schéma évolue, le fichier versionné peut devenir obsolète. Importable
directement dans Swagger UI / Postman / Insomnia, ou pour générer un client
TypeScript typé (`openapi-typescript`, `orval`, etc.), ce qui est recommandé
pour un projet Angular.

Notez que `admission_applications` n'apparaît **volontairement pas** dans cette
spec anonyme : ces données sont RGPD-sensibles et jamais lisibles publiquement
(voir plus bas, section Admissions).

## Images et fichiers

Construire l'URL directement :

```
{BASE_URL}/assets/<uuid-du-fichier>
```

Où `<uuid-du-fichier>` est la valeur du champ (`cover_image`, `logo`, `photo`,
`file`, etc.) retournée par l'item. Transformations à la volée disponibles via
query params (`?width=800&format=webp`, etc.) — utile pour respecter la
contrainte LCP < 2s / réseau mobile parfois lent mentionnée dans le brief.

Seuls les fichiers rangés dans le dossier Directus **"Public"** sont
accessibles anonymement (allowlist volontaire, voir `scripts/provision_public_read.py`) :
tout fichier illustrant du contenu public (couvertures d'actus, logos
partenaires, photos témoignages, documents téléchargeables) doit être
uploadé dans ce dossier — c'est déjà le comportement par défaut de l'interface
d'upload pour ces champs-là.

## Bilinguisme FR/EN

Chaque champ éditorial existe en deux colonnes (`title_fr`/`title_en`,
`heading_fr`/`heading_en`, etc.) sur la même ligne — pas de lignes traduites
séparées. Les deux valeurs reviennent dans un seul appel API ; changer de
langue côté frontend est un simple re-rendu (relire `_en` au lieu de `_fr`),
sans nouvelle requête.

**Pas de fallback vers le français si `_en` est vide** — décision produit :
un champ `_en` non rempli s'affiche vide en version anglaise. Ce n'est pas une
protection technique contre du contenu manquant : si l'équipe communication
oublie de traduire un champ, le site anglais aura un trou visible à cet
endroit. À l'équipe communication/admissions de veiller à remplir les deux
langues avant de publier.

## Correspondance pages Figma / sitemap ↔ collections

**Important** : cette table a été corrigée après revue directe du prototype
Figma (nav réelle = Accueil, Programmes, Admissions, Vie Campus, Actualités
[anciennement labellisée "Ressources" dans la nav — renommage en cours],
Contact). Elle ne suit plus l'ancien "sitemap verrouillé à 7 routes" — cette
mention est obsolète, à ne plus utiliser comme référence.

| Page | Collection(s) | Notes |
|---|---|---|
| Accueil | `pages` (`key=accueil`) → sections | Page composée de sections éditoriales ordonnées. Le contenu "À propos" (accroche "Choisir l'ISETAG") est intégré dans le hero de cette page, pas une page séparée. |
| Programmes | `pages` (`key=programmes`) → sections, + `poles`, `programs` | Sections éditoriales en tête de page (ex. mise en avant d'un pôle) + un bandeau CTA ("Commence ton chemin aujourd'hui", `programmes_cta_banner` — à créer) en fin de page, puis catalogue filtrable en listing direct. Filtrer `programs` par `pole`, `schedule`, `is_hnd` (`filter[pole][_eq]=...`). |
| Fiche filière | `programs` (par `slug`), `testimonials` (filtrées par `program`) | Pas de page-builder — page 1:1 avec un `programs`. |
| Admissions | `pages` (`key=admissions`) → sections, + `tuition_plans`, `scholarships`, `documents` (`filter[category][_eq]=admission`) | Sections éditoriales (dont le guide "Comment s'inscrire" en étapes numérotées), tarifs/bourses/documents en listing direct. Le formulaire de pré-inscription est un cas à part, voir section dédiée ci-dessous — **pas un simple GET**. |
| Vie Campus | `pages` (`key=vie_campus`) → sections, + `campus_services` | Sections éditoriales (hero, mise en avant), puis listing `campus_services` (filtrer par `display_section` si plusieurs zones). |
| Actualités *(nav "Ressources" → renommée)* | `pages` (`key=actualites`) → sections, + `news`, `documents` | Une seule page qui contient : une section "Success Stories" (témoignages curatés, `actualites_testimonials_highlight` — déjà créée, vide), une section actualités (`news`, triée par `date_published`), une section "ressources" (`actualites_documents_list` — déjà créée, vide, bibliothèque de documents à télécharger, filtrable par `category`), et un bandeau CTA (`actualites_cta_banner` — à créer, même contenu éditorial que celui de la page Programmes mais sa propre collection). |
| Contact | `pages` (`key=contact`) → sections | Hero éditorial + formulaire de contact. Le formulaire est un cas à part, voir section dédiée ci-dessous — **pas un simple GET**. |

## Pages composées de sections (page-builder)

Accueil, Programmes, Admissions, Vie Campus, Actualités et Contact ne sont pas
de simples listings : un éditeur compose chaque page à partir de sections
ordonnées (page-builder, modèle many-to-any Directus).

**Chaque page a ses propres collections de blocs** — ex. `admissions_hero` et
`accueil_hero` sont deux collections distinctes, chacune propriétaire du
contenu de sa page. Il n'y a plus de collection `block_*` générique partagée
entre plusieurs pages (voir `ISETAG_project_instructions.md`, section
"Organisation en pages/sections", pour le contexte de ce choix). Convention de
nommage : `<page_key>_<type_de_bloc>` (`admissions_hero`, `admissions_richtext`,
`accueil_news_preview`, `actualites_documents_list`, ...).

Tout se récupère en **un seul appel** grâce au deep-fetch, en listant les
collections propres à la page demandée dans `sections.item:<collection>.*` :

```
GET {BASE_URL}/items/pages?filter[key][_eq]=admissions&fields=*,sections.collection,sections.sort,sections.item:admissions_hero.*,sections.item:admissions_richtext.*,sections.item:admissions_feature.*,sections.item:admissions_steps.items.*,sections.item:admissions_cta_banner.*
```

Exemple pour Accueil (noter le `.partners.partners_id.*` et
`.testimonials.testimonials_id.*` pour traverser les jonctions M2M jusqu'aux
données réelles) :

```
GET {BASE_URL}/items/pages?filter[key][_eq]=accueil&fields=*,sections.collection,sections.sort,sections.item:accueil_hero.*,sections.item:accueil_poles_highlight.*,sections.item:accueil_reasons.heading_fr,sections.item:accueil_reasons.heading_en,sections.item:accueil_reasons.items.*,sections.item:accueil_cta_banner.*,sections.item:accueil_partners_highlight.heading_fr,sections.item:accueil_partners_highlight.intro_text_fr,sections.item:accueil_partners_highlight.partners.partners_id.*,sections.item:accueil_testimonials_highlight.heading_fr,sections.item:accueil_testimonials_highlight.testimonials.testimonials_id.*,sections.item:accueil_vie_campus_teaser.*,sections.item:accueil_vie_campus_teaser.gallery.image,sections.item:accueil_vie_campus_teaser.gallery.sort
```

La réponse contient `sections` = liste ordonnée (`sort`) d'objets
`{collection, item}` — `collection` indique la collection de bloc (donc
implicitement la page et le type) et `item` contient les champs du bloc
correspondant. Le frontend fait un `switch` sur `collection` pour choisir le
composant Angular à rendre pour chaque section.

Types de blocs actuellement en usage — **Admissions** et **Accueil** ont du
contenu réel à ce jour :

- **`admissions_hero`** — title_fr/en, subtitle_fr/en, image, cta_label_fr/en, cta_url
- **`admissions_feature`** — image + heading_fr/en + body_fr/en (WYSIWYG) +
  tag_label_fr/en optionnel (petit label/pill) + cta_label_fr/en + cta_url
  optionnels. Sert pour une mise en avant de filière, une modalité, etc.
- **`admissions_steps`** — heading_fr/en + `items` (O2M ordonné par `sort` :
  title_fr/en, description_fr/en) — guide en étapes numérotées ("Comment
  s'inscrire")
- **`admissions_richtext`** — content_fr/en (WYSIWYG, texte libre) + `image`
  optionnelle (illustration du bloc — ne jamais faire porter une URL d'image
  par le HTML du WYSIWYG lui-même : ça fige l'environnement, un champ fichier
  dédié laisse le frontend construire l'URL avec le bon `BASE_URL`)
- **`admissions_cta_banner`** — heading_fr/en, text_fr/en, button_label_fr/en, button_url
- **`accueil_hero`** — title_fr/en, subtitle_fr/en, image, **deux** CTA
  (`cta1_label_fr/en`/`cta1_url`, `cta2_label_fr/en`/`cta2_url` — la page
  Accueil a deux boutons hero, contrairement à Admissions qui n'en a qu'un).
  Copie mise à jour 2026-08-03 pour coller au texte réel du prototype Figma v2
  (`title_fr` = "Choisir l'ISETAG", `subtitle_fr` = "C'est s'offrir une
  profession", `cta1` = "Je me pré-inscris" → `/admissions#pre-inscription`,
  `cta2` = "Découvrir nos Programmes" → `/programmes`) — remplace l'ancienne
  copie plus longue rédigée avant que l'équipe design finalise le texte
  on-page ; `image` inchangée (déjà la bonne photo du portail/cour campus)
- **`accueil_poles_highlight`** — heading_fr/en uniquement (heading_fr =
  "Choisis le pôle qui te valorise", repris du prototype Figma — absent du
  document éditorial d'origine) ; le carrousel de pôles lui-même vient
  directement de la collection partagée `poles` (tous les pôles sont
  affichés, triés par `display_order` — pas de sélection curatée donc pas de
  jonction M2M ici). Chaque carte pôle affiche en plus la liste de ses
  `programs` (filtrer `programs?filter[pole][_eq]=<id>` — les libellés courts
  du prototype ne correspondent pas toujours exactement à `name_fr`, à
  vérifier avec l'équipe design/contenu). `poles.description_fr` (déjà
  existant) concorde mot pour mot avec le texte affiché sur la carte active
  dans le prototype Figma v2 (vérifié 2026-08-03, pôle Maritime) — aucune
  correction nécessaire. `poles.image` (5 photos réelles fournies par
  l'équipe institutionnelle, uploadées 2026-07-31) diffère des photos
  utilisées dans le prototype Figma v2 (silhouettes stock génériques par
  métier) — **conservées telles quelles délibérément** : les photos réelles de
  l'institution sont préférées aux silhouettes stock du prototype, à moins
  que l'équipe design ne demande explicitement l'alignement visuel
- **`accueil_reasons`** — heading_fr/en + `items` (O2M ordonné par `sort` :
  title_fr/en, description_fr/en, `image`) — le carrousel "5 raisons de
  choisir l'ISETAG"
- **`accueil_cta_banner`** — heading_fr/en, text_fr/en, button_label_fr/en
  (= CTA 1), button_url — même schéma de base que `admissions_cta_banner` mais
  collection propre à Accueil ; **deux lignes existent** (teaser Admissions en
  milieu de page, CTA final en bas de page), le frontend les distingue par
  `sort` dans `pages_sections`, pas par un champ dédié. + `eyebrow_fr/en`
  (ajouté 2026-08-03, optionnel) — petit label au-dessus du heading, rempli
  uniquement sur la ligne teaser (`"Admissions"`), `null` sur le bandeau final.
  + `cta2_label_fr/en`/`cta2_url` (ajoutés 2026-08-03) — le prototype Figma v2
  affiche **2 boutons** sur les deux bandeaux ; `cta2_url` du teaser
  (`/admissions#modalites`) et de la section Alumni ci-dessous (`cta_url`,
  `/actualites#success-stories`) sont **déduits**, pas confirmés par le
  frontend — même statut que `/vie-campus/` plus bas
- **`accueil_partners_highlight`** — heading_fr/en (= "Nos Entreprises
  Partenaires", corrigé 2026-08-03 pour coller au prototype Figma v2, était
  "Entreprises & Institutions Partenaires") + intro_text_fr/en + `partners`
  (M2M curaté à la main, via jonction `accueil_partners_highlight_partners`).
  Les 8 partenaires existent déjà (mêmes 8 que le prototype Figma v2) et
  **`partners.logo` est rempli sur les 8 lignes** (logos réels fournis par
  l'utilisateur le 2026-08-03, fichiers PNG légers donc non convertis en WebP)
- **`accueil_testimonials_highlight`** — heading_fr/en (= sous-titre affiché,
  "Que deviennent nos anciens étudiants ?") + `testimonials` (M2M curaté à la
  main, via jonction `accueil_testimonials_highlight_testimonials`) — section
  Alumni de la page Accueil (ne pas confondre avec
  `actualites_testimonials_highlight`, section différente de la page
  Actualités). + `eyebrow_fr/en` (ajouté 2026-08-03) — grand titre affiché
  au-dessus du heading dans Figma (= "Les Alumnis de ISETAG" ; le nom de champ
  "eyebrow" est trompeur ici, visuellement c'est le plus gros des deux titres,
  gardé pour cohérence avec les autres blocs). + `cta_label_fr/en`/`cta_url`
  (ajoutés 2026-08-03) — bouton "Découvez nos success stories" (coquille
  d'origine dans Figma, conservée telle quelle) ; même pattern que
  `actualites_testimonials_highlight` qui avait déjà ces champs
- **`accueil_vie_campus_teaser`** — heading_fr/en, text_fr/en, `image`, +
  `cta_label_fr/en`/`cta_url` (ajoutés 2026-08-01) — court teaser en bas de la
  page Accueil. Contenu réel actuel : `cta_label_fr` = "Découvrez notre
  campus", `cta_url` = `/vie-campus/` (route déduite des liens relatifs déjà
  utilisés ailleurs dans le contenu, ex. `/vie-campus/cite-universitaire/`
  dans `admissions_richtext` — **à confirmer avec le frontend** si la route
  réelle diffère). + `eyebrow_fr/en` (ajouté 2026-08-03) — petit titre affiché
  au-dessus du heading dans Figma (= "La Vie sur nos Campus") ; confirme que
  `heading_fr` ("Un cadre d'études structuré à Yassa") n'était **pas** un écart
  à corriger comme supposé le 2026-08-01, mais un second niveau de titre
  distinct — la décision de ne pas y toucher était la bonne. + `gallery` (O2M,
  alias vers `accueil_vie_campus_teaser_gallery`, ajouté 2026-08-01) — galerie
  de photos supplémentaires vue dans le prototype Figma v2 (mosaïque de
  plusieurs images en plus du fond) ; **3 photos réelles fournies 2026-08-03**
  (`sort` 1-3 : salle de classe, atelier/présentation de projet, cour du
  campus). Deux des trois sources dépassaient 1 Mo (17,5 Mo et 27,7 Mo en
  JPEG) — converties en WebP et redimensionnées (~2000px de large) avant
  upload, résultat 175 Ko / 435 Ko ; la troisième (339 Ko) est restée en PNG
  (règle projet : conversion WebP uniquement au-delà de 1 Mo). + `quote_text_fr/en`, `quote_author`,
  `quote_program` (ajoutés 2026-08-01, **remplis 2026-08-03** avec le vrai
  contenu du prototype Figma v2) — citation d'un étudiant incrustée sur la
  mosaïque : `quote_text_fr` = "On se sent bien dans les logments" (coquille
  "logments" présente telle quelle dans la maquette source, conservée à
  l'identique — à signaler à l'équipe contenu), `quote_author` = "Charles
  Mengue", `quote_program` = "L3 Banques et Finance"
- **`actualites_testimonials_highlight`** — heading_fr/en + cta_label_fr/en +
  cta_url optionnels + `testimonials` (M2M curaté à la main, via jonction
  `actualites_testimonials_highlight_testimonials`) — section "Success Stories"
  de la page Actualités, pas Accueil (voir la table de correspondance ci-dessus)
- **`actualites_documents_list`** — heading_fr/en + intro_fr/en (texte libre
  court) + `category_filter` optionnel (le frontend requête `documents`
  séparément, filtrée par cette catégorie si renseignée)

Deux collections Accueil créées lors de la première passe de restructuration
existent toujours mais restent **vides et hors de la page** pour l'instant —
le contenu fourni pour Accueil ne les couvrait pas :

- **`accueil_news_preview`** — heading_fr/en + `limit` (section "dernières
  actualités" — pas encore de brief éditorial pour cette section)
- **`accueil_programs_highlight`** — heading_fr/en + `programs` (M2M curaté ;
  le contenu Accueil actuel met en avant les **pôles**, pas des programmes
  individuels — voir `accueil_poles_highlight` ci-dessus. Cette collection
  resterait pertinente si une future section "formations phares" distincte
  des pôles est ajoutée)

Programmes, Vie Campus et Contact n'ont pas encore leurs propres collections de
blocs (hero/richtext/cta_banner, etc.) : elles seront créées au moment où le
contenu de ces pages sera saisi, en suivant la même convention de nommage et le
même schéma de champs que les collections `admissions_*`/`accueil_*` ci-dessus
(copiées comme référence). Si vous consultez ce guide avant que ce travail soit
fait, la spec OpenAPI live (`GET {BASE_URL}/server/specs/oas`) reste la source
de vérité pour savoir exactement quelles collections existent à un instant donné.

Les 6 pages existent déjà (`accueil`, `programmes`, `admissions`, `vie_campus`,
`actualites`, `contact`, toutes `status: published`, + `a_propos` conservée
mais probablement inutile vu que son contenu vit dans le hero Accueil).
`accueil` (8 sections) et `admissions` (17 sections) ont du contenu réel ; les
4 autres renvoient `sections: []` en attendant que l'équipe communication/
admissions compose leur contenu via l'Admin UI Directus.

## Référence des collections publiques

Champs exacts consultables via la spec OpenAPI ou `GET {BASE_URL}/fields/<collection>`.
Résumé :

- **poles** — `slug`, `name_fr`, `name_en`, `icon`, `color`, `display_order`,
  `description_fr`, `description_en` (WYSIWYG, ajoutés pour la section pôles
  de la page Accueil), `image` (carte carrousel — ajouté pour la section
  pôles de la page Accueil ; **4 pôles sur 5 ont une image** au 2026-07-31,
  il manque celle de `maritime-logistique`, `image: null` en attendant)
- **programs** — `slug`, `name_fr`, `name_en`, `pole` (relation → poles), `level`,
  `is_hnd`, `schedule` (`jour`/`soir`/`jour_soir`), `seo_title_fr`,
  `seo_description_fr`, `cover_image`, `status` (**filtrer `_eq: published`**)
- **scholarships** — `name`, `amount`, `description`, `conditions`,
  `display_order`, `status` (**filtrer `_eq: published`**), + `image`,
  `cta_label_fr/en`, `cta_url` (ajoutés 2026-08-01 pour matcher les cartes
  "Bourses" du prototype Figma v2 de la page Admissions — **collection
  toujours vide**, structure prête mais aucun contenu réel saisi ; ne pas
  construire de section frontend dessus tant qu'elle n'a pas de lignes)
- **tuition_plans** — `cycle_name`, `level` (BTS/HND, Licence, Master,
  Maritime), `total_amount`, `installments` (JSON), `note`, `display_order`,
  `status` (**filtrer `_eq: published`**) — **10 lignes réelles déjà en
  base**, non utilisée par la page Admissions actuelle (qui affiche un
  tableau HTML équivalent codé en dur dans `admissions_richtext`) ; à
  brancher sur la page le jour où le composant "Cycle BTS/Licence/Master" du
  prototype v2 sera implémenté. Note : le prototype ne montre pas de carte
  Maritime — les 2 lignes `level: "Maritime"` restent donc sans page pour
  l'instant, laissées telles quelles en attendant que l'équipe design ajoute
  cette carte
- **news** — `slug`, `title_fr`, `title_en`, `category`, `content_fr`,
  `date_published`, `cover_image`
- **campus_services** — `name_fr`, `name_en`, `icon`, `category`, `display_section`
- **partners** — `name`, `logo`, `type`, `website_url`, `featured`, `display_order`
- **stats_counters** — `label_fr`, `label_en`, `value`, `suffix`, `icon`, `display_order`
- **testimonials** — `student_name`, `program` (relation → programs),
  `graduation_year`, `quote_fr`, `quote_en`, `photo`, `video_url`, `featured`
- **tuition_plans** — `cycle_name`, `level`, `total_amount`, `installments` (JSON
  liste `{label, amount}`), `note`, `display_order`, `status` (**filtrer `_eq: published`**)
- **scholarships** — `name`, `amount`, `description`, `conditions`,
  `display_order`, `status` (**filtrer `_eq: published`**)
- **documents** — `title`, `category` (`admission`/`filieres`/`reglement`/`autre`),
  `file`, `display_order`, `status` (**filtrer `_eq: published`**)

Pour les collections avec un champ `status` (`programs`, `tuition_plans`,
`scholarships`, `documents`), le filtre `published` est déjà imposé **côté
serveur** par la permission Directus elle-même (voir
`scripts/provision_public_read.py`) : une requête anonyme ne peut
techniquement récupérer que les items publiés, même sans filtre explicite
côté client. Ajouter `filter[status][_eq]=published` reste une bonne pratique
de clarté, mais ce n'est pas une mesure de sécurité à réimplémenter.

## Formulaire de pré-inscription — ce n'est PAS un simple POST

Le formulaire déjà livré (`formulaire_preinscription_ISETAG.html`) suppose un
unique `POST` multipart (champs + fichiers) vers une URL personnalisée. **Ça ne
fonctionne pas tel quel avec Directus** (vérifié : Directus ne parse pas un
corps multipart mixte champs+fichiers, que ce soit sur `/items` ou sur un
déclencheur Flow). Le circuit à implémenter côté frontend est en 2 étapes :

1. **Générer un UUID par fichier** côté client (`crypto.randomUUID()`), puis
   uploader **chaque fichier individuellement** :
   ```
   POST {BASE_URL}/files
   Content-Type: multipart/form-data
   ---
   id: <uuid généré>
   file: <binaire>
   ```
   Pas de lecture de retour possible ni nécessaire (upload "à l'aveugle", le
   rôle Public n'a pas de droit de lecture sur ces fichiers-là — RGPD).

2. **Un seul POST JSON** (pas multipart) avec tous les champs texte + les UUID
   de fichiers obtenus à l'étape 1 :
   ```
   POST {BASE_URL}/flows/trigger/<FLOW_ID>
   Content-Type: application/json
   ```
   Champs requis : voir la liste complète dans `ISETAG_project_instructions.md`
   (section "Formulaire de pré-inscription") — ils correspondent 1:1 aux
   attributs `name` du HTML déjà livré. Cas particulier `autres_documents`
   (fichiers facultatifs, 0 à 5) :
   ```json
   "autres_documents": {"create": [{"directus_files_id": "<uuid>"}], "update": [], "delete": []}
   ```

   `<FLOW_ID>` diffère entre dev/staging/prod (chaque environnement provisionne
   son propre Flow via `scripts/provision_admissions_flow.py`) — sera confirmé
   pour staging/prod une fois ces environnements en place. En dev actuellement :
   `897f0ea4-c522-4bef-be2a-7171bb1f3dba`.

Ce circuit a été testé de bout en bout (upload réel, création d'item, email au
service admissions avec liens sécurisés). Aucune confirmation de soumission
n'est renvoyée avec les données de la candidature (la réponse du Flow est
volontairement minimale) — prévoir un message de succès générique côté UI une
fois le `POST` en étape 2 résolu sans erreur HTTP.

## Formulaire de contact — simple POST JSON direct

Contrairement au formulaire de pré-inscription, pas de fichiers ici : un seul
appel suffit, pas de circuit en 2 étapes.

```
POST {BASE_URL}/flows/trigger/<CONTACT_FLOW_ID>
Content-Type: application/json

{"nom": "...", "email": "...", "fonction": "...", "message": "..."}
```

`<CONTACT_FLOW_ID>` diffère entre dev/staging/prod (chaque environnement
provisionne son propre Flow via `scripts/provision_contact_flow.py`). En dev
actuellement : `fa3531bf-e3e9-4059-bc1c-bf36a60fa03a`.

Testé de bout en bout (item créé dans `contact_messages`, email envoyé au
service communication). Comme pour l'admission, aucune lecture publique n'est
possible sur `contact_messages` (rôle Public en `create` uniquement) — prévoir
un message de succès générique côté UI. Les 4 champs ci-dessus sont une
hypothèse basée sur les champs visibles dans le prototype Figma (Nom, Fonction,
Message + email déduit) — **à confirmer avec l'équipe frontend** contre le
formulaire HTML réel une fois construit, comme cela avait été fait pour le
formulaire de pré-inscription.
