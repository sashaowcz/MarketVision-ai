# AngelVision AI 2.8

Version mobile-first d’AngelVision avec marchés, risque, communauté de marchés, comptes, alertes et **portefeuille d’entraînement**.

## Nouveautés 2.7

- **Niveau d’explication** dans le compte : `Débutant` ou `Standard`.
- **Portefeuille d’entraînement** (paper trading) avec argent fictif.
- Capital de départ limité à **1 000–20 000 CHF**.
- Achat/vente virtuels avec les derniers cours disponibles via Yahoo Finance.
- Conversion indicative en CHF pour comparer les positions.
- Solde, valeur totale, performance, positions et historique des opérations.
- Aucun ordre réel n’est envoyé.

## Important

Les données Yahoo Finance peuvent être différées. Le portefeuille d’entraînement est un outil éducatif et non une plateforme de courtage. Les performances simulées ne prédisent pas les performances futures.

## Mise à jour Supabase

Réexécute `schema.sql` dans **Supabase → SQL Editor**. Le script ajoute de façon idempotente :

- `users.explanation_level`
- `paper_accounts`
- `paper_trades`

## Lancer localement

```bash
pip install -r requirements.txt
streamlit run app.py
```


## Correctif 2.8
- Navigation Compte ↔ Marchés sans rechargement complet de la page.
- La connexion reste active pendant la navigation dans la session Streamlit.
- Le bouton Compte et le retour utilisent désormais des boutons Streamlit au lieu de liens `?view=`.
