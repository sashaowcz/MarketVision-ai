# AngelVision AI 3.0 — Trading Intelligence Engine (Paper Trading Only)

AngelVision 3.0 est une application de recherche financière et de **paper trading**. Elle ne contient aucune connexion à un broker et ne peut pas envoyer d'ordre réel.

## Nouveau moteur IA

Le moteur `forecast_engine.py` utilise un **ensemble de modèles** plutôt qu'un seul modèle :

- HistGradientBoosting
- Extra Trees
- modèle linéaire robuste (Ridge / Logistic Regression)

Les modèles sont évalués chronologiquement avec un **walk-forward backtest** et un `gap` égal à l'horizon de prévision pour limiter les fuites temporelles.

### Variables analysées

- rendements sur plusieurs horizons
- moyennes mobiles 10 / 20 / 50 / 100 / 200
- volatilité
- RSI
- MACD
- position dans les bandes de Bollinger
- ATR / amplitude de séance
- drawdown
- volume et volume relatif
- régime de marché historique via SPY, VIX et taux US 10 ans quand disponible
- bêta et corrélation au marché quand les données de régime sont disponibles

### Sorties du moteur

- rendement central prévu
- probabilité de hausse
- intervalle d'incertitude empirique
- qualité du backtest
- précision directionnelle et benchmark
- AUC et score de Brier
- accord entre les modèles
- fiabilité dans le régime actuel
- score de confiance
- signal : **SCÉNARIO HAUSSIER / SCÉNARIO BAISSIER / ABSTENTION**

Le mode **ABSTENTION** est essentiel : si l'avantage statistique est trop faible, si les modèles se contredisent ou si le backtest n'est pas convaincant, AngelVision refuse de donner un signal directionnel.

## Internet et contexte externe

`external_context.py` peut enrichir l'analyse avec :

- actualités récentes via GDELT
- données macro via FRED
- dépôts publics SEC / Form 4 pour les sociétés américaines compatibles

Le contexte Internet est volontairement séparé du backtest historique pour éviter d'utiliser des informations futures dans l'évaluation du modèle.

## Sécurité : argent réel désactivé

AngelVision 3.0 ne possède :

- aucune API de broker ;
- aucune fonction d'achat/vente réelle ;
- aucun stockage de clé de courtage ;
- aucune exécution automatique.

Les prévisions sont destinées au portefeuille fictif et à l'apprentissage.

## Dépendances

```text
streamlit>=1.35,<2
pandas>=2.1,<3
numpy>=1.26,<3
plotly>=5.20,<7
yfinance>=0.2.50,<2
requests>=2.31,<3
scikit-learn>=1.5,<2
```

## Streamlit Secrets optionnels

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_SECRET_KEY = "sb_secret_..."
RESEND_API_KEY = "re_..."
RESEND_FROM = "AngelVision <alerts@your-domain.com>"
FRED_API_KEY = "..."
SEC_USER_AGENT = "AngelVision your-email@example.com"
```

Ne mets jamais ces secrets dans GitHub.

## Mise à jour depuis AngelVision 2.8

Remplace/ajoute au minimum :

- `app.py`
- `forecast_engine.py`
- `external_context.py`
- `requirements.txt`
- `README.md`

Les autres fichiers du ZIP conservent les comptes, la communauté, les alertes et le portefeuille fictif déjà présents dans AngelVision.

## Avertissement

Aucun modèle, même complexe, ne peut prévoir les marchés avec certitude. Un backtest peut être trompeur, un régime peut changer et des nouvelles inattendues peuvent rendre un modèle inutile. AngelVision est un outil de recherche et de simulation. Il ne doit pas servir de seule base à une décision d'investissement réelle.
