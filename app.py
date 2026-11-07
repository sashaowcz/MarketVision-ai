import html
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from angelvision_core import (
    ASSETS, authenticate_user, create_alert, create_user, delete_alert,
    download_prices, indicators, list_alerts, production_storage_enabled,
    search_assets, send_email, create_market_proposal, list_market_proposals,
    toggle_market_like, delete_market_proposal, market_strip_snapshot,
)

RED = '#C62828'
RED_DARK = '#8E1B1B'
RED_LIGHT = '#FFF1F1'
INK = '#171717'
MUTED = '#686868'
GRID = '#EFE8E8'

st.set_page_config(page_title='AngelVision AI', page_icon='A', layout='wide', initial_sidebar_state='collapsed')
st.markdown(f'''<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>
:root{{--av-red:{RED};--av-red-dark:{RED_DARK};--av-red-light:{RED_LIGHT};--av-ink:{INK}}}
html,body,[class*="css"]{{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Arial,sans-serif!important;background:#fff;color:var(--av-ink)}}
.block-container{{max-width:1120px;padding-top:.85rem;padding-bottom:5rem}}
h1,h2,h3{{letter-spacing:-.03em;font-weight:680!important;color:var(--av-ink)!important}}
.av-hero{{padding:.25rem 0 1rem;border-bottom:1px solid #f0e6e6;margin-bottom:.65rem}}
.av-brand{{display:flex;align-items:center;gap:.7rem}}
.av-logo{{width:42px;height:42px;border-radius:13px;background:var(--av-red);display:grid;place-items:center;color:#fff;font-weight:850;font-size:1.35rem;box-shadow:0 8px 22px rgba(198,40,40,.18)}}
.av-name{{font-size:2rem;font-weight:760;letter-spacing:-.045em}}
.av-kicker{{font-size:.76rem;letter-spacing:.12em;text-transform:uppercase;color:var(--av-red);font-weight:700;margin-bottom:.2rem}}
.av-sub{{color:{MUTED};font-size:.95rem;line-height:1.5;margin-top:.5rem}}
[data-testid="stMetric"]{{background:#fff;border:1px solid #eadede;border-radius:18px;padding:14px;min-width:0;box-shadow:0 3px 16px rgba(60,20,20,.035)}}
[data-testid="stMetricLabel"]{{color:#716767!important;font-size:.82rem}}[data-testid="stMetricValue"]{{color:var(--av-ink)!important;font-weight:700!important;font-size:clamp(1.25rem,3vw,2rem)}}
div[data-baseweb="tab-list"]{{gap:.15rem;overflow-x:auto;white-space:nowrap;border-bottom:1px solid #f0e6e6}}
button[data-baseweb="tab"]{{padding:.55rem .72rem!important}}
button[data-baseweb="tab"][aria-selected="true"]{{color:var(--av-red)!important}}
.stButton>button,.stFormSubmitButton>button{{border-radius:14px!important;min-height:44px!important;border-color:#e6d2d2!important}}
.stButton>button:hover,.stFormSubmitButton>button:hover{{border-color:var(--av-red)!important;color:var(--av-red)!important}}
.stTextInput input,.stNumberInput input{{border-radius:12px!important}}
.av-score{{border:1px solid #eadede;border-left:5px solid var(--av-red);border-radius:18px;padding:15px 16px;background:#fff;margin:.25rem 0 .8rem}}
.av-score strong{{font-size:1.1rem}}.av-muted{{color:#706666;font-size:.88rem;line-height:1.45}}
.av-status{{background:var(--av-red-light);border:1px solid #f3cece;border-radius:14px;padding:12px 14px;color:#6e2323}}
.av-search-card{{border:1px solid #eadede;border-radius:16px;padding:12px 14px;background:#fff}}
.av-post{{border:1px solid #eadede;border-radius:18px;padding:14px 15px;background:#fff;margin:.55rem 0;box-shadow:0 3px 14px rgba(60,20,20,.025)}}
.av-post-head{{display:flex;justify-content:space-between;gap:.5rem;align-items:center;margin-bottom:.45rem}}
.av-post-user{{font-weight:720}} .av-post-time{{font-size:.76rem;color:#8a7d7d}}
.av-post-body{{font-size:.97rem;line-height:1.5;white-space:pre-wrap;word-break:break-word}}
.av-share{{margin-top:.7rem;border-left:4px solid var(--av-red);background:#fff7f7;border-radius:12px;padding:10px 12px}}
.av-share-title{{font-weight:700}} .av-share-meta{{color:#6d5d5d;font-size:.82rem;margin-top:.15rem}}
.av-ticker-wrap{{overflow:hidden;border-bottom:1px solid #f0e6e6;background:#fff;padding:.38rem 0;margin:-.2rem 0 .55rem}}
.av-ticker-track{{display:flex;width:max-content;gap:1.4rem;animation:avTicker 34s linear infinite;will-change:transform}}
.av-ticker-item{{white-space:nowrap;font-size:.78rem;font-weight:650;color:#3c3434}}
.av-ticker-pos{{color:#147a54}}.av-ticker-neg{{color:var(--av-red)}}
@keyframes avTicker{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}
.av-market-card{{border:1px solid #eadede;border-radius:18px;padding:14px 15px;background:#fff;margin:.55rem 0;box-shadow:0 3px 14px rgba(60,20,20,.025)}}
.av-market-head{{display:flex;justify-content:space-between;gap:.75rem;align-items:flex-start}}
.av-market-title{{font-weight:760;font-size:1rem}}.av-market-meta{{font-size:.8rem;color:#7b6d6d;margin-top:.18rem}}
.av-period-pill{{display:inline-block;border:1px solid #efd6d6;background:#fff7f7;color:#8a2323;border-radius:999px;padding:.22rem .55rem;font-size:.76rem;font-weight:700}}
.av-perf{{font-size:1.35rem;font-weight:780;letter-spacing:-.03em;margin-top:.45rem}}
[data-testid="stAlert"]{{border-radius:14px!important}}
hr{{border-color:#f0e6e6!important}}
@media(max-width:650px){{.block-container{{padding:.65rem .65rem 5.4rem}}.av-logo{{width:38px;height:38px;border-radius:12px}}.av-name{{font-size:1.65rem}}h1{{font-size:1.7rem!important}}h2{{font-size:1.3rem!important}}h3{{font-size:1.08rem!important}}[data-testid="stHorizontalBlock"]{{gap:.42rem}}[data-testid="stMetric"]{{padding:11px}}[data-testid="stMetricValue"]{{font-size:1.35rem}}div[data-testid="stPlotlyChart"]{{max-width:100%;overflow:hidden}}.av-sub{{font-size:.9rem}}}}
</style>''', unsafe_allow_html=True)

