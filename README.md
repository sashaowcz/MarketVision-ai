# AngelVision AI 2.3 — Communauté

Application Streamlit mobile-first pour iPhone, Android et ordinateur.

## Nouveautés 2.3

- **Communauté AngelVision** inspirée d’un fil social : publications publiques, réponses et likes.
- **Texte uniquement** : aucun upload d’image ou de fichier.
- Une publication peut joindre une **fiche d’actif créée dans AngelVision** avec ticker, dernier cours, score de tendance et score de risque.
- Lecture du fil sans compte ; connexion requise pour publier, répondre, aimer ou supprimer ses propres publications.
- Messages limités à 500 caractères et affichés de façon échappée pour éviter l’injection HTML.
- Persistance des publications et likes via **Supabase** ; fallback SQLite pour les essais locaux.

## Déploiement

Remplace dans ton dépôt les fichiers :

- `app.py`
- `angelvision_core.py`
- `schema.sql`
- `README.md`

Garde également `alert_worker.py`, `requirements.txt` et `.github/workflows/alerts.yml` de la version précédente.

### Mise à jour Supabase

Si ton projet Supabase existe déjà, ouvre **SQL Editor** et exécute à nouveau le fichier `schema.sql`. Les commandes `create table if not exists` ajoutent les tables de communauté sans supprimer les comptes ni les alertes existantes.

Les nouvelles tables sont :

- `posts`
- `post_likes`

Le backend utilise `SUPABASE_URL` et `SUPABASE_SECRET_KEY` dans les Secrets Streamlit. Ne mets jamais la clé secrète dans GitHub.

## Lancement local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Important

AngelVision est un outil d’analyse éducatif. Les publications communautaires sont du contenu utilisateur et ne constituent pas des recommandations d’investissement validées par AngelVision.
