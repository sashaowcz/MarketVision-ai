"""MarketVision AI 2.0 — Streamlit mobile-first educational dashboard."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="MarketVision AI 2.0", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>
.block-container{max-width:1150px;padding-top:1rem;padding-bottom:3rem}
[data-testid="stMetric"]{background:#151e30;border:1px solid #29344b;border-radius:14px;padding:12px;min-width:0}
[data-testid="stMetricLabel"]{font-size:.83rem}
[data-testid="stMetricValue"]{font-size:clamp(1.25rem,3vw,2rem)}
@media(max-width:650px){.block-container{padding:0.8rem 0.8rem 4rem}h1{font-size:1.65rem!important}h2{font-size:1.3rem!important}h3{font-size:1.1rem!important}[data-testid="stHorizontalBlock"]{gap:.5rem}[data-testid="stMetric"]{padding:9px}[data-testid="stMetricValue"]{font-size:1.35rem}div[data-testid="stPlotlyChart"]{max-width:100%;overflow:hidden}}
</style>""", unsafe_allow_html=True)

ASSETS = {"MSCI World · URTH":"URTH", "S&P 500 · SPY":"SPY", "Nasdaq 100 · QQQ":"QQQ", "SMI suisse · ^SSMI":"^SSMI", "Nestlé · NESN.SW":"NESN.SW", "Apple · AAPL":"AAPL", "Microsoft · MSFT":"MSFT", "Bitcoin · BTC-USD":"BTC-USD", "Ethereum · ETH-USD":"ETH-USD", "Or · GLD":"GLD", "Obligations US · AGG":"AGG"}

@st.cache_data(ttl=300, show_spinner=False)
def prices(symbol, period):
    df = yf.download(symbol, period=period, interval="1d", auto_adjust=True, progress=False, threads=False)
    if df is None or df.empty: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df.dropna(subset=["Close"]).sort_index()

