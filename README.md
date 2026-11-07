# MarketVision AI 2.0

Application Streamlit adaptée aux écrans mobiles (iPhone, Android et ordinateur).

## Installation locale

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Mise à jour de l'application déjà publiée

Dans le dépôt GitHub existant, **remplacez** `app.py`, `requirements.txt` et `README.md` par les fichiers fournis (sans créer de sous-dossier). Validez avec **Commit changes**. Streamlit Community Cloud redéploie normalement automatiquement le dépôt. Si besoin, ouvrez **Manage app** puis **Reboot app**.

Sur iPhone, utilisez Safari > GitHub > dépôt > Add file > Upload files, et demandez la version pour ordinateur si nécessaire. Pour remplacer un fichier, GitHub peut exiger de supprimer l'ancien fichier puis d'importer le nouveau, ou de coller son contenu dans l'éditeur web.

## Fonctionnalités

- Cours Yahoo Finance et indicateurs (MM20, MM50, RSI)
- Volatilité, VaR 95 %, CVaR 95 %, drawdown
- Simulations bootstrap Monte-Carlo
- Comparaison multi-actifs
- Alertes de seuil **à l'écran uniquement**
- Explications automatiques **fondées sur des règles** (pas de LLM externe)

## Limites

Les données ne sont pas garanties en temps réel. Pas de notifications push ni d'analyse d'actualités par IA. Les simulations ne sont pas des probabilités prédictives calibrées. Aucune transaction n'est exécutée. Usage pédagogique, pas un conseil financier personnalisé.
