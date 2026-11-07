# 🪽 AngelVision AI 2.1

Application Streamlit mobile-first pour iPhone, Android et ordinateur. Elle affiche des cours, indicateurs de tendance, mesures de risque, scénarios Monte-Carlo, comparaison d'actifs, comptes et alertes email.

> Les alertes sont des **conditions à examiner**, pas des recommandations d'achat. Les données Yahoo Finance peuvent être différées.

## Mise à jour rapide de ton site actuel

Remplace dans ton dépôt GitHub les fichiers `app.py`, `requirements.txt` et `README.md`, puis ajoute aussi `angelvision_core.py`, `alert_worker.py`, `schema.sql` et le dossier `.github/workflows/`.

Streamlit redéploiera l'application automatiquement.

## Comptes : mode démo et mode production

Sans configuration supplémentaire, la page Compte fonctionne avec une petite base SQLite locale. C'est pratique pour tester, mais Streamlit Cloud peut effacer ce fichier lors d'un redémarrage ou redéploiement.

Pour de vrais comptes persistants, utilise Supabase.

### 1. Supabase

1. Crée un projet sur Supabase.
2. Ouvre l'éditeur SQL et exécute tout le contenu de `schema.sql`.
3. Dans le tableau de bord Supabase, récupère le **Project URL** et une **Secret key** côté serveur.
4. Dans Streamlit Cloud > ton app > Settings > Secrets, ajoute :

```toml
SUPABASE_URL="https://TON-PROJET.supabase.co"
SUPABASE_SECRET_KEY="sb_secret_..."
```

Ne mets jamais la secret key directement dans GitHub.

## Emails avec Resend

1. Crée un compte Resend.
2. Crée une API key.
3. Vérifie un domaine d'envoi ou utilise une adresse d'envoi autorisée par Resend.
4. Ajoute dans les Secrets Streamlit :

```toml
RESEND_API_KEY="re_..."
RESEND_FROM="AngelVision <alerts@ton-domaine.ch>"
```

Une fois configuré, l'app peut envoyer l'email de bienvenue.

## Alertes automatiques même quand l'app est fermée

Le fichier `.github/workflows/alerts.yml` lance `alert_worker.py` environ une fois par heure avec GitHub Actions.

Dans GitHub : Repository > Settings > Secrets and variables > Actions > New repository secret. Ajoute :

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `RESEND_API_KEY`
- `RESEND_FROM`

Tu peux ensuite ouvrir l'onglet **Actions** du dépôt et lancer manuellement `AngelVision email alerts` pour tester.

## Règles d'alerte incluses

- prix sous un seuil ;
- prix au-dessus d'un seuil ;
- RSI faible ;
- retour du cours au-dessus de la moyenne mobile 50 jours.

Un délai d'environ 20 heures évite de répéter le même email trop souvent.

## Installation locale

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Sécurité

Les mots de passe sont hachés avec PBKDF2-HMAC-SHA256. Pour une application publique à grande échelle, il est préférable d'utiliser un système d'authentification géré (par exemple Supabase Auth) plutôt que ce mécanisme simplifié.