def indicators(df):
    close=df["Close"].astype(float)
    r=close.pct_change().replace([np.inf,-np.inf],np.nan).dropna()
    ma20=close.rolling(20,min_periods=20).mean(); ma50=close.rolling(50,min_periods=50).mean()
    diff=close.diff(); g=diff.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); l=(-diff.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    rsi=100-100/(1+g/l.replace(0,np.nan))
    rsi_now=float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else (100. if g.iloc[-1]>0 else 50.)
    v=float(r.std()*np.sqrt(252)); dd=float((close/close.cummax()-1).min()); var=float(r.quantile(.05)); tail=r[r<=var]
    return dict(close=close,returns=r,ma20=ma20,ma50=ma50,rsi=rsi_now,vol=v,dd=dd,var=var,cvar=float(tail.mean()),annual=float((close.iloc[-1]/close.iloc[0])**(252/(len(close)-1))-1))

def plot_style(fig, height=320):
    fig.update_layout(template="plotly_dark",height=height,margin=dict(l=8,r=8,t=24,b=20),legend=dict(orientation="h",y=-.2,x=0,font=dict(size=10)),hovermode="x unified",font=dict(size=11),xaxis=dict(automargin=True),yaxis=dict(automargin=True))
    return fig

st.title("📈 MarketVision AI 2.0")
st.caption("Analyse financière pédagogique • mobile et iPhone • cours Yahoo Finance parfois différés • aucun conseil personnalisé")
with st.expander("⚙️ Marchés et paramètres",expanded=True):
    a,b=st.columns(2)
    with a:
        preset=st.selectbox("Actif",list(ASSETS)+["Autre symbole"])
        symbol=st.text_input("Ticker Yahoo Finance",value=ASSETS.get(preset,"TSLA")).strip().upper()
        period=st.selectbox("Historique",["6mo","1y","2y","5y"],index=2)
    with b:
        horizon=st.slider("Horizon (séances)",20,252,90,10)
        n=st.select_slider("Simulations",options=[500,1000,2000,4000],value=1000)
        capital=st.number_input("Capital hypothétique (devise du titre)",min_value=100.,max_value=1e8,value=1000.,step=100.)
    if st.button("🔄 Actualiser les cours",use_container_width=True):
        st.cache_data.clear();st.rerun()
if not symbol or len(symbol)>24:
    st.error("Ticker invalide.");st.stop()
try:
    with st.spinner("Récupération des données financières…"):
        df=prices(symbol,period)
except Exception as e:
    st.error(f"Impossible de charger {symbol}. Réessaie plus tard. ({type(e).__name__})");st.stop()
if len(df)<65:
    st.error("Pas assez de données pour analyser cet actif (minimum 65 séances). Vérifie le symbole ou choisis un historique plus long.");st.stop()
m=indicators(df);close=m["close"];last=float(close.iloc[-1]);change=(last/float(close.iloc[-2])-1)*100
st.caption(f"{symbol} · Dernière séance : {pd.Timestamp(close.index[-1]).strftime('%d/%m/%Y')} · Prix dans la devise native de l'actif, pas nécessairement CHF")
tabs=st.tabs(["📊 Marché","🛡️ Risque","🔮 Scénarios","🔎 Comparer","🔔 Alertes"])
with tabs[0]:
    c1,c2=st.columns(2)
    c1.metric("Dernier cours",f"{last:,.2f}",f"{change:+.2f}% / séance")
    c2.metric("RSI (14)",f"{m['rsi']:.1f}")
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=close.index,y=close.values,name="Cours",line=dict(color="#7c9cff",width=2.5)))
    fig.add_trace(go.Scatter(x=close.index,y=m["ma20"].values,name="MM 20",line=dict(color="#ffb86b",width=1.5)))
    fig.add_trace(go.Scatter(x=close.index,y=m["ma50"].values,name="MM 50",line=dict(color="#5dd8ad",width=1.5)))
    fig.update_yaxes(tickformat=".2f")
    st.plotly_chart(plot_style(fig),use_container_width=True,config={"displayModeBar":False})
    st.caption("Cours ajustés et moyennes mobiles 20 et 50 séances. Les axes s'adaptent à la largeur de l'écran.")
    trend="au-dessus" if last>float(m["ma50"].iloc[-1]) else "en dessous"
    zone="élevé (surachat possible)" if m["rsi"]>=70 else "faible (survente possible)" if m["rsi"]<=30 else "intermédiaire"
    st.info(f"**Lecture automatique :** le cours est {trend} de sa moyenne 50 séances. RSI {zone}. Ce sont des observations, pas des ordres d'achat.")
with tabs[1]:
    c1,c2=st.columns(2);c1.metric("Volatilité annualisée",f"{m['vol']:.1%}");c2.metric("Pire repli historique",f"{m['dd']:.1%}")
    c3,c4=st.columns(2);c3.metric("VaR 95 % (1 séance)",f"{m['var']:.2%}");c4.metric("CVaR 95 % (1 séance)",f"{m['cvar']:.2%}")
    level="très élevée" if m['vol']>=.45 else "élevée" if m['vol']>=.25 else "modérée" if m['vol']>=.12 else "relativement faible"
    st.write(f"**Analyse simple :** volatilité historique {level}. Le rendement annualisé observé sur la période est **{m['annual']:+.1%}** ; il ne prédit pas le rendement futur.")
    st.caption("VaR : seuil historique des 5 % des pires rendements journaliers. CVaR : moyenne de ces pires rendements. Les pertes peuvent dépasser ces valeurs.")
