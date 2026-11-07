import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from angelvision_core import ASSETS, authenticate_user, create_alert, create_user, delete_alert, download_prices, indicators, list_alerts, production_storage_enabled, send_email

st.set_page_config(page_title='AngelVision AI', page_icon='🪽', layout='wide', initial_sidebar_state='collapsed')
st.markdown('''<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>
html,body,[class*="css"]{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Arial,sans-serif!important}
.block-container{max-width:1120px;padding-top:1rem;padding-bottom:4.5rem}
h1,h2,h3{letter-spacing:-.025em;font-weight:650!important}
.av-hero{padding:.35rem 0 .9rem}.av-kicker{font-size:.8rem;letter-spacing:.08em;text-transform:uppercase;color:#7b8799}.av-sub{color:#6f7783;font-size:.95rem;line-height:1.45}
[data-testid="stMetric"]{background:#f8fafc;border:1px solid #e5e7eb;border-radius:16px;padding:14px;min-width:0;box-shadow:0 1px 2px rgba(15,23,42,.03)}
[data-testid="stMetricLabel"]{color:#64748b!important;font-size:.82rem}[data-testid="stMetricValue"]{color:#111827!important;font-weight:650!important;font-size:clamp(1.25rem,3vw,2rem)}
div[data-baseweb="tab-list"]{gap:.25rem;overflow-x:auto;white-space:nowrap}button[data-baseweb="tab"]{padding:.55rem .65rem!important}
.stButton>button{border-radius:14px!important;min-height:44px!important}.stTextInput input,.stNumberInput input{border-radius:12px!important}
.av-score{border:1px solid #e5e7eb;border-radius:16px;padding:14px 16px;background:white;margin:.25rem 0 .8rem}.av-score strong{font-size:1.1rem}.av-muted{color:#6b7280;font-size:.88rem}
@media(max-width:650px){.block-container{padding:.7rem .7rem 5.3rem}h1{font-size:1.75rem!important}h2{font-size:1.32rem!important}h3{font-size:1.08rem!important}[data-testid="stHorizontalBlock"]{gap:.45rem}[data-testid="stMetric"]{padding:11px}[data-testid="stMetricValue"]{font-size:1.35rem}div[data-testid="stPlotlyChart"]{max-width:100%;overflow:hidden}.av-sub{font-size:.9rem}}
</style>''', unsafe_allow_html=True)

@st.cache_data(ttl=300, show_spinner=False)
def prices(symbol, period):
    return download_prices(symbol, period)

