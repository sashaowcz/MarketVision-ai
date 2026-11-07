import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
import yfinance as yf

DB_PATH = Path(os.getenv('ANGELVISION_DB_PATH', 'angelvision.db'))

ASSETS = {
    'MSCI World · URTH': 'URTH',
    'S&P 500 · SPY': 'SPY',
    'Nasdaq 100 · QQQ': 'QQQ',
    'SMI suisse · ^SSMI': '^SSMI',
    'Nestlé · NESN.SW': 'NESN.SW',
    'Apple · AAPL': 'AAPL',
    'Microsoft · MSFT': 'MSFT',
    'Nvidia · NVDA': 'NVDA',
    'Tesla · TSLA': 'TSLA',
    'Bitcoin · BTC-USD': 'BTC-USD',
    'Ethereum · ETH-USD': 'ETH-USD',
    'Or · GC=F': 'GC=F',
    'Or ETF · GLD': 'GLD',
    'Pétrole WTI · CL=F': 'CL=F',
    'EUR/CHF · EURCHF=X': 'EURCHF=X',
    'USD/CHF · CHF=X': 'CHF=X',
    'Obligations US · AGG': 'AGG',
}


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt_bytes = secrets.token_bytes(16)
    else:
        salt_bytes = base64.b64decode(salt.encode())
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt_bytes, 210_000)
    return f"{base64.b64encode(salt_bytes).decode()}:{base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split(':', 1)
        candidate = hash_password(password, salt).split(':', 1)[1]
        return hmac.compare_digest(candidate, expected)
    except Exception:
        return False


