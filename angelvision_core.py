import base64
import hashlib
import hmac
import json
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
    'Bitcoin · BTC-USD': 'BTC-USD',
    'Ethereum · ETH-USD': 'ETH-USD',
    'Or · GLD': 'GLD',
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
        created_at TEXT NOT NULL
    )''')
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
    con.commit(); con.close()


def _supabase_cfg() -> tuple[str | None, str | None]:
    url = os.getenv('SUPABASE_URL')
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


def create_user(email: str, password: str) -> dict:
    email = email.strip().lower()
    if production_storage_enabled():
        existing = _sb('users', params={'email': f'eq.{email}', 'select': 'id'})
        if existing:
            raise ValueError('Un compte existe déjà avec cet email.')
        rows = _sb('users', 'POST', payload={'email': email, 'password_hash': hash_password(password), 'created_at': utcnow_iso()}, prefer='return=representation')
        return rows[0]
    init_local_db(); con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    try:
        cur = con.execute('INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)', (email, hash_password(password), utcnow_iso()))
        con.commit(); row = con.execute('SELECT id,email,created_at FROM users WHERE id=?', (cur.lastrowid,)).fetchone(); return dict(row)
    except sqlite3.IntegrityError:
        raise ValueError('Un compte existe déjà avec cet email.')
    finally:
        con.close()


def authenticate_user(email: str, password: str) -> dict | None:
    email = email.strip().lower()
    if production_storage_enabled():
        rows = _sb('users', params={'email': f'eq.{email}', 'select': 'id,email,password_hash,created_at'})
        if not rows or not verify_password(password, rows[0]['password_hash']):
            return None
        return {k: rows[0][k] for k in ('id','email','created_at')}
    init_local_db(); con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    row = con.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone(); con.close()
    if row and verify_password(password, row['password_hash']):
        return {'id': row['id'], 'email': row['email'], 'created_at': row['created_at']}
    return None


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
    return _sb('alerts', params={'enabled': 'eq.true', 'select': '*,users(email)'}) or []


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
