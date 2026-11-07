# AngelVision AI 2.6 — En-tête mobile corrigé

Application Streamlit mobile-first pour iPhone, Android et ordinateur.

## Nouveautés 2.5

- La **banderole de marchés est visible immédiatement à l'ouverture** : le header/toolbar Streamlit qui la recouvrait sur iPhone est masqué dans l'interface publique.
- La banderole reste placée tout en haut de la page AngelVision, juste sous la zone Safari.
- Nouveau header façon application : **logo AngelVision à gauche + bouton Compte à droite**, directement sous la banderole.
- Le bouton Compte affiche le pseudonyme lorsque l'utilisateur est connecté.
- **Compte & alertes** n'encombre plus la navigation principale : la navigation centrale reste focalisée sur **Marchés / Communauté**.
- Depuis la page Compte, un bouton **Retour aux marchés** permet de revenir immédiatement à l'analyse.
- Toutes les fonctions de la 2.4 restent présentes : banderole marchés, communauté sans texte libre, périodes, likes, partages publics/amis, recherche d'actifs, alertes, Supabase et emails.

## Fichiers à mettre à jour sur GitHub

Pour passer de 2.4 à 2.5, le changement principal est dans :

- `app.py`
- `README.md`

Tu peux aussi remplacer tous les fichiers du ZIP par sécurité, sauf `__pycache__` et les fichiers `.pyc` qui ne doivent jamais être envoyés sur GitHub.

## Supabase

Aucun changement de schéma n'est nécessaire entre 2.4 et 2.5. Si `schema.sql` de la 2.4 a déjà été exécuté dans Supabase, tu n'as rien à refaire pour cette mise à jour.

Les secrets restent dans Streamlit :

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `RESEND_API_KEY`
- `RESEND_FROM`

Ne publie jamais ces clés dans GitHub.

## Lancement local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Important

Les données Yahoo Finance peuvent être différées. Les scores, alertes, simulations, propositions et likes servent à analyser ou découvrir des marchés ; ils ne constituent pas des recommandations d'achat ou de vente.


## Correctifs 2.6

- La barre Streamlit supérieure est masquée pour rendre la banderole visible dès l’ouverture.
- Logo AngelVision à gauche et bouton Compte compact à droite.
- Espace supplémentaire entre le logo et le bouton Compte sur iPhone.