def plot_style(fig, height=330):
    fig.update_layout(template='plotly_white',height=height,margin=dict(l=8,r=8,t=18,b=25),legend=dict(orientation='h',y=-.2,x=0,font=dict(size=10)),hovermode='x unified',font=dict(size=11,family='Helvetica Neue, Arial'),xaxis=dict(automargin=True,gridcolor='#eef2f7'),yaxis=dict(automargin=True,gridcolor='#eef2f7'),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
    return fig

if 'user' not in st.session_state: st.session_state.user = None

st.markdown('<div class="av-hero"><div class="av-kicker">Analyse de marché claire</div><h1>🪽 AngelVision AI</h1><div class="av-sub">Marchés, risque, scénarios et alertes à surveiller — optimisé iPhone et mobile. Les signaux sont éducatifs et ne constituent pas des recommandations d’investissement.</div></div>', unsafe_allow_html=True)
page = st.radio('Navigation', ['Marchés','Compte & alertes'], horizontal=True, label_visibility='collapsed')

if page == 'Compte & alertes':
    st.subheader('Compte AngelVision')
    mode = st.radio('Mode', ['Se connecter','Créer un compte'], horizontal=True)
    if not st.session_state.user:
        with st.form('auth'):
            email = st.text_input('Email', placeholder='nom@exemple.com')
            password = st.text_input('Mot de passe', type='password')
            submit = st.form_submit_button('Créer le compte' if mode=='Créer un compte' else 'Se connecter', use_container_width=True)
        if submit:
            if '@' not in email or len(password) < 8:
                st.error('Entre un email valide et un mot de passe d’au moins 8 caractères.')
            else:
                try:
                    if mode == 'Créer un compte':
                        user = create_user(email,password); st.session_state.user = user
                        ok,msg = send_email(user['email'],'Bienvenue sur AngelVision AI','<h2>Bienvenue sur AngelVision AI</h2><p>Ton compte est créé. Les alertes servent à signaler des conditions de marché à examiner, pas à donner un ordre d’achat.</p>')
                        st.success('Compte créé.' + (' Email de bienvenue envoyé.' if ok else ''))
                    else:
                        user = authenticate_user(email,password)
                        if user: st.session_state.user=user; st.success('Connexion réussie.')
                        else: st.error('Email ou mot de passe incorrect.')
                    st.rerun()
                except Exception as e: st.error(str(e))
    else:
        user = st.session_state.user
        c1,c2=st.columns([3,1]); c1.success(f"Connecté : {user['email']}")
        if c2.button('Déconnexion',use_container_width=True): st.session_state.user=None; st.rerun()
        if production_storage_enabled():
            st.caption('Stockage persistant : Supabase activé.')
        else:
            st.warning('Mode démo : les comptes sont enregistrés localement et peuvent être perdus lors d’un redéploiement Streamlit. Active Supabase pour une vraie version publique.')
        st.markdown('### Créer une alerte email')
        a,b = st.columns(2)
        with a:
            preset=st.selectbox('Actif',list(ASSETS),key='alert_asset'); symbol=ASSETS[preset]
            rule_label=st.selectbox('Condition',['Prix sous un seuil','Prix au-dessus d’un seuil','RSI faible','Reprise au-dessus de la moyenne 50 jours'])
        with b:
            rule_map={'Prix sous un seuil':'price_below','Prix au-dessus d’un seuil':'price_above','RSI faible':'rsi_low','Reprise au-dessus de la moyenne 50 jours':'trend_recovery'}
            rt=rule_map[rule_label]
            if rt in ('price_below','price_above'):
                threshold=st.number_input('Seuil de prix',min_value=0.01,value=100.0,step=1.0)
            elif rt=='rsi_low':
                threshold=st.slider('Seuil RSI',20,40,30)
            else: threshold=None
            if st.button('Ajouter l’alerte',use_container_width=True):
                create_alert(user['id'],symbol,preset,rt,threshold); st.success('Alerte enregistrée.'); st.rerun()
        st.caption('Les emails automatiques nécessitent Supabase + Resend + le workflow GitHub fourni dans le projet. Une alerte indique une condition à examiner, pas une certitude de hausse.')
        alerts=list_alerts(user['id'])
        if alerts:
            for al in alerts:
                with st.container(border=True):
                    x,y=st.columns([4,1]); x.write(f"**{al['label']}** · {al['symbol']} · {al['rule_type']}")
                    x.caption(f"Seuil : {al.get('threshold') if al.get('threshold') is not None else 'automatique'} · dernier email : {al.get('last_sent_at') or 'jamais'}")
                    if y.button('Supprimer',key=f"del{al['id']}"): delete_alert(user['id'],al['id']); st.rerun()
        else: st.info('Aucune alerte pour le moment.')
    st.divider(); st.caption('Vie privée : ne mets jamais de clé API ni de mot de passe directement dans le code GitHub. Utilise les Secrets Streamlit/GitHub indiqués dans le README.')
    st.stop()

with st.expander('⚙️ Marchés et paramètres', expanded=True):
    a,b=st.columns(2)
    with a:
        preset=st.selectbox('Actif',list(ASSETS)+['Autre symbole'])
        symbol=st.text_input('Ticker Yahoo Finance',value=ASSETS.get(preset,'TSLA')).strip().upper()
        period=st.selectbox('Historique',['6mo','1y','2y','5y'],index=2)
    with b:
        horizon=st.slider('Horizon (séances)',20,252,90,10)
        n=st.select_slider('Simulations',options=[500,1000,2000,4000],value=1000)
        capital=st.number_input('Capital hypothétique (devise du titre)',min_value=100.,max_value=1e8,value=1000.,step=100.)
    if st.button('Actualiser les cours',use_container_width=True): st.cache_data.clear(); st.rerun()

if not symbol or len(symbol)>24: st.error('Ticker invalide.'); st.stop()
try:
    with st.spinner('Récupération des données…'): df=prices(symbol,period)
except Exception as e: st.error(f'Impossible de charger {symbol}. ({type(e).__name__})'); st.stop()
if len(df)<65: st.error('Pas assez de données pour cet actif. Choisis un historique plus long.'); st.stop()

m=indicators(df); close=m['close']; last=float(close.iloc[-1]); change=(last/float(close.iloc[-2])-1)*100
st.caption(f"{symbol} · Dernière séance : {pd.Timestamp(close.index[-1]).strftime('%d/%m/%Y')} · devise native de l’actif")

tabs=st.tabs(['Marché','Risque','Scénarios','Comparer'])
with tabs[0]:
    c1,c2=st.columns(2); c1.metric('Dernier cours',f'{last:,.2f}',f'{change:+.2f}% / séance'); c2.metric('RSI (14)',f"{m['rsi']:.1f}")
    label = 'Haussier' if m['trend_score']>=65 else 'Baissier' if m['trend_score']<=35 else 'Neutre'
    st.markdown(f'<div class="av-score"><strong>Contexte de tendance : {label}</strong><br><span class="av-muted">Score {m["trend_score"]}/100 — synthèse de la position par rapport aux moyennes mobiles et du RSI, sans valeur prédictive garantie.</span></div>',unsafe_allow_html=True)
    fig=go.Figure(); fig.add_trace(go.Scatter(x=close.index,y=close.values,name='Cours',line=dict(width=2.5))); fig.add_trace(go.Scatter(x=close.index,y=m['ma20'].values,name='MM 20',line=dict(width=1.5))); fig.add_trace(go.Scatter(x=close.index,y=m['ma50'].values,name='MM 50',line=dict(width=1.5)))
    fig.update_yaxes(tickformat='.2f'); st.plotly_chart(plot_style(fig),use_container_width=True,config={'displayModeBar':False})
    trend='au-dessus' if last>float(m['ma50'].iloc[-1]) else 'en dessous'; zone='élevé' if m['rsi']>=70 else 'faible' if m['rsi']<=30 else 'intermédiaire'
    st.info(f'Le cours est {trend} de sa moyenne 50 séances. RSI {zone}. À utiliser comme contexte, pas comme ordre d’achat ou de vente.')
with tabs[1]:
    c1,c2=st.columns(2); c1.metric('Volatilité annualisée',f"{m['vol']:.1%}"); c2.metric('Pire repli historique',f"{m['dd']:.1%}")
    c3,c4=st.columns(2); c3.metric('VaR 95 % (1 séance)',f"{m['var']:.2%}"); c4.metric('CVaR 95 %',f"{m['cvar']:.2%}")
    risk='Élevé' if m['risk_score']>=65 else 'Faible à modéré' if m['risk_score']<=35 else 'Modéré'
    st.markdown(f'<div class="av-score"><strong>Risque historique : {risk}</strong><br><span class="av-muted">Score {m["risk_score"]}/100 basé sur volatilité et drawdown observés.</span></div>',unsafe_allow_html=True)
    st.caption('Le risque futur peut être supérieur au risque historique. La VaR/CVaR ne couvre pas tous les scénarios extrêmes.')
with tabs[2]:
    st.write('Simulation bootstrap des rendements journaliers historiques. Elle explore des trajectoires possibles, mais ne prédit pas les nouvelles, crises ou changements de régime.')
    rng=np.random.default_rng(42); samples=rng.choice(m['returns'].to_numpy(),size=(n,horizon),replace=True); paths=np.column_stack([np.full(n,last),last*np.cumprod(1+samples,axis=1)])
    q5,q50,q95=np.quantile(paths,[.05,.5,.95],axis=0); x=np.arange(horizon+1); fig=go.Figure(); fig.add_trace(go.Scatter(x=x,y=q95,line=dict(width=0),showlegend=False,hoverinfo='skip')); fig.add_trace(go.Scatter(x=x,y=q5,fill='tonexty',line=dict(width=0),name='P5–P95')); fig.add_trace(go.Scatter(x=x,y=q50,line=dict(width=2),name='Médiane')); st.plotly_chart(plot_style(fig),use_container_width=True,config={'displayModeBar':False})
    finals=paths[:,-1]; amounts=np.quantile(finals/last*capital,[.05,.5,.95]); c1,c2,c3=st.columns(3)
    for c,label0,val in zip((c1,c2,c3),('Défavorable P5','Médian P50','Favorable P95'),amounts): c.metric(label0,f'{val:,.0f}')
    st.warning(f"Dans ce modèle, {np.mean(finals>last):.1%} des trajectoires finissent au-dessus du cours actuel. Ce pourcentage dépend entièrement des hypothèses du modèle.")
with tabs[3]:
    selected=st.multiselect('Choisir jusqu’à 5 actifs',list(ASSETS),default=['MSCI World · URTH','S&P 500 · SPY','Or · GLD'],max_selections=5)
    if st.button('Comparer',use_container_width=True):
        rows=[]; curves={}
        for name in selected:
            try:
                d=prices(ASSETS[name],'1y')
                if len(d)<65: continue
                z=indicators(d); s=z['close']; rows.append({'Actif':name,'Perf. 1 an':f'{(s.iloc[-1]/s.iloc[0]-1):+.1%}','Volatilité':f"{z['vol']:.1%}",'Repli max':f"{z['dd']:.1%}",'Tendance':z['trend_score']}); curves[name]=s/s.iloc[0]*100
            except Exception: pass
        if rows:
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True); aligned=pd.concat(curves,axis=1).dropna(); fig=go.Figure();
            for name in aligned: fig.add_trace(go.Scatter(x=aligned.index,y=aligned[name],name=name))
            st.plotly_chart(plot_style(fig),use_container_width=True,config={'displayModeBar':False})

st.divider(); st.caption('Données : Yahoo Finance via yfinance, potentiellement différées. Aucun ordre n’est exécuté. Les scores, simulations et alertes sont des outils d’analyse éducatifs, pas des recommandations personnalisées.')