@st.cache_data(ttl=300, show_spinner=False)
def prices(symbol, period):
    return download_prices(symbol, period)

@st.cache_data(ttl=900, show_spinner=False)
def asset_search(query):
    return search_assets(query, 12)

@st.cache_data(ttl=300, show_spinner=False)
def ticker_strip():
    return market_strip_snapshot()

@st.cache_data(ttl=300, show_spinner=False)
def proposal_performance(symbol, period):
    sessions = {'1d': 1, '1w': 5, '1mo': 21, '6mo': 126, '1y': 252}
    fetch = {'1d': '5d', '1w': '1mo', '1mo': '3mo', '6mo': '1y', '1y': '2y'}
    d = prices(symbol, fetch[period])
    if len(d) < 2:
        return None, None
    close = d['Close'].astype(float)
    n = sessions[period]
    ref = float(close.iloc[max(0, len(close)-1-n)])
    last = float(close.iloc[-1])
    return last, (last/ref-1)*100 if ref else None

def plot_style(fig, height=340, rangeslider=False):
    fig.update_layout(
        template='plotly_white', height=height, margin=dict(l=8,r=8,t=18,b=34),
        legend=dict(orientation='h',y=-.23,x=0,font=dict(size=10)), hovermode='x unified',
        dragmode='pan', font=dict(size=11,family='Helvetica Neue, Arial',color=INK),
        xaxis=dict(automargin=True,gridcolor=GRID,showgrid=False,rangeslider=dict(visible=rangeslider,thickness=.055)),
        yaxis=dict(automargin=True,gridcolor=GRID), paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF',
        modebar=dict(bgcolor='rgba(255,255,255,.90)',color='#6a5b5b',activecolor=RED),
    )
    return fig