with tabs[2]:
    st.write("Simulation bootstrap : on rééchantillonne les rendements journaliers passés. Les scénarios ne tiennent pas compte des événements imprévus.")
    rng=np.random.default_rng(42)
    samples=rng.choice(m['returns'].to_numpy(),size=(n,horizon),replace=True)
    paths=np.column_stack([np.full(n,last),last*np.cumprod(1+samples,axis=1)])
    q5,q50,q95=np.quantile(paths,[.05,.5,.95],axis=0);x=np.arange(horizon+1)
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=x,y=q95,line=dict(width=0),showlegend=False,hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x,y=q5,fill="tonexty",fillcolor="rgba(124,156,255,.18)",line=dict(width=0),name="Intervalle P5–P95"))
    fig.add_trace(go.Scatter(x=x,y=q50,line=dict(color="#5dd8ad",width=2),name="Médiane"))
    st.plotly_chart(plot_style(fig),use_container_width=True,config={"displayModeBar":False})
    finals=paths[:,-1];amounts=np.quantile(finals/last*capital,[.05,.5,.95])
    c1,c2,c3=st.columns(3)
    for c,label,val in zip((c1,c2,c3),("Défavorable P5","Médian P50","Favorable P95"),amounts):c.metric(label,f"{val:,.0f}")
    st.write(f"**Résultats du modèle :** {np.mean(finals>last):.1%} des trajectoires finissent en hausse ; {np.mean(finals<last*.8):.1%} finissent avec une baisse de plus de 20 %.")
    st.warning("Probabilités issues du modèle uniquement, non calibrées sur le futur. Montants sans frais, fiscalité ni conversion de devise.")
with tabs[3]:
    st.write("Comparaison indicative sur un historique commun de 1 an. Les prix et risques sont exprimés dans la devise propre à chaque actif.")
    selected=st.multiselect("Choisir jusqu'à 5 actifs",list(ASSETS),default=["MSCI World · URTH","S&P 500 · SPY","Or · GLD"],max_selections=5)
    if st.button("Comparer les actifs",use_container_width=True):
        rows=[]; curves={}
        for name in selected:
            try:
                d=prices(ASSETS[name],"1y")
                if len(d)<65:continue
                z=indicators(d);s=z["close"]
                rows.append({"Actif":name,"Performance 1 an":f"{(s.iloc[-1]/s.iloc[0]-1):+.1%}","Volatilité":f"{z['vol']:.1%}","Repli max":f"{z['dd']:.1%}"})
                curves[name]=s/s.iloc[0]*100
            except Exception:continue
        if rows:
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
            aligned=pd.concat(curves,axis=1).dropna()
            if not aligned.empty:
                fig=go.Figure()
                for name in aligned:fig.add_trace(go.Scatter(x=aligned.index,y=aligned[name],name=name))
                st.plotly_chart(plot_style(fig),use_container_width=True,config={"displayModeBar":False})
                st.caption("Base 100 à la première date commune. Performance passée ≠ performance future.")
        else:st.warning("Aucune comparaison disponible. Réessaie.")
with tabs[4]:
    st.write("**Alertes locales à l'écran** : elles sont évaluées lorsque l'application est ouverte ou actualisée. Pas de notification push, d'e-mail ni de surveillance en arrière-plan.")
    threshold=st.number_input("Seuil de prix à surveiller",min_value=0.01,value=float(round(last,2)),step=max(round(last*.01,2),.01))
    direction=st.radio("Déclencher si le cours est…",["au-dessus du seuil","en dessous du seuil"],horizontal=True)
    triggered=last>=threshold if direction.startswith("au-dessus") else last<=threshold
    if triggered:st.warning(f"🔔 Seuil atteint sur le dernier cours disponible : {last:,.2f}.")
    else:st.success(f"Seuil non atteint : dernier cours disponible {last:,.2f}.")
    st.caption("Pour des notifications iPhone automatiques, il faudra ajouter un service de surveillance et de notification externe.")
st.divider()
st.caption("Sources : Yahoo Finance via yfinance (données potentiellement différées). Commentaires automatiques basés sur des règles, pas sur un modèle de langage. Aucun achat ni vente exécuté. Usage éducatif uniquement.")
