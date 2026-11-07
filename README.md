# AngelVision AI 2.2

Version mobile-first pour iPhone, Android et ordinateur.

## Nouveautés 2.2

- Identité visuelle **blanc + rouge AngelVision**.
- Logo typographique rouge intégré à l'interface.
- Graphiques mobiles plus naturels : **glisser = déplacer**, pincement = zoom, double-tap = reset, boutons de dézoom/reset et curseur temporel.
- Pseudonyme lors de la création du compte.
- Recherche Yahoo Finance pour retrouver des actions, ETF, indices, cryptomonnaies, devises et matières premières non présentes dans la sélection rapide.
- Alertes disponibles sur les actifs recherchés.
- Configuration Supabase actualisée pour les nouvelles **Secret keys** côté serveur.
- Workflow GitHub Actions fourni pour vérifier les alertes environ chaque heure.

## Mise à jour depuis l'iPhone

1. Décompresse le ZIP dans l'app **Fichiers**.
2. Dans ton dépôt GitHub, remplace `app.py`, `angelvision_core.py`, `alert_worker.py`, `requirements.txt`, `schema.sql` et `README.md`.
3. Ajoute aussi le fichier caché `.github/workflows/alerts.yml`. Sur iPhone, GitHub peut masquer les dossiers commençant par un point : utilise Safari en **Version pour ordinateur** si nécessaire.
4. Streamlit redéploiera automatiquement l'app.

## Activer Supabase depuis l'iPhone

1. Dans Safari, ouvre `supabase.com` et crée un nouveau projet.
2. Ouvre **SQL Editor** → **New query**.
3. Copie tout le contenu de `schema.sql`, colle-le et appuie sur **Run**.
4. Ouvre **Connect** ou **Settings → API Keys**.
5. Copie le **Project URL**.
6. Crée/copie une **Secret key** commençant par `sb_secret_` (côté serveur uniquement).
7. Dans Streamlit : **Manage app → Settings → Secrets**, ajoute :

```toml
SUPABASE_URL = "https://TON-PROJET.supabase.co"
SUPABASE_SECRET_KEY = "sb_secret_..."
```

8. Sauvegarde puis redémarre l'app. Dans **Compte & alertes**, AngelVision doit afficher que Supabase est activé.

> Ne mets jamais `SUPABASE_SECRET_KEY` dans un fichier GitHub public.

## Emails avec Resend

Ajoute également dans Streamlit Secrets :

```toml
RESEND_API_KEY = "re_..."
RESEND_FROM = "AngelVision <alerts@ton-domaine.com>"
```

Pour GitHub Actions, ajoute les mêmes quatre valeurs dans : **Repository → Settings → Secrets and variables → Actions**.

## Graphiques tactiles

- 1 doigt : déplacement horizontal/vertical du graphique.
- Pincement : zoom avant/arrière.
- Double-tap : réinitialisation de la vue.
- Barre d'outils : zoom +, zoom −, autoscale, reset.
- Mini curseur sous les graphiques principaux pour choisir rapidement une période.

## Important

Les données Yahoo Finance peuvent être différées. Les scores, simulations et alertes ne sont pas des conseils personnalisés et ne prédisent pas les marchés avec certitude.