PLOT_CONFIG = {
    'displayModeBar': True,
    'displaylogo': False,
    'scrollZoom': True,
    'doubleClick': 'reset',
    'modeBarButtonsToRemove': ['select2d','lasso2d','toImage'],
    'modeBarButtonsToAdd': [],
    'responsive': True,
}

def choose_symbol(prefix, default_label='MSCI World · URTH'):
    preset = st.selectbox('Sélection rapide', list(ASSETS)+['Rechercher un autre actif'], key=f'{prefix}_preset', index=list(ASSETS).index(default_label) if default_label in ASSETS else 0)
    if preset != 'Rechercher un autre actif':
        return ASSETS[preset], preset
    query = st.text_input('Rechercher une action, ETF, indice, crypto, devise ou matière première', key=f'{prefix}_query', placeholder='Ex. LVMH, Tesla, SMI, Bitcoin, gold…')
    if st.button('Rechercher', key=f'{prefix}_search', use_container_width=True) and query.strip():
        st.session_state[f'{prefix}_results'] = asset_search(query)
    results = st.session_state.get(f'{prefix}_results', [])
    if results:
        options = {r['label']: r for r in results}
        chosen = st.selectbox('Résultats', list(options), key=f'{prefix}_result_choice')
        r = options[chosen]
        return r['symbol'], r['name']
    manual = st.text_input('Ou entrer directement un ticker Yahoo Finance', value='AAPL', key=f'{prefix}_manual').strip().upper()
    return manual, manual

if 'user' not in st.session_state: st.session_state.user = None

strip = ticker_strip()
if strip:
    parts=[]
    for item in strip:
        cls='av-ticker-pos' if item['change'] >= 0 else 'av-ticker-neg'
        arrow='▲' if item['change'] >= 0 else '▼'
        parts.append(f'<span class="av-ticker-item"><b>{html.escape(item["label"])}</b> {item["price"]:,.2f} <span class="{cls}">{arrow} {item["change"]:+.2f}%</span></span>')
    content=''.join(parts)
    st.markdown(f'<div class="av-ticker-wrap"><div class="av-ticker-track">{content}{content}</div></div>', unsafe_allow_html=True)

# En-tête mobile : identité à gauche, compte à droite, directement sous la banderole.
if 'active_page' not in st.session_state:
    st.session_state.active_page = 'Marchés'

head_left, head_right = st.columns([3.2, 1.15], vertical_alignment='center')
with head_left:
    st.markdown('''<div class="av-apphead"><div class="av-brand"><div class="av-logo">A</div><div><div class="av-kicker">Marchés • Risque • Tendances • Alertes</div><div class="av-name">AngelVision</div></div></div></div>''', unsafe_allow_html=True)
with head_right:
    account_text = (st.session_state.user.get('display_name') or 'Compte') if st.session_state.user else 'Compte'
    if st.button(account_text, key='top_account_btn', use_container_width=True):
        st.session_state.active_page = 'Compte & alertes'
        st.rerun()

st.markdown('<div class="av-sub">Une lecture claire des marchés, pensée pour iPhone. Blanc pour la lisibilité, rouge AngelVision pour les actions et les signaux à examiner.</div><div style="height:.35rem;border-bottom:1px solid #f0e6e6;margin-bottom:.45rem"></div>', unsafe_allow_html=True)

if st.session_state.active_page == 'Compte & alertes':
    page = 'Compte & alertes'
    if st.button('← Retour aux marchés', key='back_from_account'):
        st.session_state.active_page = 'Marchés'
        st.rerun()
else:
    nav_default = 1 if st.session_state.active_page == 'Communauté' else 0
    page = st.radio('Navigation', ['Marchés','Communauté'], horizontal=True, label_visibility='collapsed', index=nav_default, key='main_nav')
    st.session_state.active_page = page

