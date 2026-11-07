import html
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from angelvision_core import (
    ASSETS, authenticate_user, create_alert, create_user, delete_alert,
    download_prices, indicators, list_alerts, production_storage_enabled,
    search_assets, send_email, create_post, list_posts, toggle_like, delete_post,
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

def plot_style(fig, height=340, rangeslider=False):
    fig.update_layout(
        template='plotly_white', height=height, margin=dict(l=8,r=8,t=18,b=34),
        legend=dict(orientation='h',y=-.23,x=0,font=dict(size=10)), hovermode='x unified',
        dragmode='pan', font=dict(size=11,family='Helvetica Neue, Arial',color=INK),
        xaxis=dict(automargin=True,gridcolor=GRID,showgrid=False,rangeslider=dict(visible=rangeslider,thickness=.08)),
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

st.markdown('''<div class="av-hero"><div class="av-kicker">Marchés • Risque • Communauté • Alertes</div><div class="av-brand"><div class="av-logo">A</div><div class="av-name">AngelVision</div></div><div class="av-sub">Une lecture claire des marchés, pensée pour iPhone. Blanc pour la lisibilité, rouge AngelVision pour les actions et les signaux à examiner.</div></div>''', unsafe_allow_html=True)
page = st.radio('Navigation', ['Marchés','Communauté','Compte & alertes'], horizontal=True, label_visibility='collapsed')

if page == 'Communauté':
    st.subheader('Communauté AngelVision')
    st.caption('Un fil texte uniquement. Pas d’images ni de fichiers : tu peux écrire librement et joindre seulement des données générées dans AngelVision.')

    if st.session_state.user:
        with st.container(border=True):
            st.markdown('### Publier')
            body = st.text_area('Ton message', max_chars=500, placeholder='Partage une idée, une question ou ton analyse…', key='community_body')
            attach_mode = st.radio('Ajouter', ['Texte uniquement','Un actif AngelVision'], horizontal=True, key='community_attach')
            shared = None
            if attach_mode == 'Un actif AngelVision':
                share_symbol, share_label = choose_symbol('community_share', 'MSCI World · URTH')
                if share_symbol:
                    try:
                        share_df = prices(share_symbol, '6mo')
                        if len(share_df) >= 65:
                            share_m = indicators(share_df)
                            share_price = float(share_m['close'].iloc[-1])
                            shared = {'symbol': share_symbol, 'label': share_label, 'price': share_price,
                                      'trend_score': share_m['trend_score'], 'risk_score': share_m['risk_score']}
                            st.markdown(f'<div class="av-share"><div class="av-share-title">{html.escape(str(share_label))} · {html.escape(str(share_symbol))}</div><div class="av-share-meta">Cours {share_price:,.2f} · Tendance {share_m["trend_score"]}/100 · Risque {share_m["risk_score"]}/100</div></div>', unsafe_allow_html=True)
                        else:
                            st.warning('Pas assez de données pour créer la fiche de cet actif.')
                    except Exception:
                        st.warning('Impossible de charger cet actif pour le moment.')
            if st.button('Publier', type='primary', use_container_width=True, key='publish_post'):
                try:
                    create_post(st.session_state.user['id'], body, shared=shared)
                    st.session_state.community_body = ''
                    st.success('Publication envoyée.')
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    else:
        st.info('Connecte-toi dans « Compte & alertes » pour publier, répondre ou aimer. Le fil reste lisible sans compte.')

    posts = list_posts(120)
    top = [p for p in posts if not p.get('parent_id')]
    replies_by_parent = {}
    for p0 in posts:
        if p0.get('parent_id'):
            replies_by_parent.setdefault(p0['parent_id'], []).append(p0)

    if not top:
        st.info('Aucune publication pour le moment. Sois le premier à lancer une discussion.')
    for post in top:
        name = html.escape(str(post.get('display_name') or 'Utilisateur'))
        body_safe = html.escape(str(post.get('body') or ''))
        when = html.escape(str(post.get('created_at') or '').replace('T',' ')[:16])
        st.markdown(f'<div class="av-post"><div class="av-post-head"><span class="av-post-user">@{name}</span><span class="av-post-time">{when}</span></div><div class="av-post-body">{body_safe}</div>', unsafe_allow_html=True)
        if post.get('shared_symbol'):
            lbl = html.escape(str(post.get('shared_label') or post.get('shared_symbol')))
            sym = html.escape(str(post.get('shared_symbol')))
            price = post.get('shared_price'); trend = post.get('shared_trend'); risk = post.get('shared_risk')
            meta=[]
            if price is not None: meta.append(f'Cours {float(price):,.2f}')
            if trend is not None: meta.append(f'Tendance {int(trend)}/100')
            if risk is not None: meta.append(f'Risque {int(risk)}/100')
            st.markdown(f'<div class="av-share"><div class="av-share-title">{lbl} · {sym}</div><div class="av-share-meta">{" · ".join(meta)}</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        user = st.session_state.user
        likes = int(post.get('like_count') or 0)
        if user:
            liked = user['id'] in (post.get('like_user_ids') or [])
            c1,c2,c3 = st.columns([1.25,1.35,3])
            if c1.button(('♥' if liked else '♡') + f' {likes}', key=f'like_{post["id"]}', use_container_width=True):
                toggle_like(user['id'], post['id']); st.rerun()
            with c2.popover('Répondre', use_container_width=True):
                with st.form(f'reply_form_{post["id"]}'):
                    reply = st.text_area('Réponse', max_chars=500, key=f'reply_{post["id"]}', label_visibility='collapsed', placeholder='Écrire une réponse…')
                    if st.form_submit_button('Envoyer', use_container_width=True):
                        create_post(user['id'], reply, parent_id=post['id']); st.rerun()
            if post.get('user_id') == user['id'] and c3.button('Supprimer', key=f'delpost_{post["id"]}'):
                delete_post(user['id'], post['id']); st.rerun()
        else:
            st.caption(f'♡ {likes}')

        replies = list(reversed(replies_by_parent.get(post['id'], [])))
        for rep in replies:
            rname = html.escape(str(rep.get('display_name') or 'Utilisateur'))
            rbody = html.escape(str(rep.get('body') or ''))
            st.markdown(f'<div style="margin-left:1rem;border-left:2px solid #f0dede;padding:.35rem 0 .35rem .8rem"><b>@{rname}</b><br><span style="white-space:pre-wrap">{rbody}</span></div>', unsafe_allow_html=True)
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
