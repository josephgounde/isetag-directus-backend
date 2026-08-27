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
(voir plus bas, section Admissions). Pour connaître la forme du formulaire
(champs, choix) sans lire les candidatures, voir "Descripteurs de champs du
formulaire d'admission" plus bas.

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
| Actualités *(nav "Ressources" → renommée)* | `pages` (`key=actualites`) → sections, + `news` | Hero éditorial (`actualites_hero`), puis un listing **live** (pas des blocs page-builder) piloté directement par `news` : `filter[featured][_eq]=true` (curation manuelle, un choix éditorial — pas juste "la plus récente") pour "À la Une" (grand format), le reste trié `sort=-date_published` et paginé (9/page) pour la grille "Lire Aussi". Toujours filtrer `filter[status][_eq]=published` (comme `documents`/`scholarships`/`tuition_plans`). Puis le même bandeau CTA partagé que les autres pages (`accueil_cta_banner` id=2, pas de collection dédiée). **`actualites_testimonials_highlight`/`actualites_documents_list` ont été retirées le 2026-08-27** : aucune contrepartie dans le vrai fichier Figma design (pas de section "Success Stories" ni "ressources" sur cette page) — ne plus s'y référer. |
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
`accueil_hero`, `contact_hero`, `actualites_hero`, ...).

Tout se récupère en **un seul appel** grâce au deep-fetch, en listant les
collections propres à la page demandée dans `sections.item:<collection>.*` :

```
GET {BASE_URL}/items/pages?filter[key][_eq]=admissions&fields=*,sections.collection,sections.sort,sections.item:admissions_hero.*,sections.item:admissions_steps.items.*,sections.item:admissions_brochure.*,sections.item:admissions_tuition_highlight.*,sections.item:admissions_scholarships_highlight.*
```

(`admissions_richtext` et `admissions_feature` ont été retirées de cette
requête le 2026-08-10 : les deux collections existent toujours dans le schéma
mais n'ont plus aucune ligne liée à `pages_sections` sur la page Admissions —
le prototype Figma mis à jour ne montre plus ce contenu, voir
`ISETAG_project_instructions.md`. Inutile de les interroger, la réponse serait
vide.)