if page == 'Communauté':
    st.subheader('Marchés de la communauté')
    st.caption('Ici, pas de posts texte : la communauté propose uniquement des marchés à regarder sur une période précise. Tu peux liker si tu as un compte.')

    period_labels = {'1d':'1 jour','1w':'1 semaine','1mo':'1 mois','6mo':'6 mois','1y':'1 an'}
    if st.session_state.user:
        with st.container(border=True):
            st.markdown('### Proposer un marché')
            prop_symbol, prop_label = choose_symbol('proposal', 'MSCI World · URTH')
            prop_period = st.radio('Période', ['1d','1w','1mo','6mo','1y'], horizontal=True, format_func=lambda x: period_labels[x], key='proposal_period')
            destination = st.radio('Partager', ['Au public','À un ami'], horizontal=True, key='proposal_scope')
            friend_name = ''
            if destination == 'À un ami':
                friend_name = st.text_input('Pseudonyme de l’ami', placeholder='Ex. Sasha', key='proposal_friend')
            if st.button('Proposer ce marché', type='primary', use_container_width=True, key='proposal_submit'):
                try:
                    create_market_proposal(st.session_state.user['id'], prop_symbol, prop_label, prop_period, 'public' if destination=='Au public' else 'friend', friend_name)
                    st.success('Marché proposé.')
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    else:
        st.markdown('<div class="av-status"><b>Connecte-toi pour liker ou proposer un marché.</b><br><span class="av-muted">Le fil public reste visible sans compte.</span></div>', unsafe_allow_html=True)

    viewer_id = st.session_state.user['id'] if st.session_state.user else None
    proposals = list_market_proposals(viewer_id, 120)
    if not proposals:
        st.info('Aucun marché proposé pour le moment.')
    for prop in proposals:
        try:
            last_prop, perf = proposal_performance(prop['symbol'], prop['period'])
        except Exception:
            last_prop, perf = None, None
        scope_text = 'Public' if prop.get('scope') == 'public' else 'Partagé en privé'
        who = html.escape(str(prop.get('display_name') or 'Utilisateur'))
        label_safe = html.escape(str(prop.get('label') or prop.get('symbol')))
        sym_safe = html.escape(str(prop.get('symbol') or ''))
        perf_html = 'Données indisponibles' if perf is None else f'{perf:+.2f}% sur {period_labels[prop["period"]]}'
        perf_class = 'av-ticker-pos' if (perf or 0) >= 0 else 'av-ticker-neg'
        st.markdown(f'''<div class="av-market-card"><div class="av-market-head"><div><div class="av-market-title">{label_safe}</div><div class="av-market-meta">{sym_safe} · proposé par @{who} · {scope_text}</div></div><span class="av-period-pill">{period_labels[prop['period']]}</span></div><div class="av-perf {perf_class}">{perf_html}</div></div>''', unsafe_allow_html=True)
        likes = int(prop.get('like_count') or 0)
        user = st.session_state.user
        if user:
            liked = user['id'] in (prop.get('like_user_ids') or [])
            c1,c2 = st.columns([1.2,3])
            if c1.button(('♥' if liked else '♡') + f' {likes}', key=f'market_like_{prop["id"]}', use_container_width=True):
                toggle_market_like(user['id'], prop['id'])
                st.rerun()
            if prop.get('user_id') == user['id'] and c2.button('Retirer ma proposition', key=f'market_del_{prop["id"]}'):
                delete_market_proposal(user['id'], prop['id'])
                st.rerun()
        else:
            st.caption(f'♡ {likes} likes')
        st.divider()
    st.stop()

