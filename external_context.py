from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import math
import os
import re
import xml.etree.ElementTree as ET
from typing import Any

import pandas as pd
import requests


@dataclass
class InternetContext:
    news_score: float = 0.0
    news_count: int = 0
    news_items: list[dict[str, Any]] = field(default_factory=list)
    macro_score: float = 0.0
    macro_details: dict[str, Any] = field(default_factory=dict)
    insider_score: float = 0.0
    insider_details: dict[str, Any] = field(default_factory=dict)
    event_risk: float = 0.0
    sources_ok: list[str] = field(default_factory=list)
    sources_missing: list[str] = field(default_factory=list)

    @property
    def context_score(self) -> float:
        # Deliberately conservative. This is a current-context overlay, not a calibrated forecast.
        return float(max(-1.0, min(1.0, 0.50 * self.news_score + 0.30 * self.macro_score + 0.20 * self.insider_score)))


_POSITIVE = {
    'beat','beats','surge','surges','growth','record','profit','profits','upgrade','upgrades','bullish',
    'strong','rebound','recovery','expands','expansion','approval','approved','partnership','contract',
    'buyback','dividend','raises','raised','outperform','optimistic','gain','gains','rally','rallies',
    'croissance','record','hausse','bénéfice','benefice','bénéfices','benefices','rebond','optimiste',
    'accord','approuvé','approuve','dividende','surperformance','gagne','gains'
}
_NEGATIVE = {
    'miss','misses','drop','drops','plunge','plunges','loss','losses','downgrade','downgrades','bearish',
    'weak','warning','cuts','cut','lawsuit','probe','investigation','fraud','recall','default','bankruptcy',
    'layoffs','decline','declines','slump','selloff','crash','risk','risks','tariff','sanction',
    'baisse','perte','pertes','alerte','faible','enquête','enquete','fraude','rappel','faillite','licenciements',
    'risque','sanction','chute','repli'
}


def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return float(max(lo, min(hi, x)))


def _headline_sentiment(text: str) -> float:
    words = re.findall(r"[A-Za-zÀ-ÿ'-]+", (text or '').lower())
    if not words:
        return 0.0
    pos = sum(w in _POSITIVE for w in words)
    neg = sum(w in _NEGATIVE for w in words)
    raw = (pos - neg) / max(2.0, math.sqrt(len(words)))
    return _clip(raw)


def fetch_gdelt_news(query: str, max_records: int = 25) -> tuple[list[dict[str, Any]], float]:
    """Fetch recent public news from GDELT DOC API.

    GDELT is used as a broad public-web news discovery source. Sentiment here is a transparent
    headline lexicon, not a language model and not a trading signal.
    """
    if not query.strip():
        return [], 0.0
    params = {
        'query': query.strip(),
        'mode': 'ArtList',
        'maxrecords': max(5, min(int(max_records), 75)),
        'format': 'json',
        'sort': 'HybridRel',
        'timespan': '7d',
    }
    r = requests.get('https://api.gdeltproject.org/api/v2/doc/doc', params=params, timeout=12)
    r.raise_for_status()
    payload = r.json()
    articles = payload.get('articles') or payload.get('results') or []
    items: list[dict[str, Any]] = []
    scores: list[float] = []
    for a in articles:
        title = str(a.get('title') or '').strip()
        if not title:
            continue
        score = _headline_sentiment(title)
        scores.append(score)
        items.append({
            'title': title,
            'url': a.get('url') or '',
            'domain': a.get('domain') or '',
            'seen_date': a.get('seendate') or a.get('date') or '',
            'sentiment': score,
        })
    if not scores:
        return items, 0.0
    # Trim outliers so one sensational headline does not dominate.
    s = pd.Series(scores, dtype=float)
    score = float(s.clip(s.quantile(.10), s.quantile(.90)).mean()) if len(s) >= 5 else float(s.mean())
    return items, _clip(score)


def _fred_series(series_id: str, api_key: str, limit: int = 200) -> pd.Series:
    params = {
        'series_id': series_id,
        'api_key': api_key,
        'file_type': 'json',
        'sort_order': 'desc',
        'limit': int(limit),
    }
    r = requests.get('https://api.stlouisfed.org/fred/series/observations', params=params, timeout=12)
    r.raise_for_status()
    obs = r.json().get('observations', [])
    rows = []
    for o in obs:
        try:
            val = float(o.get('value'))
        except (TypeError, ValueError):
            continue
        rows.append((pd.to_datetime(o.get('date')), val))
    if not rows:
        return pd.Series(dtype=float)
    return pd.Series(dict(rows), dtype=float).sort_index()


