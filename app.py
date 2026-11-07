"""MarketVision AI — educational market dashboard. Run: streamlit run app.py"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="MarketVision AI", page_icon="📈", layout="wide")
st.title("📈 MarketVision AI")
st.caption("Tableau de bord éducatif • cours Yahoo Finance potentiellement différés • aucune recommandation personnalisée")

PRESETS = {"MSCI World (ETF URTH)": "URTH", "S&P 500 (ETF SPY)": "SPY", "Nasdaq 100 (ETF QQQ)": "QQQ", "Bitcoin (USD)": "BTC-USD", "Or (ETF GLD)": "GLD", "Apple": "AAPL", "Nestlé (Suisse)": "NESN.SW", "SMI (Suisse)": "^SSMI"}
with st.sidebar:
    st.header("Paramètres")
    preset = st.selectbox("Marché", list(PRESETS) + ["Autre symbole"])
    ticker = st.text_input("Symbole Yahoo Finance", value="MSFT" if preset == "Autre symbole" else PRESETS[preset]).strip().upper()
    period = st.selectbox("Historique", ["6mo", "1y", "2y", "5y"], index=2)
    horizon = st.slider("Horizon de simulation (jours de bourse)", 20, 252, 90)
    simulations = st.slider("Trajectoires Monte-Carlo", 500, 5000, 2000, step=500)
    capital = st.number_input("Capital hypothétique (devise de l'actif)", 100.0, 10000000.0, 1000.0, step=100.0)
    st.info("Actualisation : le bouton ci-dessous recharge les données. Les cours peuvent être différés.")
    if st.button("🔄 Actualiser les données"):
        st.cache_data.clear()
        st.rerun()

@st.cache_data(ttl=300, show_spinner=False)
def fetch_prices(symbol: str, history: str) -> pd.DataFrame:
    data = yf.download(symbol, period=history, interval="1d", auto_adjust=True, progress=False, threads=False)
    if data is None or data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data.dropna(subset=["Close"]).sort_index()

if not ticker:
    st.warning("Saisis un symbole valide.")
    st.stop()
try:
    with st.spinner("Chargement des cours…"):
        df = fetch_prices(ticker, period)
except Exception as exc:
    st.error(f"Impossible de récupérer les données pour {ticker}. Vérifie le symbole, la connexion ou réessaie. Détail : {exc}")
    st.stop()
if len(df) < 65:
    st.error("Historique insuffisant : au moins 65 séances sont nécessaires pour calculer les indicateurs et le risque.")
    st.stop()

close = df["Close"].astype(float)
returns = close.pct_change().dropna()
last = float(close.iloc[-1]); prev = float(close.iloc[-2])
change = (last / prev - 1) * 100
vol = float(returns.std(ddof=1) * np.sqrt(252))
ann_return = float((close.iloc[-1] / close.iloc[0]) ** (252 / (len(close)-1)) - 1)
wealth = close / close.iloc[0]
max_dd = float((wealth / wealth.cummax() - 1).min())
var95 = float(np.quantile(returns, 0.05))
tail = returns[returns <= var95]
cvar95 = float(tail.mean()) if not tail.empty else var95
ma20 = close.rolling(20).mean(); ma50 = close.rolling(50).mean()
delta = close.diff(); gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean(); loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
rs = gain / loss.replace(0, np.nan)
rsi = 100 - 100 / (1 + rs)
if loss.iloc[-1] == 0:
    rsi_now = 100.0 if gain.iloc[-1] > 0 else 50.0
else:
    rsi_now = float(rsi.iloc[-1])

st.subheader(f"{ticker} — aperçu du marché")
st.caption(f"Dernière séance disponible : {pd.Timestamp(close.index[-1]).strftime('%d/%m/%Y')} • devise native du symbole • données quotidiennes")
a,b,c,d = st.columns(4)
a.metric("Dernier cours", f"{last:,.2f}", f"{change:+.2f}% (1 séance)")
b.metric("Volatilité annualisée", f"{vol:.1%}")
c.metric("Drawdown maximum", f"{max_dd:.1%}")
d.metric("RSI (14)", f"{rsi_now:.1f}")
fig = go.Figure()
fig.add_trace(go.Scatter(x=close.index, y=close, name="Cours", line=dict(width=2)))
fig.add_trace(go.Scatter(x=ma20.index, y=ma20, name="Moyenne 20 jours"))
fig.add_trace(go.Scatter(x=ma50.index, y=ma50, name="Moyenne 50 jours"))
fig.update_layout(template="plotly_dark", title="Cours ajusté et moyennes mobiles", xaxis_title="Date", yaxis_title="Prix (devise native)", hovermode="x unified", height=430)
st.plotly_chart(fig, use_container_width=True)

st.subheader("🛡️ Analyse du risque")
r1,r2,r3 = st.columns(3)
r1.metric("VaR historique 95 % (1 jour)", f"{var95:.2%}")
r2.metric("CVaR historique 95 % (1 jour)", f"{cvar95:.2%}")
r3.metric("Rendement annualisé historique", f"{ann_return:+.1%}")
if vol < 0.12: risk = "Volatilité relativement faible"
elif vol < 0.25: risk = "Volatilité modérée"
elif vol < 0.45: risk = "Volatilité élevée"
else: risk = "Volatilité très élevée"
st.write(f"**Lecture simple :** {risk}. Le cours est {'au-dessus' if last > ma50.iloc[-1] else 'en dessous'} de sa moyenne mobile à 50 séances. RSI : {'surachat possible' if rsi_now >= 70 else 'survente possible' if rsi_now <= 30 else 'zone intermédiaire'}. Ces indicateurs ne sont pas des signaux fiables d'achat ou de vente à eux seuls.")
st.caption("VaR : seuil historique des 5 % de pires séances ; CVaR : perte moyenne lors de ces séances. Les pertes futures peuvent être plus importantes.")

st.subheader("🔮 Simulation de scénarios futurs")
st.write("Monte-Carlo : rendements journaliers simulés par rééchantillonnage des rendements historiques (bootstrap). Chaque trajectoire est hypothétique ; ce modèle ne prévoit pas les nouvelles, les crises ni les changements de régime.")
rng = np.random.default_rng(42)
sampled = rng.choice(returns.to_numpy(), size=(simulations, horizon), replace=True)
paths = last * np.cumprod(1 + sampled, axis=1)
paths = np.vstack([np.full(simulations, last), paths.T])
q05, q50, q95 = np.quantile(paths, [0.05, 0.5, 0.95], axis=1)
x = np.arange(horizon + 1)
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=x, y=q95, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
fig2.add_trace(go.Scatter(x=x, y=q05, mode="lines", fill="tonexty", fillcolor="rgba(70,130,180,0.22)", line=dict(width=0), name="Intervalle simulé 5–95 %"))
fig2.add_trace(go.Scatter(x=x, y=q50, name="Médiane simulée", line=dict(width=3)))
fig2.update_layout(template="plotly_dark", title="Distribution des trajectoires simulées", xaxis_title="Séances futures", yaxis_title="Prix hypothétique", height=400)
st.plotly_chart(fig2, use_container_width=True)
finals = paths[-1]
p_up = float(np.mean(finals > last))
p_loss20 = float(np.mean(finals < last * 0.8))
low, med, high = np.quantile(finals / last * capital, [0.05, 0.5, 0.95])
s1,s2,s3 = st.columns(3)
s1.metric("Scénario défavorable (P5)", f"{low:,.0f}")
s2.metric("Scénario médian (P50)", f"{med:,.0f}")
s3.metric("Scénario favorable (P95)", f"{high:,.0f}")
st.write(f"**Probabilités simulées :** {p_up:.1%} de finir au-dessus du cours actuel ; {p_loss20:.1%} de perdre plus de 20 % sur l'horizon. Valeurs de portefeuille en devise native, sans frais ni fiscalité.")
st.warning("Ces probabilités sont conditionnelles au modèle, non des probabilités réelles calibrées. Aucune décision d'investissement ne devrait reposer uniquement sur ces résultats.")
st.caption("Sources : Yahoo Finance via yfinance. Aucun ordre d'achat ou de vente n'est exécuté. Données et calculs fournis à titre éducatif.")