if page == 'Compte & alertes':
    st.subheader('Compte AngelVision')
    mode = st.radio('Mode', ['Se connecter','Créer un compte'], horizontal=True)
    if not st.session_state.user:
        with st.form('auth'):
            display_name = st.text_input('Pseudonyme', placeholder='Ex. Sasha') if mode=='Créer un compte' else ''
            email = st.text_input('Email', placeholder='nom@exemple.com')
            password = st.text_input('Mot de passe', type='password')
            submit = st.form_submit_button('Créer le compte' if mode=='Créer un compte' else 'Se connecter', use_container_width=True)
        if submit:
            if '@' not in email or len(password) < 8 or (mode=='Créer un compte' and not display_name.strip()):
                st.error('Entre un pseudonyme, un email valide et un mot de passe d’au moins 8 caractères.')
            else:
                try:
                    if mode == 'Créer un compte':
                        user = create_user(email,password,display_name); st.session_state.user = user
                        ok,_ = send_email(user['email'],'Bienvenue sur AngelVision',f'<h2>Bienvenue {user.get("display_name") or ""}</h2><p>Ton compte AngelVision est créé. Les alertes indiquent des conditions de marché à examiner ; elles ne constituent pas un ordre d’achat.</p>')
                        st.success('Compte créé.' + (' Email de bienvenue envoyé.' if ok else ''))
                    else:
                        user = authenticate_user(email,password)
                        if user: st.session_state.user=user; st.success('Connexion réussie.')
                        else: st.error('Email ou mot de passe incorrect.')
                    st.rerun()
                except Exception as e: st.error(str(e))
    else:
        user = st.session_state.user
        pseudo = user.get('display_name') or 'Utilisateur'
        c1,c2=st.columns([3,1]); c1.markdown(f'<div class="av-status"><b>{pseudo}</b><br><span style="font-size:.86rem">{user["email"]}</span></div>',unsafe_allow_html=True)
        if c2.button('Déconnexion',use_container_width=True): st.session_state.user=None; st.rerun()
        if production_storage_enabled():
            st.success('Supabase est activé : comptes et alertes sont persistants.')
        else:
            st.warning('Mode démo : les comptes sont locaux et peuvent disparaître lors d’un redéploiement. Configure Supabase avant de publier l’app à d’autres utilisateurs.')

        with st.expander('Supabase — configuration depuis iPhone'):
            st.markdown('''1. Ouvre **supabase.com** dans Safari et crée un projet.  
2. Dans **SQL Editor**, colle le fichier `schema.sql` du dépôt puis appuie sur **Run**.  
3. Dans **Connect / API keys**, copie le **Project URL** et une **Secret key** (`sb_secret_...`).  
4. Dans Streamlit → **Manage app → Settings → Secrets**, ajoute `SUPABASE_URL` et `SUPABASE_SECRET_KEY`.  
5. Redémarre l’app. Le bandeau ci-dessus doit alors afficher **Supabase est activé**.  
**Ne mets jamais la secret key dans GitHub.**''')

        st.markdown('### Créer une alerte email')
        with st.container(border=True):
            symbol, asset_label = choose_symbol('alert', 'Or · GC=F')
            rule_label=st.selectbox('Condition',['Prix sous un seuil','Prix au-dessus d’un seuil','RSI faible','Reprise au-dessus de la moyenne 50 jours'])
            rule_map={'Prix sous un seuil':'price_below','Prix au-dessus d’un seuil':'price_above','RSI faible':'rsi_low','Reprise au-dessus de la moyenne 50 jours':'trend_recovery'}
            rt=rule_map[rule_label]
            if rt in ('price_below','price_above'):
                threshold=st.number_input('Seuil de prix',min_value=0.0001,value=100.0,step=1.0,format='%.4f')
            elif rt=='rsi_low':
                threshold=st.slider('Seuil RSI',20,40,30)
            else: threshold=None
            if st.button('Ajouter l’alerte',use_container_width=True,type='primary'):
                if not symbol: st.error('Choisis un actif valide.')
                else:
                    create_alert(user['id'],symbol,asset_label,rt,threshold); st.success('Alerte enregistrée.'); st.rerun()
        st.caption('La recherche Yahoo Finance permet d’ajouter des actions, ETF, indices, cryptos, devises et matières premières au-delà de la liste proposée.')
        alerts=list_alerts(user['id'])
        if alerts:
            for al in alerts:
                with st.container(border=True):
                    x,y=st.columns([4,1]); x.write(f"**{al['label']}** · `{al['symbol']}`")
                    x.caption(f"{al['rule_type']} · seuil : {al.get('threshold') if al.get('threshold') is not None else 'automatique'} · dernier email : {al.get('last_sent_at') or 'jamais'}")
                    if y.button('Supprimer',key=f"del{al['id']}"): delete_alert(user['id'],al['id']); st.rerun()
        else: st.info('Aucune alerte pour le moment.')
    st.divider(); st.caption('Les clés API et secrets doivent rester dans Streamlit/GitHub Secrets. AngelVision ne doit jamais les afficher côté utilisateur.')
    st.stop()

