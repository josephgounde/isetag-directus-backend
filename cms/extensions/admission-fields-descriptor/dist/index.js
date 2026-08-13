/**
 * GET /admission-fields-descriptor
 *
 * Renvoie les descripteurs de champs du formulaire de pré-inscription
 * (admission_applications) : field, type, interface, required, sort, note,
 * choices — à l'exclusion des champs de gestion (status, source,
 * annee_academique, desired_program) et des champs masqués (meta.hidden).
 *
 * Contexte : le front recopiait ces listes à la main depuis un export
 * ponctuel du schéma ; toute modification faite dans Directus restait
 * invisible côté front (voir ISETAG_project_instructions.md, entrée
 * "Descripteurs de champs du formulaire d'admission").
 *
 * `directus_fields` n'est lisible ni via /items/directus_fields (bloqué en
 * dur pour toute collection système, permissions ou pas) ni, pour
 * `admission_applications` spécifiquement, via /fields/:collection (cette
 * route lie strictement sa visibilité au champ `fields` de la permission
 * `read` sur la collection elle-même — donc toute permission assez large
 * pour voir les descripteurs serait aussi assez large pour lire les
 * candidatures). Voir les deux collections "Introspection Formulaire
 * (interne)" (rôle/policy/utilisateur, désormais inutilisées) laissées de
 * côté après ce constat.
 *
 * Cet endpoint contourne le problème en lisant le schéma directement en
 * mémoire (FieldsService, accountability: null = accès système, jamais
 * exposé publiquement) plutôt qu'en repassant par une route soumise aux
 * permissions. La portée est fixée en dur dans le code ci-dessous
 * (COLLECTION, EXCLUDED_FIELDS) — jamais dérivée d'un paramètre de requête —
 * donc cet endpoint ne peut décrire aucune autre collection, et ne touche
 * jamais aux données réelles des candidatures (table admission_applications
 * elle-même n'est jamais interrogée).
 */

const COLLECTION = 'admission_applications';
const EXCLUDED_FIELDS = ['status', 'source', 'annee_academique', 'desired_program'];

module.exports = function registerEndpoint(router, context) {
  const { services, getSchema, logger } = context;
  const { FieldsService } = services;

  router.get('/', async (req, res) => {
    try {
      const schema = await getSchema();
      const fieldsService = new FieldsService({ schema, accountability: null });
      const allFields = await fieldsService.readAll(COLLECTION);

      const data = allFields
        .filter((f) => !EXCLUDED_FIELDS.includes(f.field) && !(f.meta && f.meta.hidden))
        .sort((a, b) => ((a.meta && a.meta.sort) || 0) - ((b.meta && b.meta.sort) || 0))
        .map((f) => ({
          field: f.field,
          type: f.type,
          interface: f.meta ? f.meta.interface : null,
          required: !!(f.meta && f.meta.required),
          sort: f.meta ? f.meta.sort : null,
          note: f.meta ? f.meta.note : null,
          choices: f.meta && f.meta.options ? f.meta.options.choices || null : null,
        }));

      res.json({ data });
    } catch (err) {
      if (logger) logger.error(err, 'admission-fields-descriptor endpoint failed');
      res.status(500).json({ errors: [{ message: 'Internal error' }] });
    }
  });
};