def fetch_macro_context(api_key: str | None = None) -> tuple[dict[str, Any], float]:
    """Current US/global-risk proxies from FRED.

    FRED requires an API key. If none is configured, the caller should treat macro context as unavailable.
    """
    api_key = (api_key or os.getenv('FRED_API_KEY') or '').strip()
    if not api_key:
        raise RuntimeError('FRED_API_KEY absent')

    details: dict[str, Any] = {}
    score_parts: list[float] = []

    vix = _fred_series('VIXCLS', api_key, 120)
    if not vix.empty:
        latest = float(vix.iloc[-1])
        details['VIX'] = latest
        # Lower volatility is mildly risk-on; very high VIX is risk-off.
        score_parts.append(_clip((22.0 - latest) / 18.0))

    ten = _fred_series('DGS10', api_key, 120)
    if not ten.empty:
        latest = float(ten.iloc[-1])
        change20 = latest - float(ten.iloc[-min(20, len(ten))])
        details['US10Y'] = latest
        details['US10Y_20d_change'] = change20
        score_parts.append(_clip(-change20 / 0.75) * 0.45)

    fed = _fred_series('DFF', api_key, 45)
    if not fed.empty:
        details['FedFunds'] = float(fed.iloc[-1])

    unrate = _fred_series('UNRATE', api_key, 24)
    if len(unrate) >= 4:
        latest = float(unrate.iloc[-1])
        change3 = latest - float(unrate.iloc[-4])
        details['Unemployment'] = latest
        details['Unemployment_3m_change'] = change3
        score_parts.append(_clip(-change3 / 0.8) * 0.35)

    cpi = _fred_series('CPIAUCSL', api_key, 30)
    if len(cpi) >= 13:
        yoy = float(cpi.iloc[-1] / cpi.iloc[-13] - 1.0)
        details['CPI_yoy'] = yoy
        # Inflation far above ~2.5% is a mild headwind in this simple context overlay.
        score_parts.append(_clip((0.025 - yoy) / 0.035) * 0.25)

    score = float(sum(score_parts) / max(1.0, sum(abs(x) > 0 for x in score_parts))) if score_parts else 0.0
    return details, _clip(score)


@lru_cache(maxsize=1)
def _sec_ticker_map(user_agent: str) -> dict[str, int]:
    headers = {'User-Agent': user_agent, 'Accept-Encoding': 'gzip, deflate'}
    r = requests.get('https://www.sec.gov/files/company_tickers.json', headers=headers, timeout=12)
    r.raise_for_status()
    data = r.json()
    out: dict[str, int] = {}
    for row in data.values():
        ticker = str(row.get('ticker') or '').upper()
        cik = row.get('cik_str')
        if ticker and cik is not None:
            out[ticker] = int(cik)
    return out


def _xml_values(text: str, parent_tag: str, child_tag: str) -> list[str]:
    # Form 4 XML is simple but can include namespaces / wrappers. Regex is intentionally defensive.
    block_re = re.compile(rf'<{parent_tag}[^>]*>(.*?)</{parent_tag}>', re.I | re.S)
    child_re = re.compile(rf'<{child_tag}[^>]*>.*?<value[^>]*>(.*?)</value>.*?</{child_tag}>', re.I | re.S)
    vals: list[str] = []
    for block in block_re.findall(text):
        m = child_re.search(block)
        if m:
            vals.append(re.sub(r'<[^>]+>', '', m.group(1)).strip())
    return vals