with st.expander('Marché et paramètres', expanded=True):
    a,b=st.columns(2)
    with a:
        symbol, asset_label = choose_symbol('market', 'MSCI World · URTH')
        period=st.selectbox('Historique',['6mo','1y','2y','5y'],index=2)
    with b:
        horizon=st.slider('Horizon (séances)',20,252,90,10)
        n=st.select_slider('Simulations',options=[500,1000,2000,4000],value=1000)
        capital=st.number_input('Capital hypothétique (devise du titre)',min_value=100.,max_value=1e8,value=1000.,step=100.)
    if st.button('Actualiser les cours',use_container_width=True): st.cache_data.clear(); st.rerun()

if not symbol or len(symbol)>32: st.error('Ticker invalide.'); st.stop()
try:
    with st.spinner('Récupération des données…'): df=prices(symbol,period)
except Exception as e: st.error(f'Impossible de charger {symbol}. ({type(e).__name__})'); st.stop()
if len(df)<65: st.error('Pas assez de données pour cet actif. Choisis un historique plus long.'); st.stop()

m=indicators(df); close=m['close']; last=float(close.iloc[-1]); change=(last/float(close.iloc[-2])-1)*100
st.caption(f"{asset_label} · {symbol} · Dernière séance : {pd.Timestamp(close.index[-1]).strftime('%d/%m/%Y')} · devise native de l’actif")

tabs=st.tabs(['Marché','Risque','Scénarios','Comparer'])
with tabs[0]:
    c1,c2=st.columns(2); c1.metric('Dernier cours',f'{last:,.2f}',f'{change:+.2f}% / séance'); c2.metric('RSI (14)',f"{m['rsi']:.1f}")
    label = 'Haussier' if m['trend_score']>=65 else 'Baissier' if m['trend_score']<=35 else 'Neutre'
    st.markdown(f'<div class="av-score"><strong>Contexte de tendance : {label}</strong><br><span class="av-muted">Score {m["trend_score"]}/100 — position par rapport aux moyennes mobiles et au RSI, sans valeur prédictive garantie.</span></div>',unsafe_allow_html=True)
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=close.index,y=close.values,name='Cours',line=dict(width=2.6,color=RED)))
    fig.add_trace(go.Scatter(x=close.index,y=m['ma20'].values,name='MM 20',line=dict(width=1.5,color=RED_DARK)))
    fig.add_trace(go.Scatter(x=close.index,y=m['ma50'].values,name='MM 50',line=dict(width=1.5,color='#B8AAAA')))
    fig.update_yaxes(tickformat='.2f')
    st.plotly_chart(plot_style(fig,rangeslider=True),use_container_width=True,config=PLOT_CONFIG)
    st.caption('Interaction : glisse avec un doigt pour déplacer le graphique, pince pour zoomer/dézoomer, double-tape pour réinitialiser. Les boutons − / maison de Plotly permettent aussi de dézoomer ou de revenir à la vue initiale.')
    trend='au-dessus' if last>float(m['ma50'].iloc[-1]) else 'en dessous'; zone='élevé' if m['rsi']>=70 else 'faible' if m['rsi']<=30 else 'intermédiaire'
    st.markdown(f'<div class="av-status">Le cours est <b>{trend}</b> de sa moyenne 50 séances. RSI {zone}. À utiliser comme contexte, pas comme ordre d’achat ou de vente.</div>', unsafe_allow_html=True)
