# AngelVision AI 2.4 — Marchés communautaires

Application Streamlit mobile-first pour iPhone, Android et ordinateur.

## Nouveautés 2.4

- **Banderole de marché défilante** tout en haut : S&P 500, Nasdaq, Dow, SMI, Euro Stoxx 50, Bitcoin, or et pétrole WTI avec variation de la dernière séance disponible.
- La communauté n'est plus un réseau social texte : **aucun post libre, aucune image, aucun commentaire**.
- Un utilisateur connecté peut **proposer un marché** et choisir une période : 1 jour, 1 semaine, 1 mois, 6 mois ou 1 an.
- Une proposition peut être envoyée **au public** ou **à un ami par pseudonyme**.
- Les comptes connectés peuvent **liker un marché sur la période proposée**. Le compteur de likes est public.
- Chaque carte affiche automatiquement la performance du marché sur la période sélectionnée.
- Persistance des propositions et likes via **Supabase**, avec fallback SQLite pour le mode démo.
- Le rangeslider des graphiques est plus fin sur mobile et les encadrés d'analyse utilisent davantage l'identité blanc/rouge AngelVision.

## Fichiers à mettre à jour sur GitHub

Remplace :

- `app.py`
- `angelvision_core.py`
- `schema.sql`
- `README.md`

Garde aussi `alert_worker.py`, `requirements.txt` et `.github/workflows/alerts.yml`.

## Mise à jour Supabase

Dans Supabase → **SQL Editor**, exécute à nouveau `schema.sql`.

AngelVision 2.4 ajoute :

- `market_proposals`
- `market_likes`

Le fichier conserve également les anciennes tables `posts` / `post_likes` afin de ne pas casser une base 2.3 existante, mais l'interface 2.4 ne les utilise plus.

Les secrets restent dans Streamlit :

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `RESEND_API_KEY` et `RESEND_FROM` pour les emails

Ne publie jamais ces clés dans GitHub.

## Lancement local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Important

Les likes et propositions expriment uniquement l'intérêt de la communauté pour un marché et une période. Ils ne constituent pas une recommandation d'achat ou de vente. Les données Yahoo Finance peuvent être différées.