`admissions_tuition_highlight` et `admissions_scholarships_highlight` ne
portent que le `heading_fr/en` — le frontend doit faire un appel séparé pour
les données réelles : `GET {BASE_URL}/items/tuition_plans?filter[status][_eq]=published&sort=display_order`
et `GET {BASE_URL}/items/scholarships?filter[status][_eq]=published&sort=display_order`
(même pattern que `poles` pour la section pôles d'Accueil).

Exemple pour Accueil (noter le `.partners.partners_id.*` et
`.news.news_id.*` pour traverser les jonctions M2M jusqu'aux données
réelles) :

```
GET {BASE_URL}/items/pages?filter[key][_eq]=accueil&fields=*,sections.collection,sections.sort,sections.item:accueil_hero.*,sections.item:accueil_poles_highlight.*,sections.item:accueil_cta_banner.*,sections.item:accueil_promoter_message.*,sections.item:accueil_reasons.heading_fr,sections.item:accueil_reasons.heading_en,sections.item:accueil_reasons.items.*,sections.item:accueil_partners_highlight.heading_fr,sections.item:accueil_partners_highlight.intro_text_fr,sections.item:accueil_partners_highlight.partners.partners_id.*,sections.item:accueil_testimonials_highlight.eyebrow_fr,sections.item:accueil_testimonials_highlight.cta_label_fr,sections.item:accueil_testimonials_highlight.cta_url,sections.item:accueil_testimonials_highlight.news.news_id.*,sections.item:accueil_vie_campus_teaser.*,sections.item:accueil_vie_campus_teaser.gallery.image,sections.item:accueil_vie_campus_teaser.gallery.sort
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
- **`admissions_tuition_highlight`** (ajouté 2026-08-03) — heading_fr/en (=
  "Nos différents Cycles" depuis le 2026-08-10 — c'était "Tarifs et Frais
  d'Inscription" jusque-là, corrigé pour coller au texte affiché par le
  prototype Figma mis à jour, qui ne parle plus de tarifs à cet endroit),
  même
  pattern que `accueil_poles_highlight` : le tableau de prix lui-même vient
  directement de la collection partagée `tuition_plans` (les 10 lignes,
  triées par `display_order`, pas de sélection curatée). Les 3 cartes
  "Cycle X" affichées **au-dessus** du tableau (niveau requis, date de
  rentrée, mode d'admission) viennent d'une collection séparée, voir
  `admissions_tuition_cycles` ci-dessous.
  + `common_documents_fr/en` (WYSIWYG, ajouté 2026-08-04) — la liste
  "Pièces communes" affichée sur chaque carte Cycle. Un seul champ ici plutôt
  que dupliqué sur les 3 lignes de `admissions_tuition_cycles` : le texte est
  **identique mot pour mot sur les 3 cartes** dans le prototype Figma v2
  (vérifié par extraction complète du texte de la frame), donc partagé plutôt
  que répété. Absent de Directus jusqu'ici — repéré et signalé par l'équipe
  éditoriale après la première passe sur `admissions_tuition_cycles`, qui
  n'avait couvert que niveau/rentrée/mode d'admission
- **`admissions_tuition_cycles`** (ajouté 2026-08-04) — collection autonome,
  **pas une section de page-builder** (comme `tuition_plans`/`scholarships`,
  appel séparé : `GET {BASE_URL}/items/admissions_tuition_cycles?sort=display_order`).
  Une ligne par cycle (BTS, Licence, Master, **Maritime** — 4 lignes depuis
  le 2026-08-10 ; la carte Maritime a été ajoutée au prototype Figma à cette
  date, elle était absente des versions précédentes) :
  `heading_fr/en` (ex. "Cycle BTS"), `level` (texte, sert de clé de
  correspondance avec `tuition_plans.level` — "BTS/HND", "Licence", "Master" —
  côté frontend pour associer chaque carte à ses lignes de tarifs),
  `academic_year` (ex. "2026/2027"), `start_date_fr/en` (ex.
  "11 septembre 2026"), `required_level_fr/en`, `admission_mode_fr/en`,
  `display_order`. Ce contenu était jusqu'ici absent de Directus (probablement
  codé en dur côté frontend) — signalé par l'équipe éditoriale, ajouté pour
  que ce soit éditable comme le reste
- **`admissions_scholarships_highlight`** (ajouté 2026-08-03) — heading_fr/en
  (= "Bourses, aides et facilités") + `eyebrow_fr/en` (= "La Scolarité") +
  `intro_text_fr/en` (ajouté 2026-08-13, = "Des avantages ou bourses peuvent
  être proposés dans le cadre de partenariats académiques et de campagnes
  spécifiques.") ; même pattern que le reste du bloc : les cartes
  viennent directement de `scholarships` (triées par `display_order`)
- **`admissions_brochure`** (ajouté 2026-08-03) — heading_fr/en, text_fr/en,
  cta_label_fr/en + `file` (relation directe vers `directus_files`, interface
  `file` générique et non `file-image` puisque c'est un PDF) — bloc
  "Télécharger notre brochure" du prototype Figma v2. **`file` est vide pour
  l'instant** : le PDF de la brochure admissions n'a pas encore été fourni —
  structure prête, à remplir dès réception (ne pas afficher le bouton de
  téléchargement côté frontend tant que `file` est `null`)
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
- **`accueil_promoter_message`** (ajouté 2026-08-10) — heading_fr/en (=
  "Bienvenue à l'ISETAG"), subheading_fr/en (= "Le mot du promoteur"),
  body_fr/en (WYSIWYG, texte libre), `author` (texte simple, non traduit —
  ex. "Pasteur PAMEN FLAUBERT"). Nouvelle section apparue dans la mise à jour
  du prototype Figma du 2026-08-10, absente avant cette date. Insérée dans
  `pages_sections` de la page Accueil juste après la bannière CTA Admissions
  (`sort=4`). **`_en` vide pour l'instant** — traduction anglaise à fournir,
  structure prête (même convention que `admissions_brochure.file`).
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
  + `image` (ajouté 2026-08-04) — fichier `directus_files` (WebP), rempli
  **sur les deux lignes** (id=1 teaser et id=2 final) — le prototype Figma v2
  affiche le même collage (carte d'identité, stylo, relevés de notes) sur les
  deux bandeaux, pas seulement le final. D'abord recréé par composition à
  partir des visuels bruts de `contenuç_accueil/` (deux itérations, corrigées
  après retour utilisateur), puis **remplacé le même jour par le visuel
  officiel** fourni par l'équipe design (`contenuç_accueil/CTA image.png`,
  converti en WebP, 326 Ko → 118 Ko) ; les deux lignes pointent vers le même
  fichier (le frontend le recadre différemment selon le conteneur, cf. les
  deux captures Figma)
- **`accueil_partners_highlight`** — heading_fr/en (= "Nos Entreprises
  Partenaires", corrigé 2026-08-03 pour coller au prototype Figma v2, était
  "Entreprises & Institutions Partenaires") + intro_text_fr/en + `partners`
  (M2M curaté à la main, via jonction `accueil_partners_highlight_partners`).
  Les 8 partenaires existent déjà (mêmes 8 que le prototype Figma v2) et
  **`partners.logo` est rempli sur les 8 lignes** (logos réels fournis par
  l'utilisateur le 2026-08-03, fichiers PNG légers donc non convertis en WebP)
- **`accueil_testimonials_highlight`** (nom de collection conservé pour ne pas
  casser `sections.item:accueil_testimonials_highlight.*` côté frontend, mais
  **section entièrement repensée le 2026-08-13** — ce n'est plus une section
  Alumni). Avant cette date : heading_fr/en + `testimonials` (M2M vers
  `testimonials`), eyebrow "Les Alumnis de ISETAG", CTA "Découvez nos success
  stories". Le prototype Figma mis à jour a remplacé tout ça par un carrousel
  d'actualités réelles ("Actualités de ISETAG") — même refonte que les autres
  écarts déjà traités ce mois-ci (contenu retiré/remplacé par le prototype).
  **Nouveaux champs** : `eyebrow_fr/en` (= "Actualités de ISETAG"),
  `cta_label_fr/en` (= "Découvrez nos actualités"), `cta_url` (=
  `/actualites`), `heading_fr/en` (laissé `null` — le titre affiché par
  carte vient de l'actualité elle-même, pas d'un heading statique du bloc),
  et surtout `news` (M2M curaté à la main, via jonction
  `accueil_testimonials_highlight_news`, même mécanique que `partners` —
  `sections.item:accueil_testimonials_highlight.news.news_id.*` pour
  traverser jusqu'aux vraies données `news`). L'ancien champ `testimonials`
  et sa jonction ont été supprimés (plus jamais utilisés sur ce bloc — le
  reste de la collection `testimonials` n'est pas affecté ;
  `actualites_testimonials_highlight`, elle, a depuis été retirée entièrement
  le 2026-08-27, voir plus bas). Premier élément du carrousel : l'actualité
  "Immersion professionnelle chez GAP Motors" (`news.slug =
  immersion-professionnelle-gap-motors`), `cover_image` = la photo fournie
  par l'équipe.
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
- **`actualites_testimonials_highlight` / `actualites_documents_list`** —
  **retirées le 2026-08-27**, 0 ligne depuis leur création et aucune
  contrepartie dans le vrai fichier Figma design de la page Actualités (voir
  entrée ci-dessous). Ne plus s'y référer — mention conservée ici uniquement
  pour l'historique, au cas où d'anciennes notes en parlent encore ailleurs.
- **`actualites_hero`** — **nouvelle collection créée le 2026-08-27**,
  non-singleton (id=1). Section hero de la page Actualités : `title_fr/en`,
  `subtitle_fr/en`, `image` (vrai champ éditorial cette fois, contrairement à
  `contact_hero` — le fond est une vraie photo/collage dans le design, pas un
  simple habillage décoratif). `image` laissée `null` pour l'instant, aucune
  photo hero fournie par l'utilisateur pour cette page. Le reste de la page
  (**"À la Une" + "Lire Aussi"**) n'a **pas** de collection dédiée : c'est un
  listing live directement piloté par `news`, voir la table de correspondance
  plus haut.

Deux collections Accueil créées lors de la première passe de restructuration
(`accueil_news_preview`, `accueil_programs_highlight` + sa jonction) ont été
**supprimées le 2026-08-03** lors d'un nettoyage strict contre le prototype
Figma v2 : vides depuis leur création, jamais branchées à la page, aucun
équivalent visuel dans le prototype (celui-ci met en avant les **pôles**, pas
des programmes individuels — voir `accueil_poles_highlight` ci-dessus). Si une
section "formations phares" distincte des pôles est demandée un jour, ce sera
une nouvelle collection à recréer, pas une réactivation.

Programmes et Vie Campus n'ont pas encore leurs propres collections de
blocs (hero/richtext/cta_banner, etc.) : elles seront créées au moment où le
contenu de ces pages sera saisi, en suivant la même convention de nommage et le
même schéma de champs que les collections `admissions_*`/`accueil_*` ci-dessus
(copiées comme référence). Si vous consultez ce guide avant que ce travail soit
fait, la spec OpenAPI live (`GET {BASE_URL}/server/specs/oas`) reste la source
de vérité pour savoir exactement quelles collections existent à un instant donné.

**Contact** a été construite le 2026-08-27 (dev uniquement, pas encore poussée
en prod) : `contact_hero` (title_fr/en, subtitle_fr/en, pas d'image) au-dessus
du formulaire, puis le même bandeau CTA final que Accueil/Programmes/
Actualités — réutilisé tel quel via `accueil_cta_banner` id=2, pas une nouvelle
collection (`accueil_cta_banner` est un composant multi-pages, comme
`partners`/`stats_counters`). Le formulaire de contact lui-même reste géré par
`contact_messages` (voir « Formulaire de contact » plus bas) — 4 champs
(nom, email, fonction, message), `email` étant `required` même si le design
Figma n'a que 3 champs visibles (Nom/Fonction/Message) : ajouté côté schéma
pour permettre une réponse au message.

**Actualités** a aussi été construite le 2026-08-27 (dev uniquement) :
`actualites_hero` (title_fr/en, subtitle_fr/en, `image`) au-dessus d'un
listing live piloté par `news` ("À la Une" = `featured=true`, curation
manuelle ; "Lire Aussi" = le reste, paginé), puis le même bandeau CTA partagé
(`accueil_cta_banner` id=2). Les deux anciennes collections
`actualites_testimonials_highlight`/`actualites_documents_list` ont été
retirées (0 ligne, aucune contrepartie dans ce fichier design). `news` a
aussi reçu deux champs manquants ce jour-là, repérés en creusant "Lire Aussi"
(question directe de l'utilisateur : "only two collections, what about the
lire aussi grid") : `featured` (boolean, même pattern que
`testimonials.featured`) et `status` (published/draft/archived, même pattern
que `documents`/`scholarships`/`tuition_plans` — `news` n'avait jusqu'ici
**aucun** contrôle brouillon/publié, chaque ligne était publique dès sa
création). Lecture publique resserrée à `filter[status][_eq]=published`.
L'unique actualité existante (GAP Motors) passée à `status=published`,
`featured=true`. **Vérifié réellement, pas juste supposé** : une ligne
`draft` de test créée puis lue anonymement (`403` en lecture directe, absente
du listing), supprimée ensuite.

Les 6 pages existent déjà (`accueil`, `programmes`, `admissions`, `vie_campus`,
`actualites`, `contact`, toutes `status: published`, + `a_propos` conservée
mais probablement inutile vu que son contenu vit dans le hero Accueil).
`accueil` (9 sections), `admissions` (19 sections, depuis l'ajout des
sections tarifs/bourses le 2026-08-03), `contact` (2 sections, depuis le
2026-08-27) et `actualites` (2 sections, depuis le 2026-08-27) ont du
contenu réel ; `programmes` et `vie_campus` renvoient `sections: []` en
attendant que l'équipe communication/admissions compose leur contenu via
l'Admin UI Directus.

## Référence des collections publiques

Champs exacts consultables via la spec OpenAPI ou `GET {BASE_URL}/fields/<collection>`.
Résumé :

- **contact_hero** — **nouvelle collection créée le 2026-08-27**, non-singleton
  (id=1). Section hero de la page Contact, au-dessus du formulaire. Champs :
  `title_fr/en`, `subtitle_fr/en`, pas d'image (fond décoratif fixe, pas un
  champ éditorial dans le design Figma). `_en` vide pour l'instant.
- **programmes_hero** — **nouvelle collection créée le 2026-08-25**, singleton.
  Section hero de la page Programmes (même pattern que `admissions_hero`/
  `vie_campus_hero`, sans les champs CTA — pas de bouton dans le prototype
  Figma pour cette section). Champs : `title_fr/en`, `subtitle_fr/en`,
  `image`. `_en` vide pour l'instant (contenu FR uniquement dans le
  prototype).
- **poles** — **reconstruite le 2026-08-23** pour matcher le nouveau prototype
  Figma de la page Programmes. **4 lignes** (le 5ᵉ pôle "Santé & Paramédical"
  a été supprimé, absent du nouveau design) : `slug`, `name_fr`, `name_en`,
  `icon`, `color`, `display_order` (1=Maritime, 2=Industriel, 3=Gestion,
  4=Communication, ordre du prototype), `image` (photo héro du pôle),
  `description_fr/en` (ancien champ, conservé), et les nouveaux champs
  ajoutés pour matcher le prototype : `subtitle_fr/en` (sous-titre court sous
  le nom du pôle), `notes_fr/en` (bloc de notes/puces : régimes de cours,
  tutelle académique, date limite d'admission), `deadline_fr/en` (ligne
  "Date limite de recevabilité des dossiers : 16 septembre 2026" — identique
  sur les 4 pôles actuellement), `featured_name_fr/en` (nom de la filière
  phare mise en avant sur la carte du pôle), `featured_description_fr/en`
  (paragraphe descriptif de cette filière phare), `tags_fr` (JSON — liste des
  autres filières/spécialités affichées en pastilles sous la filière phare).
  Les champs `_en` sont tous `null` pour l'instant (contenu FR uniquement
  dans le prototype).
- **programs** — **reconstruite le 2026-08-23** pour matcher le "Référentiel
  de nos formations" du nouveau prototype Figma (liste par cycle avec 6
  onglets). Champs : `slug`, `name_fr`, `name_en`, `pole` (relation → poles,
  **`null` pour toutes les nouvelles lignes** — le référentiel du prototype
  n'associe pas ces filières à un pôle précis, c'est un catalogue académique
  transversal par cycle), `cycle` (**nouveau champ**, valeurs :
  `bts`/`hnd`/`licence`/`master`/`maritime`/`certifiante`), `level`, `is_hnd`,
  `schedule` (anciens champs, conservés uniquement sur les lignes `cycle:
  "hnd"` héritées), `seo_title_fr`, `seo_description_fr`, `cover_image`,
  `status` (**filtrer `_eq: published`**).
  Répartition actuelle (77 lignes) : `bts` 39, `certifiante` 18, `licence` 8,
  `maritime` 6, `hnd` 6 (**anciennes lignes conservées telles quelles** —
  le prototype Figma n'a que du texte de remplissage anglais pour l'onglet
  HND, non utilisable), `master` 0 (**aucun contenu réel dans le prototype**
  pour cet onglet — c'est une copie exacte du contenu Licence, donc rien n'a
  été inséré ; à compléter quand le contenu réel sera fourni). Pour les
  cycles `licence` et `certifiante`, chaque puce du prototype (ex. "Génie
  Civil : Bâtiments ; Réseaux hydrauliques ... ; Voies et Ouvrages d'art.")
  est stockée comme **une seule ligne `name_fr`** avec les sous-spécialités
  séparées par `;` à l'intérieur du texte, plutôt que d'être éclatée en
  lignes séparées.
- **pole_filieres** — **nouvelle collection créée le 2026-08-25**, distincte
  de `programs`/`poles`. Elle porte le contenu de la rangée de boutons
  filtrables affichée sous l'en-tête de chaque section "Pôle X" de la page
  Programmes (mécanique repérée dans le fichier Figma "Test 1", zone
  node-id=4190-1478 — même principe de bande de variantes empilées que pour
  le "Référentiel des formations"). Cliquer un bouton change le texte et la
  photo affichés en dessous ; ce n'est **pas** le même contenu que le
  catalogue plat `programs`. **33 lignes** : Maritime 10, Industriel 9,
  Gestion 8, Communication 6. Champs : `pole` (relation → poles),
  `display_order`, `code` (sigle court affiché sur le bouton non-sélectionné
  quand il existe, ex. `GLPM`/`EMN`/`PM`/`AQ`/`SSPPM`/`SN` — `null` sinon),
  `button_label_fr` (texte exact du bouton), `title_fr` (nom complet utilisé
  en tête de la description), `kind` (`filiere` = description en
  paragraphes, ou `certifiante` = intro + liste à puces groupée),
  `description_fr` (JSON — liste de paragraphes, utilisé si `kind:
  "filiere"`), `intro_fr` (texte d'intro des cartes `certifiante`, identique
  sur les 3 pôles qui en ont une : "Formations courtes de 4 à 9 mois,
  proposées en cours du jour et du soir, avec 75 % de pratique annoncé."),
  `certifiante_groups` (JSON — liste de `{group_fr, items_fr}` ; `group_fr`
  est `null` pour Maritime et Gestion qui n'ont qu'une liste plate, rempli
  pour Industriel qui a 5 groupes nommés type "Génie Civil"), `image`
  (photo dédiée par filière — **33/33 lignes ont une image, 2026-08-25**.
  25 photos uploadées depuis `contenu_programmes/poles_images/` fourni par
  l'utilisateur et liées sur 27 lignes (flyer "Formations certifiantes"
  réutilisé sur les 3 pôles qui en ont une) ; identification faite par
  inspection visuelle, les fichiers Figma exportés n'ayant aucun nom
  exploitable ("Rectangle 65 (n).png"). Les 2 dernières lignes — Maritime
  GLPM et Communication "Communication des Organisations & Communication
  option Publicité" — réutilisent directement `poles.image` (le pôle avait
  déjà cette photo, uploadée lors de la reconstruction `poles`/`programs`
  du 2026-08-23, puisque GLPM et Communication des Organisations sont déjà
  les filières "featured" de leur pôle respectif — même photo, pas de
  nouvel upload),
  `has_content` (booléen — `false` sur 4 lignes du pôle Communication qui
  n'ont pas encore de contenu réel dans le prototype : "Communication option
  Publicité", "E-Commerce et Marketing numérique", "Marketing Digital",
  "Formations certifiantes digitales" — les boutons existent dans le design
  mais le frontend doit soit les masquer, soit afficher un état "contenu à
  venir"), `status`. Le bouton "Je me pré-inscris" visible sur chaque carte
  Figma est un CTA générique identique partout — non stocké en base,
  à coder en dur côté frontend.
- **scholarships** — `name`, `amount`, `description`, `conditions`,
  `display_order`, `status` (**filtrer `_eq: published`**), + `image`,
  `cta_label_fr/en`, `cta_url` (ajoutés 2026-08-01 pour matcher les cartes
  "Bourses" du prototype Figma v2 de la page Admissions). **2 lignes réelles
  ajoutées 2026-08-03** après confirmation du contenu réel du prototype :
  "Bourse SNK" (image = flyer réel "Bourse Académique d'Innovation" de la SNK
  Foundation, `cta_url` = `https://www.snk-foundation.org`, vraie URL trouvée
  sur le flyer) et "Bourse de l'Université Montplaisir Tunis" (pas d'image
  dans le prototype, `cta_url` laissé `null` — pas de cible confirmée).
  Branchée sur la page Admissions via la nouvelle section
  `admissions_scholarships_highlight` (voir plus bas).