with tabs[1]:
    c1,c2=st.columns(2); c1.metric('Volatilité annualisée',f"{m['vol']:.1%}"); c2.metric('Pire repli historique',f"{m['dd']:.1%}")
    c3,c4=st.columns(2); c3.metric('VaR 95 % (1 séance)',f"{m['var']:.2%}"); c4.metric('CVaR 95 %',f"{m['cvar']:.2%}")
    risk='Élevé' if m['risk_score']>=65 else 'Faible à modéré' if m['risk_score']<=35 else 'Modéré'
    st.markdown(f'<div class="av-score"><strong>Risque historique : {risk}</strong><br><span class="av-muted">Score {m["risk_score"]}/100 basé sur volatilité et drawdown observés.</span></div>',unsafe_allow_html=True)
    st.caption('Le risque futur peut être supérieur au risque historique. La VaR/CVaR ne couvre pas tous les scénarios extrêmes.')
with tabs[2]:
    st.write('Simulation bootstrap des rendements journaliers historiques. Elle explore des trajectoires possibles, mais ne prédit pas les nouvelles, crises ou changements de régime.')
    rng=np.random.default_rng(42); samples=rng.choice(m['returns'].to_numpy(),size=(n,horizon),replace=True); paths=np.column_stack([np.full(n,last),last*np.cumprod(1+samples,axis=1)])
    q5,q50,q95=np.quantile(paths,[.05,.5,.95],axis=0); x=np.arange(horizon+1)
    fig=go.Figure(); fig.add_trace(go.Scatter(x=x,y=q95,line=dict(width=0),showlegend=False,hoverinfo='skip')); fig.add_trace(go.Scatter(x=x,y=q5,fill='tonexty',fillcolor='rgba(198,40,40,.10)',line=dict(width=0),name='P5–P95')); fig.add_trace(go.Scatter(x=x,y=q50,line=dict(width=2,color=RED),name='Médiane'))
    st.plotly_chart(plot_style(fig),use_container_width=True,config=PLOT_CONFIG)
    finals=paths[:,-1]; amounts=np.quantile(finals/last*capital,[.05,.5,.95]); c1,c2,c3=st.columns(3)
    for c,label0,val in zip((c1,c2,c3),('Défavorable P5','Médian P50','Favorable P95'),amounts): c.metric(label0,f'{val:,.0f}')
    st.warning(f"Dans ce modèle, {np.mean(finals>last):.1%} des trajectoires finissent au-dessus du cours actuel. Ce pourcentage dépend entièrement des hypothèses du modèle.")
with tabs[3]:
    selected=st.multiselect('Choisir jusqu’à 5 actifs',list(ASSETS),default=['MSCI World · URTH','S&P 500 · SPY','Or · GC=F'],max_selections=5)
    if st.button('Comparer',use_container_width=True):
        rows=[]; curves={}
        for name in selected:
            try:
                d=prices(ASSETS[name],'1y')
                if len(d)<65: continue
                z=indicators(d); s=z['close']; rows.append({'Actif':name,'Perf. 1 an':f'{(s.iloc[-1]/s.iloc[0]-1):+.1%}','Volatilité':f"{z['vol']:.1%}",'Repli max':f"{z['dd']:.1%}",'Tendance':z['trend_score']}); curves[name]=s/s.iloc[0]*100
            except Exception: pass
        if rows:
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True); aligned=pd.concat(curves,axis=1).dropna(); fig=go.Figure()
            shades=[RED,RED_DARK,'#9E7B7B','#6D5959','#C97A7A']
            for i,name in enumerate(aligned): fig.add_trace(go.Scatter(x=aligned.index,y=aligned[name],name=name,line=dict(color=shades[i%len(shades)])))
            st.plotly_chart(plot_style(fig,rangeslider=True),use_container_width=True,config=PLOT_CONFIG)

st.divider(); st.caption('Données : Yahoo Finance via yfinance, potentiellement différées. Aucun ordre n’est exécuté. Les scores, simulations et alertes sont des outils d’analyse éducatifs, pas des recommandations personnalisées.')