def init_local_db() -> None:
    con = sqlite3.connect(DB_PATH)
    con.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        display_name TEXT,
        explanation_level TEXT NOT NULL DEFAULT 'standard',
        created_at TEXT NOT NULL
    )''')
    cols = {row[1] for row in con.execute('PRAGMA table_info(users)').fetchall()}
    if 'display_name' not in cols:
        con.execute('ALTER TABLE users ADD COLUMN display_name TEXT')
    if 'explanation_level' not in cols:
        con.execute("ALTER TABLE users ADD COLUMN explanation_level TEXT NOT NULL DEFAULT 'standard'")
    con.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        label TEXT NOT NULL,
        rule_type TEXT NOT NULL,
        threshold REAL,
        enabled INTEGER NOT NULL DEFAULT 1,
        last_sent_at TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    con.execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        parent_id INTEGER,
        body TEXT NOT NULL,
        shared_symbol TEXT, shared_label TEXT, shared_price REAL,
        shared_trend INTEGER, shared_risk INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(parent_id) REFERENCES posts(id)
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS post_likes (
        post_id INTEGER NOT NULL, user_id INTEGER NOT NULL, created_at TEXT NOT NULL,
        PRIMARY KEY(post_id,user_id),
        FOREIGN KEY(post_id) REFERENCES posts(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS market_proposals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        label TEXT NOT NULL,
        period TEXT NOT NULL,
        scope TEXT NOT NULL DEFAULT 'public',
        target_user_id INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(target_user_id) REFERENCES users(id)
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS market_likes (
        proposal_id INTEGER NOT NULL, user_id INTEGER NOT NULL, created_at TEXT NOT NULL,
        PRIMARY KEY(proposal_id,user_id),
        FOREIGN KEY(proposal_id) REFERENCES market_proposals(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS paper_accounts (
        user_id INTEGER PRIMARY KEY,
        initial_cash_chf REAL NOT NULL,
        cash_chf REAL NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS paper_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        label TEXT NOT NULL,
        side TEXT NOT NULL,
        quantity REAL NOT NULL,
        price_native REAL NOT NULL,
        currency TEXT NOT NULL,
        fx_to_chf REAL NOT NULL,
        price_chf REAL NOT NULL,
        total_chf REAL NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    con.commit(); con.close()


def _supabase_cfg() -> tuple[str | None, str | None]:
    url = os.getenv('SUPABASE_URL')
    # New Supabase server-side key first; legacy service-role remains supported as fallback.
    key = os.getenv('SUPABASE_SECRET_KEY') or os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    return url, key


def production_storage_enabled() -> bool:
    url, key = _supabase_cfg()
    return bool(url and key)


def _sb_headers(prefer: str | None = None) -> dict[str, str]:
    _, key = _supabase_cfg()
    h = {'apikey': key or '', 'Authorization': f'Bearer {key or ""}', 'Content-Type': 'application/json'}
    if prefer:
        h['Prefer'] = prefer
    return h


def _sb(table: str, method: str = 'GET', params: dict | None = None, payload: Any = None, prefer: str | None = None):
    url, _ = _supabase_cfg()
    if not url:
        raise RuntimeError('Supabase non configuré')
    r = requests.request(method, f"{url.rstrip('/')}/rest/v1/{table}", headers=_sb_headers(prefer), params=params, json=payload, timeout=20)
    if r.status_code >= 300:
        raise RuntimeError(f"Supabase {r.status_code}: {r.text[:300]}")
    if not r.text:
        return None
    return r.json()


def create_user(email: str, password: str, display_name: str) -> dict:
    email = email.strip().lower()
    display_name = (display_name or '').strip()[:40]
    if not display_name:
        raise ValueError('Choisis un pseudonyme.')
    if production_storage_enabled():
        existing = _sb('users', params={'email': f'eq.{email}', 'select': 'id'})
        if existing:
            raise ValueError('Un compte existe déjà avec cet email.')
        rows = _sb('users', 'POST', payload={'email': email, 'password_hash': hash_password(password), 'display_name': display_name, 'explanation_level': 'standard', 'created_at': utcnow_iso()}, prefer='return=representation')
        return rows[0]
    init_local_db(); con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    try:
        cur = con.execute('INSERT INTO users(email,password_hash,display_name,explanation_level,created_at) VALUES(?,?,?,?,?)', (email, hash_password(password), display_name, 'standard', utcnow_iso()))
        con.commit(); row = con.execute('SELECT id,email,display_name,explanation_level,created_at FROM users WHERE id=?', (cur.lastrowid,)).fetchone(); return dict(row)
    except sqlite3.IntegrityError:
        raise ValueError('Un compte existe déjà avec cet email.')
    finally:
        con.close()


def authenticate_user(email: str, password: str) -> dict | None:
    email = email.strip().lower()
    if production_storage_enabled():
        rows = _sb('users', params={'email': f'eq.{email}', 'select': 'id,email,password_hash,display_name,explanation_level,created_at'})
        if not rows or not verify_password(password, rows[0]['password_hash']):
            return None
        return {k: rows[0].get(k) for k in ('id','email','display_name','explanation_level','created_at')}
    init_local_db(); con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    row = con.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone(); con.close()
    if row and verify_password(password, row['password_hash']):
        return {'id': row['id'], 'email': row['email'], 'display_name': row['display_name'], 'explanation_level': row['explanation_level'] if 'explanation_level' in row.keys() else 'standard', 'created_at': row['created_at']}
    return None



def update_explanation_level(user_id: int, level: str) -> None:
    level = level if level in ('beginner','standard','advanced') else 'standard'
    if production_storage_enabled():
        _sb('users', 'PATCH', params={'id': f'eq.{user_id}'}, payload={'explanation_level': level}, prefer='return=minimal')
        return
    init_local_db(); con = sqlite3.connect(DB_PATH)
    con.execute('UPDATE users SET explanation_level=? WHERE id=?', (level, user_id)); con.commit(); con.close()


def get_paper_account(user_id: int) -> dict | None:
    if production_storage_enabled():
        rows = _sb('paper_accounts', params={'user_id': f'eq.{user_id}', 'select': '*'}) or []
        return rows[0] if rows else None
    init_local_db(); con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    row = con.execute('SELECT * FROM paper_accounts WHERE user_id=?', (user_id,)).fetchone(); con.close()
    return dict(row) if row else None


def create_paper_account(user_id: int, initial_cash_chf: float) -> dict:
    amount = float(initial_cash_chf)
    if amount < 1000 or amount > 20000:
        raise ValueError('Le capital virtuel doit être compris entre 1 000 et 20 000 CHF.')
    if get_paper_account(user_id):
        raise ValueError('Ton portefeuille d’entraînement existe déjà.')
    row = {'user_id': user_id, 'initial_cash_chf': amount, 'cash_chf': amount, 'created_at': utcnow_iso()}
    if production_storage_enabled():
        rows = _sb('paper_accounts', 'POST', payload=row, prefer='return=representation') or []
        return rows[0]
    init_local_db(); con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    con.execute('INSERT INTO paper_accounts(user_id,initial_cash_chf,cash_chf,created_at) VALUES(?,?,?,?)', (user_id,amount,amount,row['created_at']))
    con.commit(); out = dict(con.execute('SELECT * FROM paper_accounts WHERE user_id=?',(user_id,)).fetchone()); con.close(); return out


def list_paper_trades(user_id: int) -> list[dict]:
    if production_storage_enabled():
        return _sb('paper_trades', params={'user_id': f'eq.{user_id}', 'select': '*', 'order': 'created_at.asc'}) or []
    init_local_db(); con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    rows=[dict(r) for r in con.execute('SELECT * FROM paper_trades WHERE user_id=? ORDER BY created_at ASC,id ASC',(user_id,)).fetchall()]; con.close(); return rows


def paper_positions(user_id: int) -> list[dict]:
    trades = list_paper_trades(user_id)
    pos = {}
    for t in trades:
        sym=t['symbol']; sign=1.0 if t['side']=='buy' else -1.0; q=float(t['quantity'])*sign
        d=pos.setdefault(sym, {'symbol':sym,'label':t['label'],'quantity':0.0,'cost_chf':0.0})
        if t['side']=='buy':
            d['cost_chf'] += float(t['total_chf'])
            d['quantity'] += float(t['quantity'])
        else:
            old_q=d['quantity']
            avg=(d['cost_chf']/old_q) if old_q>1e-12 else 0.0
            d['quantity'] -= float(t['quantity'])
            d['cost_chf'] -= avg*float(t['quantity'])
        if abs(d['quantity']) < 1e-9:
            d['quantity']=0.0; d['cost_chf']=0.0
    return [v for v in pos.values() if v['quantity']>1e-9]


def _quote_currency(symbol: str) -> str:
    try:
        fi = yf.Ticker(symbol).fast_info
        cur = getattr(fi, 'currency', None) or (fi.get('currency') if hasattr(fi,'get') else None)
        if cur: return str(cur).upper()
    except Exception:
        pass
    return 'USD'


def _fx_to_chf(currency: str) -> float:
    c=(currency or 'USD').upper()
    if c=='CHF': return 1.0
    scale=1.0
    if c=='GBP': symbol='GBPCHF=X'
    elif c=='GBX' or c=='GBPENCE': symbol='GBPCHF=X'; scale=.01
    elif c=='USD': symbol='CHF=X'
    else: symbol=f'{c}CHF=X'
    try:
        d=download_prices(symbol,'5d')
        if not d.empty: return float(d['Close'].iloc[-1])*scale
    except Exception:
        pass
    raise ValueError(f'Conversion {c} → CHF indisponible pour le moment.')


def market_quote_chf(symbol: str) -> dict:
    d=download_prices(symbol,'5d')
    if d.empty: raise ValueError('Cours indisponible pour cet actif.')
    price=float(d['Close'].iloc[-1]); currency=_quote_currency(symbol); fx=_fx_to_chf(currency)
    return {'symbol':symbol,'price_native':price,'currency':currency,'fx_to_chf':fx,'price_chf':price*fx,'asof':str(d.index[-1])}


def place_paper_trade(user_id: int, symbol: str, label: str, side: str, amount_chf: float | None = None, quantity: float | None = None) -> dict:
    side='buy' if side=='buy' else 'sell'
    account=get_paper_account(user_id)
    if not account: raise ValueError('Crée d’abord ton portefeuille d’entraînement.')
    q=market_quote_chf(symbol); price_chf=float(q['price_chf'])
    if side=='buy':
        amount=float(amount_chf or 0)
        if amount < 10: raise ValueError('Montant minimum : 10 CHF virtuels.')
        if amount > float(account['cash_chf']) + 1e-8: raise ValueError('Solde virtuel insuffisant.')
        qty=amount/price_chf; total=amount
        new_cash=float(account['cash_chf'])-total
    else:
        qty=float(quantity or 0)
        if qty<=0: raise ValueError('Quantité invalide.')
        positions={p['symbol']:p for p in paper_positions(user_id)}
        available=float(positions.get(symbol,{}).get('quantity',0))
        if qty>available+1e-9: raise ValueError('Tu ne possèdes pas cette quantité dans ton portefeuille virtuel.')
        total=qty*price_chf; new_cash=float(account['cash_chf'])+total
    row={'user_id':user_id,'symbol':symbol,'label':label,'side':side,'quantity':qty,'price_native':q['price_native'],'currency':q['currency'],'fx_to_chf':q['fx_to_chf'],'price_chf':price_chf,'total_chf':total,'created_at':utcnow_iso()}
    if production_storage_enabled():
        _sb('paper_trades','POST',payload=row,prefer='return=minimal')
        _sb('paper_accounts','PATCH',params={'user_id':f'eq.{user_id}'},payload={'cash_chf':new_cash},prefer='return=minimal')
    else:
        init_local_db(); con=sqlite3.connect(DB_PATH)
        con.execute('INSERT INTO paper_trades(user_id,symbol,label,side,quantity,price_native,currency,fx_to_chf,price_chf,total_chf,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)', (user_id,symbol,label,side,qty,q['price_native'],q['currency'],q['fx_to_chf'],price_chf,total,row['created_at']))
        con.execute('UPDATE paper_accounts SET cash_chf=? WHERE user_id=?',(new_cash,user_id)); con.commit(); con.close()
    row['cash_after_chf']=new_cash; return row


def paper_portfolio_snapshot(user_id: int) -> dict:
    account=get_paper_account(user_id)
    if not account: return {'account':None,'positions':[],'positions_value_chf':0.0,'total_value_chf':0.0,'pnl_chf':0.0,'pnl_pct':0.0}
    out=[]; value=0.0
    for p in paper_positions(user_id):
        try:
            q=market_quote_chf(p['symbol']); market_value=float(p['quantity'])*q['price_chf']; value+=market_value
            avg=(p['cost_chf']/p['quantity']) if p['quantity'] else 0.0
            out.append({**p,'current_price_chf':q['price_chf'],'market_value_chf':market_value,'avg_cost_chf':avg,'pnl_chf':market_value-p['cost_chf']})
        except Exception:
            out.append({**p,'current_price_chf':None,'market_value_chf':None,'avg_cost_chf':(p['cost_chf']/p['quantity']) if p['quantity'] else 0.0,'pnl_chf':None})
    total=float(account['cash_chf'])+value; initial=float(account['initial_cash_chf']); pnl=total-initial
    return {'account':account,'positions':out,'positions_value_chf':value,'total_value_chf':total,'pnl_chf':pnl,'pnl_pct':(pnl/initial if initial else 0.0)}


def search_assets(query: str, max_results: int = 10) -> list[dict]:
    query = (query or '').strip()
    if len(query) < 2:
        return []
    try:
        quotes = yf.Search(query, max_results=max_results, news_count=0, lists_count=0, include_research=False, enable_fuzzy_query=True, raise_errors=False).quotes or []
    except Exception:
        quotes = []
    out = []
    seen = set()
    for q in quotes:
        symbol = str(q.get('symbol') or '').strip()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        name = q.get('shortname') or q.get('longname') or q.get('name') or symbol
        exch = q.get('exchange') or q.get('exchDisp') or ''
        qtype = q.get('quoteType') or q.get('typeDisp') or ''
        label = f"{name} · {symbol}"
        if exch: label += f" · {exch}"
        out.append({'symbol': symbol, 'name': name, 'label': label, 'type': qtype})
        if len(out) >= max_results:
            break
    return out


def list_alerts(user_id: int) -> list[dict]:
    if production_storage_enabled():
        return _sb('alerts', params={'user_id': f'eq.{user_id}', 'select': '*', 'order': 'id.desc'}) or []
    init_local_db(); con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute('SELECT * FROM alerts WHERE user_id=? ORDER BY id DESC', (user_id,)).fetchall()]; con.close(); return rows


def create_alert(user_id: int, symbol: str, label: str, rule_type: str, threshold: float | None) -> None:
    row = {'user_id': user_id, 'symbol': symbol, 'label': label, 'rule_type': rule_type, 'threshold': threshold, 'enabled': True, 'created_at': utcnow_iso()}
    if production_storage_enabled():
        _sb('alerts', 'POST', payload=row, prefer='return=minimal'); return
    init_local_db(); con = sqlite3.connect(DB_PATH)
    con.execute('INSERT INTO alerts(user_id,symbol,label,rule_type,threshold,enabled,created_at) VALUES(?,?,?,?,?,?,?)', (user_id,symbol,label,rule_type,threshold,1,row['created_at']))
    con.commit(); con.close()


def delete_alert(user_id: int, alert_id: int) -> None:
    if production_storage_enabled():
        _sb('alerts', 'DELETE', params={'id': f'eq.{alert_id}', 'user_id': f'eq.{user_id}'}, prefer='return=minimal'); return
    init_local_db(); con = sqlite3.connect(DB_PATH); con.execute('DELETE FROM alerts WHERE id=? AND user_id=?',(alert_id,user_id)); con.commit(); con.close()


def all_enabled_alerts() -> list[dict]:
    if not production_storage_enabled():
        return []
    return _sb('alerts', params={'enabled': 'eq.true', 'select': '*,users(email,display_name)'}) or []


def mark_alert_sent(alert_id: int) -> None:
    if production_storage_enabled():
        _sb('alerts','PATCH',params={'id':f'eq.{alert_id}'},payload={'last_sent_at':utcnow_iso()},prefer='return=minimal')


def download_prices(symbol: str, period: str = '2y') -> pd.DataFrame:
    df = yf.download(symbol, period=period, interval='1d', auto_adjust=True, progress=False, threads=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna(subset=['Close']).sort_index()


def indicators(df: pd.DataFrame) -> dict:
    close = df['Close'].astype(float)
    returns = close.pct_change().replace([np.inf,-np.inf], np.nan).dropna()
    ma20 = close.rolling(20,min_periods=20).mean(); ma50 = close.rolling(50,min_periods=50).mean()
    diff = close.diff(); gain = diff.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); loss = (-diff.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    rsi_series = 100 - 100/(1 + gain/loss.replace(0,np.nan))
    rsi = float(rsi_series.iloc[-1]) if pd.notna(rsi_series.iloc[-1]) else 50.0
    vol = float(returns.std()*np.sqrt(252)); dd = float((close/close.cummax()-1).min()); var = float(returns.quantile(.05)); tail = returns[returns<=var]
    annual = float((close.iloc[-1]/close.iloc[0])**(252/max(len(close)-1,1))-1)
    ma50_now = float(ma50.iloc[-1]) if pd.notna(ma50.iloc[-1]) else float(close.iloc[-1])
    trend_score = 50
    trend_score += 18 if close.iloc[-1] > ma50_now else -18
    trend_score += 10 if ma20.iloc[-1] > ma50_now else -10
    if rsi < 30: trend_score += 8
    elif rsi > 70: trend_score -= 8
    trend_score = int(np.clip(trend_score,0,100))
    risk_score = int(np.clip(vol/0.6*70 + abs(dd)/0.6*30, 0, 100))
    return dict(close=close,returns=returns,ma20=ma20,ma50=ma50,rsi=rsi,vol=vol,dd=dd,var=var,cvar=float(tail.mean()) if len(tail) else var,annual=annual,trend_score=trend_score,risk_score=risk_score)


def evaluate_alert(rule_type: str, threshold: float | None, last: float, m: dict) -> tuple[bool,str]:
    if rule_type == 'price_below':
        ok = last <= float(threshold); return ok, f'cours {last:.2f} ≤ seuil {float(threshold):.2f}'
    if rule_type == 'price_above':
        ok = last >= float(threshold); return ok, f'cours {last:.2f} ≥ seuil {float(threshold):.2f}'
    if rule_type == 'rsi_low':
        t = float(threshold or 30); ok = m['rsi'] <= t; return ok, f'RSI {m["rsi"]:.1f} ≤ {t:.0f}'
    if rule_type == 'trend_recovery':
        ma50 = float(m['ma50'].iloc[-1]); ok = last > ma50 and m['rsi'] < 60; return ok, f'cours repassé au-dessus de MM50 ({ma50:.2f}) avec RSI {m["rsi"]:.1f}'
    return False, 'règle inconnue'


def send_email(to_email: str, subject: str, html: str) -> tuple[bool,str]:
    api_key = os.getenv('RESEND_API_KEY')
    sender = os.getenv('RESEND_FROM')
    if not api_key or not sender:
        return False, 'Resend non configuré'
    r = requests.post('https://api.resend.com/emails', headers={'Authorization':f'Bearer {api_key}','Content-Type':'application/json'}, json={'from':sender,'to':[to_email],'subject':subject,'html':html}, timeout=20)
    return r.ok, (r.json().get('id','envoyé') if r.ok else r.text[:300])

def create_post(user_id: int, body: str, parent_id: int | None = None, shared: dict | None = None) -> dict:
    body = (body or '').strip()
    if not body:
        raise ValueError('Le message est vide.')
    if len(body) > 500:
        raise ValueError('500 caractères maximum.')
    shared = shared or {}
    row = {'user_id': user_id, 'parent_id': parent_id, 'body': body,
           'shared_symbol': shared.get('symbol'), 'shared_label': shared.get('label'),
           'shared_price': shared.get('price'), 'shared_trend': shared.get('trend_score'),
           'shared_risk': shared.get('risk_score'), 'created_at': utcnow_iso()}
    if production_storage_enabled():
        rows = _sb('posts', 'POST', payload=row, prefer='return=representation')
        return rows[0]
    init_local_db(); con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    cur = con.execute("INSERT INTO posts(user_id,parent_id,body,shared_symbol,shared_label,shared_price,shared_trend,shared_risk,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (row['user_id'],row['parent_id'],row['body'],row['shared_symbol'],row['shared_label'],row['shared_price'],row['shared_trend'],row['shared_risk'],row['created_at']))
    con.commit(); post = dict(con.execute('SELECT * FROM posts WHERE id=?',(cur.lastrowid,)).fetchone()); con.close(); return post


def list_posts(limit: int = 80) -> list[dict]:
    limit = max(1, min(int(limit), 200))
    if production_storage_enabled():
        rows = _sb('posts', params={'select':'*,users(display_name),post_likes(user_id)','order':'created_at.desc','limit':str(limit)}) or []
        out=[]
        for r in rows:
            users = r.get('users') or {}; likes = r.get('post_likes') or []
            r['display_name'] = users.get('display_name') or 'Utilisateur'
            r['like_user_ids'] = [x.get('user_id') for x in likes if x.get('user_id') is not None]
            r['like_count'] = len(r['like_user_ids'])
            r.pop('users',None); r.pop('post_likes',None); out.append(r)
        return out
    init_local_db(); con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    rows = con.execute("SELECT p.*,u.display_name,(SELECT COUNT(*) FROM post_likes l WHERE l.post_id=p.id) AS like_count FROM posts p JOIN users u ON u.id=p.user_id ORDER BY p.created_at DESC LIMIT ?",(limit,)).fetchall()
    out=[]
    for row in rows:
        d=dict(row); d['like_user_ids']=[x[0] for x in con.execute('SELECT user_id FROM post_likes WHERE post_id=?',(d['id'],)).fetchall()]; out.append(d)
    con.close(); return out


def toggle_like(user_id: int, post_id: int) -> bool:
    if production_storage_enabled():
        existing = _sb('post_likes', params={'post_id':f'eq.{post_id}','user_id':f'eq.{user_id}','select':'post_id'}) or []
        if existing:
            _sb('post_likes','DELETE',params={'post_id':f'eq.{post_id}','user_id':f'eq.{user_id}'},prefer='return=minimal'); return False
        _sb('post_likes','POST',payload={'post_id':post_id,'user_id':user_id,'created_at':utcnow_iso()},prefer='return=minimal'); return True
    init_local_db(); con = sqlite3.connect(DB_PATH)
    exists = con.execute('SELECT 1 FROM post_likes WHERE post_id=? AND user_id=?',(post_id,user_id)).fetchone()
    if exists:
        con.execute('DELETE FROM post_likes WHERE post_id=? AND user_id=?',(post_id,user_id)); liked=False
    else:
        con.execute('INSERT INTO post_likes(post_id,user_id,created_at) VALUES(?,?,?)',(post_id,user_id,utcnow_iso())); liked=True
    con.commit(); con.close(); return liked


def delete_post(user_id: int, post_id: int) -> None:
    if production_storage_enabled():
        _sb('posts','DELETE',params={'id':f'eq.{post_id}','user_id':f'eq.{user_id}'},prefer='return=minimal'); return
    init_local_db(); con = sqlite3.connect(DB_PATH)
    con.execute('DELETE FROM post_likes WHERE post_id=?',(post_id,)); con.execute('DELETE FROM posts WHERE parent_id=?',(post_id,)); con.execute('DELETE FROM posts WHERE id=? AND user_id=?',(post_id,user_id)); con.commit(); con.close()


def _find_user_by_display_name(display_name: str) -> dict | None:
    name = (display_name or '').strip()
    if not name:
        return None
    if production_storage_enabled():
        rows = _sb('users', params={'display_name': f'eq.{name}', 'select': 'id,display_name,email', 'limit': '1'}) or []
        return rows[0] if rows else None
    init_local_db()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute('SELECT id,display_name,email FROM users WHERE lower(display_name)=lower(?) LIMIT 1', (name,)).fetchone()
    con.close()
    return dict(row) if row else None

def create_market_proposal(user_id: int, symbol: str, label: str, period: str, scope: str = 'public', target_display_name: str | None = None) -> dict:
    symbol = (symbol or '').strip().upper()[:32]
    label = (label or symbol).strip()[:120]
    if period not in {'1d','1w','1mo','6mo','1y'}:
        raise ValueError('Période invalide.')
    if scope not in {'public','friend'}:
        raise ValueError('Destination invalide.')
    target_user_id = None
    if scope == 'friend':
        friend = _find_user_by_display_name(target_display_name or '')
        if not friend:
            raise ValueError('Aucun compte trouvé avec ce pseudonyme.')
        if int(friend['id']) == int(user_id):
            raise ValueError('Choisis un autre utilisateur.')
        target_user_id = int(friend['id'])
    row = {'user_id': user_id, 'symbol': symbol, 'label': label, 'period': period, 'scope': scope, 'target_user_id': target_user_id, 'created_at': utcnow_iso()}
    if production_storage_enabled():
        rows = _sb('market_proposals', 'POST', payload=row, prefer='return=representation') or []
        return rows[0] if rows else row
    init_local_db()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.execute('INSERT INTO market_proposals(user_id,symbol,label,period,scope,target_user_id,created_at) VALUES(?,?,?,?,?,?,?)', (user_id,symbol,label,period,scope,target_user_id,row['created_at']))
    con.commit()
    out = dict(con.execute('SELECT * FROM market_proposals WHERE id=?', (cur.lastrowid,)).fetchone())
    con.close()
    return out

def list_market_proposals(viewer_user_id: int | None = None, limit: int = 100) -> list[dict]:
    limit = max(1, min(int(limit), 200))
    if production_storage_enabled():
        if viewer_user_id:
            params = {
                'or': f'(scope.eq.public,target_user_id.eq.{viewer_user_id},user_id.eq.{viewer_user_id})',
                'select': '*,users!market_proposals_user_id_fkey(display_name),market_likes(user_id)',
                'order': 'created_at.desc', 'limit': str(limit)
            }
        else:
            params = {
                'scope': 'eq.public',
                'select': '*,users!market_proposals_user_id_fkey(display_name),market_likes(user_id)',
                'order': 'created_at.desc', 'limit': str(limit)
            }
        rows = _sb('market_proposals', params=params) or []
        out = []
        for r in rows:
            users = r.get('users') or {}
            likes = r.get('market_likes') or []
            r['display_name'] = users.get('display_name') or 'Utilisateur'
            r['like_user_ids'] = [x.get('user_id') for x in likes if x.get('user_id') is not None]
            r['like_count'] = len(r['like_user_ids'])
            r.pop('users', None)
            r.pop('market_likes', None)
            out.append(r)
        return out
    init_local_db()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    if viewer_user_id:
        rows = con.execute("""SELECT p.*,u.display_name,(SELECT COUNT(*) FROM market_likes l WHERE l.proposal_id=p.id) like_count
                              FROM market_proposals p JOIN users u ON u.id=p.user_id
                              WHERE p.scope='public' OR p.target_user_id=? OR p.user_id=?
                              ORDER BY p.created_at DESC LIMIT ?""", (viewer_user_id, viewer_user_id, limit)).fetchall()
    else:
        rows = con.execute("""SELECT p.*,u.display_name,(SELECT COUNT(*) FROM market_likes l WHERE l.proposal_id=p.id) like_count
                              FROM market_proposals p JOIN users u ON u.id=p.user_id
                              WHERE p.scope='public' ORDER BY p.created_at DESC LIMIT ?""", (limit,)).fetchall()
    out = []
    for row in rows:
        d = dict(row)
        d['like_user_ids'] = [x[0] for x in con.execute('SELECT user_id FROM market_likes WHERE proposal_id=?', (d['id'],)).fetchall()]
        out.append(d)
    con.close()
    return out

def toggle_market_like(user_id: int, proposal_id: int) -> bool:
    if production_storage_enabled():
        existing = _sb('market_likes', params={'proposal_id': f'eq.{proposal_id}', 'user_id': f'eq.{user_id}', 'select': 'proposal_id'}) or []
        if existing:
            _sb('market_likes', 'DELETE', params={'proposal_id': f'eq.{proposal_id}', 'user_id': f'eq.{user_id}'}, prefer='return=minimal')
            return False
        _sb('market_likes', 'POST', payload={'proposal_id': proposal_id, 'user_id': user_id, 'created_at': utcnow_iso()}, prefer='return=minimal')
        return True
    init_local_db()
    con = sqlite3.connect(DB_PATH)
    exists = con.execute('SELECT 1 FROM market_likes WHERE proposal_id=? AND user_id=?', (proposal_id,user_id)).fetchone()
    if exists:
        con.execute('DELETE FROM market_likes WHERE proposal_id=? AND user_id=?', (proposal_id,user_id))
        liked = False
    else:
        con.execute('INSERT INTO market_likes(proposal_id,user_id,created_at) VALUES(?,?,?)', (proposal_id,user_id,utcnow_iso()))
        liked = True
    con.commit()
    con.close()
    return liked

def delete_market_proposal(user_id: int, proposal_id: int) -> None:
    if production_storage_enabled():
        _sb('market_proposals', 'DELETE', params={'id': f'eq.{proposal_id}', 'user_id': f'eq.{user_id}'}, prefer='return=minimal')
        return
    init_local_db()
    con = sqlite3.connect(DB_PATH)
    con.execute('DELETE FROM market_likes WHERE proposal_id=?', (proposal_id,))
    con.execute('DELETE FROM market_proposals WHERE id=? AND user_id=?', (proposal_id,user_id))
    con.commit()
    con.close()

def market_strip_snapshot() -> list[dict]:
    items = [('S&P 500','^GSPC'), ('Nasdaq','^IXIC'), ('Dow','^DJI'), ('SMI','^SSMI'), ('Euro Stoxx 50','^STOXX50E'), ('Bitcoin','BTC-USD'), ('Or','GC=F'), ('WTI','CL=F')]
    out = []
    for label, symbol in items:
        try:
            d = download_prices(symbol, '5d')
            if len(d) >= 2:
                last = float(d['Close'].iloc[-1])
                prev = float(d['Close'].iloc[-2])
                out.append({'label': label, 'symbol': symbol, 'price': last, 'change': (last/prev-1)*100})
        except Exception:
            continue
    return out
