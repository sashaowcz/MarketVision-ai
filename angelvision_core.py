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
        created_at TEXT NOT NULL
    )''')
    cols = {row[1] for row in con.execute('PRAGMA table_info(users)').fetchall()}
    if 'display_name' not in cols:
        con.execute('ALTER TABLE users ADD COLUMN display_name TEXT')
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
        rows = _sb('users', 'POST', payload={'email': email, 'password_hash': hash_password(password), 'display_name': display_name, 'created_at': utcnow_iso()}, prefer='return=representation')
        return rows[0]
    init_local_db(); con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    try:
        cur = con.execute('INSERT INTO users(email,password_hash,display_name,created_at) VALUES(?,?,?,?)', (email, hash_password(password), display_name, utcnow_iso()))
        con.commit(); row = con.execute('SELECT id,email,display_name,created_at FROM users WHERE id=?', (cur.lastrowid,)).fetchone(); return dict(row)
    except sqlite3.IntegrityError:
        raise ValueError('Un compte existe déjà avec cet email.')
    finally:
        con.close()


def authenticate_user(email: str, password: str) -> dict | None:
    email = email.strip().lower()
    if production_storage_enabled():
        rows = _sb('users', params={'email': f'eq.{email}', 'select': 'id,email,password_hash,display_name,created_at'})
        if not rows or not verify_password(password, rows[0]['password_hash']):
            return None
        return {k: rows[0].get(k) for k in ('id','email','display_name','created_at')}
    init_local_db(); con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    row = con.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone(); con.close()
    if row and verify_password(password, row['password_hash']):
        return {'id': row['id'], 'email': row['email'], 'display_name': row['display_name'], 'created_at': row['created_at']}
    return None


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