- **Page Vie Campus — collections créées le 2026-08-23** pour matcher le
  prototype Figma "Vie Campus - Desktop" (1233×9809). La page n'avait aucun
  contenu structuré avant (seule `campus_services` existait, vide). Toutes en
  lecture publique.
  - **vie_campus_hero** (singleton, 1 ligne) — `eyebrow_fr/en`,
    `heading_fr/en`, `body_fr/en`, `image` (photo cour ISETAG)
  - **vie_campus_highlights** (6 lignes, section "Notre campus c'est :") —
    `title_fr/en`, `description_fr/en`, `display_order`
  - **vie_campus_residence** (singleton, 1 ligne, section "La Cité
    Universitaire") — `heading_fr/en`, `image` (photo bâtiment), `description_fr/en`
    (texte de gauche), `details_fr/en` (texte de droite, tarifs), `gallery`
    (JSON — 3 UUID fichiers)
  - **campus_services** (collection existante, était vide — **8 lignes**,
    section "Services du campus") — `name_fr/en` (existant),
    **`description_fr/en` et `display_order` ajoutés** (nouveaux champs).
    Pas d'image par ligne — la bannière de section vit sur
    `vie_campus_sections.services_image`.
  - **vie_campus_service_details** (7 lignes, nouvelle collection) — les 3
    blocs détaillés du prototype (Santé/restauration, Mobilité/sport/connexion,
    Infrastructures) aplatis en une liste avec `group_fr` (titre du bloc
    parent), `group_image` (photo du bloc, répétée sur chaque ligne du même
    groupe), `title_fr/en`, `body_fr/en`, `bullets_fr` (JSON liste de
    chaînes), `display_order`, `gallery` (JSON — **uniquement renseigné sur
    la dernière ligne du groupe "Infrastructures d'apprentissage et de
    pratique"**, id=7 "Amphithéâtre" — c'est le seul des 3 groupes à avoir
    une galerie de 3 photos dans le prototype ; convention à connaître côté
    frontend : ne pas s'attendre à une galerie sur les groupes Santé/Mobilité)
  - **vie_campus_clubs** (4 lignes, section "Clubs & Associations") —
    `name_fr/en`, `description_fr/en`, `display_order`
  - **vie_campus_staff** (4 lignes, section "Enseignants et encadreurs") —
    **contenu placeholder du prototype Figma inséré tel quel sur demande
    explicite de l'utilisateur** : les 4 lignes sont identiques ("Dr Marina
    Walter" / "Ingénieure en énergies renouvelables" / même `photo`) — **pas
    de vraies données enseignants dans le prototype**, à remplacer quand le
    contenu réel sera fourni. Photo source `enseignant.jpg` (11,9 Mo, fournie
    par l'utilisateur) convertie en WebP + redimensionnée à 1600px de large
    avant upload (règle projet : toute image > 1 Mo est convertie), résultat
    97 Ko / 1600×1066.
  - **vie_campus_sections** (singleton, 1 ligne) — 3 paragraphes d'intro de
    section (`services_intro_fr`, `clubs_intro_fr`, `staff_intro_fr`) +
    3 bannières photo (`services_image`, `clubs_image`, `staff_image`) qui ne
    rentraient pas naturellement ailleurs
  - **Photos** : 14 photos réelles uploadées depuis `contenu vie campus/`
    (dossier fourni par l'utilisateur le 2026-08-23, après la première passe
    de contenu texte) + 1 convertie en WebP (voir `vie_campus_staff`
    ci-dessus). Associées par comparaison visuelle directe avec les sections
    Figma correspondantes, comme pour `contenu_programmes/`.
  - **Non repris** : les paragraphes d'intro `_en` (tous `null`, comme
    ailleurs — contenu FR uniquement dans le prototype), et le bandeau CTA
    "Commence Ton Chemin Aujourd'hui" (identique à celui de la page
    Programmes, non construit ici — hors périmètre de cette passe)
- **tuition_plans** — `cycle_name`, `level` (BTS/HND, Licence, Master,
  Maritime), `total_amount`, `installments` (JSON), `note`, `display_order`,
  `status` (**filtrer `_eq: published`**) — **10 lignes réelles**, désormais
  **branchées sur la page Admissions** (2026-08-03) via la nouvelle section
  `admissions_tuition_highlight` (voir plus bas) ; le tableau HTML codé en dur
  dans `admissions_richtext` (sort 9) reste en place à côté (texte
  d'introduction + liste des filières par cycle), le vrai tableau de prix
  vient de cette collection. Un écart de montant a été corrigé le 2026-08-03 :
  `id=6` ("Licence — Sciences de gestion appliquée") était à 500 000 FCFA,
  corrigé à **395 000 FCFA** (valeur confirmée par l'utilisateur, conforme au
  prototype Figma v2). Note : le prototype ne montre pas de carte Maritime
  séparée — les 2 lignes `level: "Maritime"` restent affichées avec les
  autres (triées par `display_order`), aucune section dédiée n'existe pour
  elles dans Figma
- **news** — `slug`, `title_fr`, `title_en`, `category`, `content_fr`
  (extrait court, utilisé sur les cartes "À la Une"/"Lire Aussi" — pas
  l'article complet), `date_published`, `cover_image`, `featured` (boolean —
  **ajouté 2026-08-27**, curation manuelle de l'article "À la Une" sur la
  page Actualités, pas juste le plus récent), `status` (**ajouté
  2026-08-27**, `published`/`draft`/`archived` — **filtrer `_eq:
  published`**, jusque-là `news` n'avait aucun filtre de visibilité),
  `body_fr`/`body_en` (**ajoutés 2026-08-27**, WYSIWYG/HTML — même pattern
  que `admissions_richtext.content_fr` — le contenu **complet** de
  l'article, pour une page de détail par actualité que le front doit encore
  construire ; `content_fr` reste le seul champ utilisé sur la liste
  Actualités elle-même)
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

## Descripteurs de champs du formulaire d'admission

Ne recopiez plus à la main les listes de choix (`sexe`, `dernier_diplome`,
`cycle`, `domaine`, `regime`, etc.) : un ajout/retrait de valeur côté Directus
resterait invisible tant que personne ne relivre un nouvel export — c'est le
problème qui s'est déjà produit avec les cycles de formation. À la place :

```
GET {BASE_URL}/admission-fields-descriptor
```

Public, sans authentification. Renvoie tous les champs du formulaire de
pré-inscription (hors champs de gestion `status`/`source`/`annee_academique`/
`desired_program`, gérés côté back), triés par `sort` :

```json
{
  "data": [
    {
      "field": "sexe",
      "type": "string",
      "interface": "select-radio",
      "required": true,
      "sort": 15,
      "note": null,
      "choices": [
        {"text": "Féminin", "value": "Féminin"},
        {"text": "Masculin", "value": "Masculin"},
        {"text": "Autre", "value": "Autre"}
      ]
    }
  ]
}
```

`interface` indique le type de contrôle à construire (`input`, `input-multiline`,
`select-dropdown`, `select-radio`, `boolean`, `datetime`, `file`, `list-m2m`).
`choices` n'est présent (non `null`) que pour les champs à liste fermée —
utilisez `text` pour l'affichage et `value` pour ce qui doit être envoyé dans
la requête de soumission (section suivante). Cet endpoint ne renvoie que la
description des champs, jamais le contenu des candidatures — il reste
impossible de lire `admission_applications` (403, volontaire).

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
un message de succès générique côté UI.

**Mise à jour 2026-08-27**, après revue du vrai fichier Figma design (pas
seulement le prototype) : le formulaire n'a réellement que **3 champs
visibles** — Nom, Fonction, Message — pas de champ email dans la maquette.
`email` a néanmoins été gardé `required` côté schéma (décision produit :
sans email, impossible de répondre à un message reçu) — le champ doit donc
être ajouté à l'UI même s'il n'apparaît pas dans le design Figma tel quel.
