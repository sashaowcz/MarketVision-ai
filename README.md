# MarketVision AI

Tableau de bord interactif Streamlit pour analyser des cours financiers, des indicateurs techniques, des risques historiques et des scénarios simulés.

## Démarrage

1. Installer Python 3.10 ou plus récent.
2. Dans ce dossier, exécuter :

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

3. Ouvrir l'adresse locale indiquée dans le terminal (généralement http://localhost:8501).

## Fonctionnalités

- Recherche de symboles Yahoo Finance et sélection d'actifs courants.
- Historique quotidien, prix, variation, moyennes mobiles 20/50 jours et RSI 14.
- Volatilité annualisée, drawdown maximal, VaR et CVaR historiques.
- Simulation Monte-Carlo par bootstrap de rendements quotidiens, avec percentiles 5/50/95.
- Mise en cache des cours pendant 5 minutes et actualisation manuelle.

## Limites importantes

- **Pas de temps réel garanti** : Yahoo Finance peut publier des cours différés et limiter les requêtes. Le rafraîchissement ne supprime pas ce délai.
- **Aucune prévision fiable garantie** : le bootstrap suppose que les rendements historiques sont représentatifs du futur ; il ne modélise pas explicitement les changements de régime, les corrélations temporelles ni les chocs inconnus.
- **Pas de conseil financier** : les scénarios ne constituent pas des recommandations personnalisées. Aucun passage d'ordres.
- Les valeurs affichées sont dans la devise native du symbole, sans conversion automatique en CHF.
- Pour un usage professionnel, remplacer le fournisseur par une API de marché sous licence et ajouter monitoring, gestion des erreurs et tests de validation.