def fetch_sec_insider_activity(ticker: str, user_agent: str | None = None, lookback_days: int = 120) -> tuple[dict[str, Any], float]:
    """Summarise *publicly filed* US insider Form 4 activity for an issuer.

    This never accesses private portfolios. It only uses disclosures published through SEC EDGAR.
    """
    ua = (user_agent or os.getenv('SEC_USER_AGENT') or '').strip()
    if not ua or '@' not in ua:
        raise RuntimeError('SEC_USER_AGENT absent (utilise un identifiant avec email de contact)')
    ticker = ticker.upper().strip()
    # Strip Yahoo suffixes: SEC mapping only works for US issuer tickers.
    if any(ch in ticker for ch in ('^', '=', '-', '.')) and ticker not in ('BRK-B', 'BRK-A'):
        raise RuntimeError('Ticker non-US ou non compatible SEC')
    mapping = _sec_ticker_map(ua)
    cik = mapping.get(ticker)
    if not cik:
        raise RuntimeError('Ticker absent du mapping SEC')

    headers = {'User-Agent': ua, 'Accept-Encoding': 'gzip, deflate'}
    cik10 = f'{cik:010d}'
    r = requests.get(f'https://data.sec.gov/submissions/CIK{cik10}.json', headers=headers, timeout=12)
    r.raise_for_status()
    recent = (r.json().get('filings') or {}).get('recent') or {}
    forms = recent.get('form') or []
    accessions = recent.get('accessionNumber') or []
    docs = recent.get('primaryDocument') or []
    dates = recent.get('filingDate') or []
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=int(lookback_days))

    form4 = []
    material = []
    for form, acc, doc, date_s in zip(forms, accessions, docs, dates):
        try:
            d = datetime.strptime(date_s, '%Y-%m-%d').date()
        except Exception:
            continue
        if d < cutoff:
            continue
        if form == '4':
            form4.append((acc, doc, date_s))
        if form in ('8-K', '10-Q', '10-K'):
            material.append({'form': form, 'date': date_s, 'accession': acc})

    purchases = sales = 0
    purchase_shares = sale_shares = 0.0
    parsed = 0
    for acc, doc, date_s in form4[:10]:
        acc_clean = str(acc).replace('-', '')
        url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/{doc}'
        try:
            rr = requests.get(url, headers=headers, timeout=10)
            rr.raise_for_status()
            text = rr.text
            codes = re.findall(r'<transactionCode>\s*([A-Z])\s*</transactionCode>', text, re.I)
            shares = re.findall(r'<transactionShares>.*?<value>([0-9.,-]+)</value>.*?</transactionShares>', text, re.I | re.S)
            parsed += 1
            for i, code in enumerate(codes):
                try:
                    sh = float(shares[i].replace(',', '')) if i < len(shares) else 0.0
                except Exception:
                    sh = 0.0
                if code.upper() == 'P':
                    purchases += 1; purchase_shares += max(0.0, sh)
                elif code.upper() == 'S':
                    sales += 1; sale_shares += max(0.0, sh)
        except Exception:
            continue

    # Use transaction counts and log-scaled disclosed shares; do not pretend these represent all insider intent.
    net_count = purchases - sales
    denom = max(1, purchases + sales)
    count_score = net_count / denom
    share_score = 0.0
    if purchase_shares + sale_shares > 0:
        share_score = (purchase_shares - sale_shares) / (purchase_shares + sale_shares)
    score = _clip(0.65 * count_score + 0.35 * share_score)
    details = {
        'ticker': ticker,
        'cik': cik,
        'form4_filings': len(form4),
        'forms_parsed': parsed,
        'purchase_transactions': purchases,
        'sale_transactions': sales,
        'purchase_shares_reported': purchase_shares,
        'sale_shares_reported': sale_shares,
        'recent_material_filings': material[:8],
    }
    return details, score


def build_internet_context(asset_name: str, ticker: str) -> InternetContext:
    ctx = InternetContext()

    # Broad current news.
    try:
        query = f'"{asset_name}"' if asset_name and asset_name.upper() != ticker.upper() else ticker
        items, score = fetch_gdelt_news(query, 30)
        ctx.news_items = items
        ctx.news_count = len(items)
        ctx.news_score = score
        ctx.sources_ok.append('GDELT news')
    except Exception as e:
        ctx.sources_missing.append(f'GDELT: {e}')

    # Macro context is optional because FRED requires a user API key.
    try:
        details, score = fetch_macro_context()
        ctx.macro_details = details
        ctx.macro_score = score
        ctx.sources_ok.append('FRED macro')
    except Exception as e:
        ctx.sources_missing.append(f'FRED: {e}')

    # Public SEC insider activity for compatible US equities only.
    try:
        details, score = fetch_sec_insider_activity(ticker)
        ctx.insider_details = details
        ctx.insider_score = score
        ctx.sources_ok.append('SEC EDGAR Form 4')
    except Exception as e:
        ctx.sources_missing.append(f'SEC: {e}')

    # Event risk: high news volume + many recent material filings reduces confidence, without choosing direction.
    filings_n = len(ctx.insider_details.get('recent_material_filings') or []) if ctx.insider_details else 0
    ctx.event_risk = _clip((ctx.news_count / 50.0) + (filings_n / 12.0), 0.0, 1.0)
    return ctx
