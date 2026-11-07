import os
from datetime import datetime, timezone
from email.utils import format_datetime

from angelvision_core import all_enabled_alerts, download_prices, evaluate_alert, indicators, mark_alert_sent, production_storage_enabled, send_email


def hours_since(iso):
    if not iso: return 1e9
    try:
        dt=datetime.fromisoformat(iso.replace('Z','+00:00')); return (datetime.now(timezone.utc)-dt).total_seconds()/3600
    except Exception: return 1e9

if not production_storage_enabled():
    raise SystemExit('Supabase doit être configuré pour le worker.')

for alert in all_enabled_alerts():
    if hours_since(alert.get('last_sent_at')) < 20:
        continue
    symbol=alert['symbol']; df=download_prices(symbol,'1y')
    if len(df)<65: continue
    m=indicators(df); last=float(m['close'].iloc[-1]); hit,reason=evaluate_alert(alert['rule_type'],alert.get('threshold'),last,m)
    if not hit: continue
    user=alert.get('users') or {}; email=user.get('email') if isinstance(user,dict) else None
    if not email: continue
    html=f'''<div style="font-family:Arial,sans-serif;max-width:620px"><h2>AngelVision AI — signal à examiner</h2><p><b>{alert['label']}</b> ({symbol}) a déclenché une condition configurée.</p><p><b>Pourquoi :</b> {reason}</p><p>Cours disponible : {last:.2f}<br>RSI : {m['rsi']:.1f}<br>Volatilité annualisée historique : {m['vol']:.1%}</p><p style="color:#666">Ce message n'est pas un conseil d'achat. Vérifie les fondamentaux, l'actualité, ton horizon et le risque avant toute décision.</p></div>'''
    ok,_=send_email(email,f'AngelVision — {symbol} : condition à examiner',html)
    if ok: mark_alert_sent(alert['id'])
