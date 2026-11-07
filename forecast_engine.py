from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, brier_score_loss, mean_absolute_error, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import TimeSeriesSplit


@dataclass
class ForecastResult:
    horizon: int
    expected_return: float
    probability_up: float
    low_return: float
    high_return: float
    direction_accuracy: float
    baseline_accuracy: float
    mae: float
    baseline_mae: float
    brier: float
    quality_score: int
    samples: int
    backtest: pd.DataFrame
    feature_importance_note: str
    regime_features_used: bool
    # AngelVision 3.0 robust engine fields
    signal: str
    confidence_score: int
    model_agreement: float
    regime: str
    regime_accuracy: float | None
    auc: float | None
    confident_accuracy: float | None
    confident_coverage: float
    abstention_reason: str


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / window, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / window, adjust=False).mean()
    rs = up / down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _download_regime_context(start, end) -> pd.DataFrame:
    """Historical context that existed at each backtest date.

    No current news is included here. This is deliberate: current news belongs to
    external_context.py so the historical backtest cannot accidentally see the future.
    """
    try:
        raw = yf.download(
            ['SPY', '^VIX', '^TNX'], start=start, end=end, progress=False,
            auto_adjust=True, group_by='column', threads=True,
        )
        if raw is None or len(raw) < 100 or not isinstance(raw.columns, pd.MultiIndex):
            return pd.DataFrame()
        close = raw['Close'].copy()
        out = pd.DataFrame(index=close.index)
        if 'SPY' in close:
            s = pd.to_numeric(close['SPY'], errors='coerce')
            out['mkt_ret_1'] = s.pct_change()
            out['mkt_ret_5'] = s.pct_change(5)
            out['mkt_ret_20'] = s.pct_change(20)
            out['mkt_ret_60'] = s.pct_change(60)
            out['mkt_ma50'] = s / s.rolling(50).mean() - 1
            out['mkt_ma200'] = s / s.rolling(200).mean() - 1
            out['mkt_vol20'] = s.pct_change().rolling(20).std() * np.sqrt(252)
        if '^VIX' in close:
            v = pd.to_numeric(close['^VIX'], errors='coerce')
            out['vix_level'] = v / 100.0
            out['vix_chg_5'] = v.pct_change(5)
            out['vix_chg_20'] = v.pct_change(20)
            out['vix_z60'] = (v - v.rolling(60).mean()) / v.rolling(60).std().replace(0, np.nan)
        if '^TNX' in close:
            y = pd.to_numeric(close['^TNX'], errors='coerce')
            out['yield10y'] = y / 100.0
            out['yield10y_chg5'] = y.diff(5) / 10.0
            out['yield10y_chg20'] = y.diff(20) / 10.0
        return out.replace([np.inf, -np.inf], np.nan)
    except Exception:
        return pd.DataFrame()


def _features(df: pd.DataFrame, regime: pd.DataFrame | None = None) -> pd.DataFrame:
    close = pd.to_numeric(df['Close'], errors='coerce')
    high = pd.to_numeric(df['High'], errors='coerce') if 'High' in df else close
    low = pd.to_numeric(df['Low'], errors='coerce') if 'Low' in df else close
    volume = pd.to_numeric(df['Volume'], errors='coerce') if 'Volume' in df else pd.Series(index=df.index, dtype=float)
    r1 = close.pct_change()

    out = pd.DataFrame(index=df.index)
    out['ret_1'] = r1
    for n in (2, 3, 5, 10, 20, 60, 120):
        out[f'ret_{n}'] = close.pct_change(n)
    for n in (10, 20, 50, 100, 200):
        ma = close.rolling(n).mean()
        out[f'price_ma_{n}'] = close / ma - 1
    for n in (10, 20, 60):
        out[f'vol_{n}'] = r1.rolling(n).std() * np.sqrt(252)
        out[f'skew_{n}'] = r1.rolling(n).skew()
    out['rsi_14'] = _rsi(close) / 100.0

    # MACD / trend acceleration
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    out['macd_pct'] = macd / close.replace(0, np.nan)
    out['macd_signal_gap'] = (macd - macd.ewm(span=9, adjust=False).mean()) / close.replace(0, np.nan)

    # Bollinger position and ATR-like range
    ma20 = close.rolling(20).mean()
    sd20 = close.rolling(20).std()
    out['bollinger_z'] = (close - ma20) / sd20.replace(0, np.nan)
    tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    out['atr14_pct'] = tr.rolling(14).mean() / close.replace(0, np.nan)
    out['range'] = (high - low) / close.replace(0, np.nan)
    out['drawdown_60'] = close / close.rolling(60).max() - 1
    out['drawdown_252'] = close / close.rolling(252).max() - 1
    out['day_of_week'] = pd.Index(df.index).dayofweek / 4.0

    if volume.notna().sum() > 20 and float(volume.fillna(0).abs().sum()) > 0:
        lv = np.log1p(volume.clip(lower=0))
        out['volume_z20'] = (lv - lv.rolling(20).mean()) / lv.rolling(20).std().replace(0, np.nan)
        out['volume_change_5'] = volume.pct_change(5).replace([np.inf, -np.inf], np.nan)
        out['volume_ma20_ratio'] = volume / volume.rolling(20).mean() - 1
    else:
        out['volume_z20'] = 0.0
        out['volume_change_5'] = 0.0
        out['volume_ma20_ratio'] = 0.0

    if regime is not None and not regime.empty:
        rg = regime.reindex(out.index).ffill(limit=5)
        for col in rg.columns:
            out[f'regime_{col}'] = rg[col]
        if 'mkt_ret_1' in rg:
            out['corr_mkt_60'] = r1.rolling(60).corr(rg['mkt_ret_1'])
            cov = r1.rolling(60).cov(rg['mkt_ret_1'])
            var = rg['mkt_ret_1'].rolling(60).var()
            out['beta_mkt_60'] = cov / var.replace(0, np.nan)

    return out.replace([np.inf, -np.inf], np.nan)


def _regime_labels(X: pd.DataFrame) -> pd.Series:
    idx = X.index
    # Prefer market regime if available; otherwise derive an asset-only regime.
    trend_col = 'regime_mkt_ma200' if 'regime_mkt_ma200' in X else 'price_ma_200'
    vol_col = 'regime_vix_level' if 'regime_vix_level' in X else 'vol_20'
    trend = X.get(trend_col, pd.Series(0.0, index=idx)).fillna(0.0)
    vol = X.get(vol_col, pd.Series(0.2, index=idx)).fillna(0.2)
    high_vol = vol > (0.25 if 'vix' not in vol_col else 0.25)
    bull = trend >= 0
    labels = np.where(bull & ~high_vol, 'hausse calme',
             np.where(bull & high_vol, 'hausse volatile',
             np.where(~bull & ~high_vol, 'baisse calme', 'baisse volatile')))
    return pd.Series(labels, index=idx)


def _dataset(df: pd.DataFrame, horizon: int, regime: pd.DataFrame | None = None):
    X = _features(df, regime)
    close = pd.to_numeric(df['Close'], errors='coerce')
    future_return = close.shift(-horizon) / close - 1.0
    direction = (future_return > 0).astype(int)
    reg_label = _regime_labels(X)
    data = X.copy()
    data['target_return'] = future_return
    data['target_direction'] = direction
    data['regime_label'] = reg_label
    data = data.dropna()
    return data[X.columns], data['target_return'], data['target_direction'], data['regime_label']


def _models(seed: int = 42):
    reg_models = [
        HistGradientBoostingRegressor(
            learning_rate=0.035, max_iter=260, max_leaf_nodes=15,
            l2_regularization=3.0, min_samples_leaf=28, random_state=seed,
        ),
        ExtraTreesRegressor(
            n_estimators=320, max_depth=8, min_samples_leaf=10,
            max_features=0.75, random_state=seed, n_jobs=-1,
        ),
        make_pipeline(RobustScaler(), Ridge(alpha=8.0)),
    ]
    cls_models = [
        HistGradientBoostingClassifier(
            learning_rate=0.035, max_iter=260, max_leaf_nodes=15,
            l2_regularization=3.0, min_samples_leaf=28, random_state=seed,
        ),
        ExtraTreesClassifier(
            n_estimators=320, max_depth=8, min_samples_leaf=10,
            max_features=0.75, class_weight='balanced', random_state=seed, n_jobs=-1,
        ),
        make_pipeline(RobustScaler(), LogisticRegression(C=0.25, max_iter=1200, class_weight='balanced')),
    ]
    return reg_models, cls_models


def _fit_predict_ensemble(Xtr, Xte, yr, yc, seed=42):
    regs, clfs = _models(seed)
    reg_preds = []
    cls_preds = []
    for model in regs:
        model.fit(Xtr, yr)
        reg_preds.append(np.asarray(model.predict(Xte), dtype=float))
    for model in clfs:
        model.fit(Xtr, yc)
        cls_preds.append(np.asarray(model.predict_proba(Xte)[:, 1], dtype=float))
    return np.vstack(reg_preds), np.vstack(cls_preds)


def forecast_market(df: pd.DataFrame, horizon: int = 20) -> ForecastResult:
    """AngelVision paper-trading forecast engine.

    Design goals:
    - time ordered / walk-forward only;
    - purge gap equal to prediction horizon to reduce label leakage;
    - ensemble rather than one model;
    - explicit uncertainty and model disagreement;
    - ABSTENTION when the estimated edge is weak.
    """
    horizon = int(horizon)
    if horizon not in (5, 20, 60):
        raise ValueError('Horizon pris en charge : 5, 20 ou 60 séances.')
    if df is None or len(df) < 420:
        raise ValueError('Pas assez de données. Utilise au moins plusieurs années d’historique.')

    regime = _download_regime_context(df.index.min() - pd.Timedelta(days=420), df.index.max() + pd.Timedelta(days=5))
    X, y_reg, y_cls, regime_labels = _dataset(df, horizon, regime)
    if len(X) < 320:
        regime = pd.DataFrame()
        X, y_reg, y_cls, regime_labels = _dataset(df, horizon, regime)
    if len(X) < 320:
        raise ValueError('Pas assez de données exploitables après création des variables.')

    # Keep the recent regime relevant and training time reasonable on Streamlit Cloud.
    if len(X) > 2500:
        X = X.iloc[-2500:]
        y_reg = y_reg.loc[X.index]
        y_cls = y_cls.loc[X.index]
        regime_labels = regime_labels.loc[X.index]

    n_splits = 6 if len(X) >= 1000 else 5 if len(X) >= 700 else 4
    splitter = TimeSeriesSplit(n_splits=n_splits, gap=horizon)
    pred_reg = pd.Series(index=X.index, dtype=float)
    pred_prob = pd.Series(index=X.index, dtype=float)
    pred_disp = pd.Series(index=X.index, dtype=float)

    for fold, (train_idx, test_idx) in enumerate(splitter.split(X)):
        Xtr, Xte = X.iloc[train_idx], X.iloc[test_idx]
        yr_tr = y_reg.iloc[train_idx]
        yc_tr = y_cls.iloc[train_idx]
        reg_mat, cls_mat = _fit_predict_ensemble(Xtr, Xte, yr_tr, yc_tr, seed=42 + fold)
        pred_reg.iloc[test_idx] = np.median(reg_mat, axis=0)
        pred_prob.iloc[test_idx] = np.mean(cls_mat, axis=0)
        pred_disp.iloc[test_idx] = np.std(cls_mat, axis=0)

    valid = pred_reg.notna() & pred_prob.notna()
    yv_reg = y_reg[valid]
    yv_cls = y_cls[valid]
    pr = pred_reg[valid]
    raw_pp = pred_prob[valid].clip(.01, .99)
    pdsp = pred_disp[valid].fillna(0.0)

    # Conservative probability shrinkage. The model must earn extremity in walk-forward tests.
    raw_direction = (raw_pp >= 0.5).astype(int)
    raw_acc = float(accuracy_score(yv_cls, raw_direction))
    base_rate = float(y_cls.iloc[: max(50, int(len(y_cls) * 0.6))].mean())
    baseline_class = int(base_rate >= 0.5)
    baseline_accuracy = float(np.mean(yv_cls.to_numpy() == baseline_class))
    edge_acc = raw_acc - baseline_accuracy
    shrink = float(np.clip(0.30 + edge_acc / 0.10, 0.20, 1.0))
    pp = (0.5 + (raw_pp - 0.5) * shrink).clip(.02, .98)
    direction_pred = (pp >= 0.5).astype(int)
    direction_accuracy = float(accuracy_score(yv_cls, direction_pred))

    mae = float(mean_absolute_error(yv_reg, pr))
    baseline_mae = float(mean_absolute_error(yv_reg, np.zeros(len(yv_reg))))
    brier = float(brier_score_loss(yv_cls, pp))
    try:
        auc = float(roc_auc_score(yv_cls, pp)) if yv_cls.nunique() > 1 else None
    except Exception:
        auc = None

    confident_mask = (pp >= 0.58) | (pp <= 0.42)
    confident_coverage = float(confident_mask.mean()) if len(pp) else 0.0
    confident_accuracy = None
    if confident_mask.sum() >= 20:
        confident_accuracy = float(accuracy_score(yv_cls[confident_mask], (pp[confident_mask] >= 0.5).astype(int)))

    # Fit full ensemble for today's forecast.
    feat_all = _features(df, regime).reindex(columns=X.columns).dropna()
    if feat_all.empty:
        raise ValueError('Impossible de calculer les variables de la séance courante.')
    feat = feat_all.iloc[[-1]]
    reg_mat, cls_mat = _fit_predict_ensemble(X, feat, y_reg, y_cls, seed=123)
    expected = float(np.median(reg_mat[:, 0]))
    raw_prob_up = float(np.mean(cls_mat[:, 0]))
    prob_up = float(np.clip(0.5 + (raw_prob_up - 0.5) * shrink, .02, .98))
    model_agreement = float(np.clip(1.0 - np.std(cls_mat[:, 0]) / 0.20, 0.0, 1.0))

    residuals = (yv_reg - pr).to_numpy(dtype=float)
    if len(residuals) >= 80:
        q_low, q_high = np.quantile(residuals, [0.10, 0.90])
    else:
        s = float(np.std(residuals)) if len(residuals) else 0.05
        q_low, q_high = -1.28 * s, 1.28 * s
    low = expected + float(q_low)
    high = expected + float(q_high)

    # Regime-specific reliability.
    current_regime = str(_regime_labels(feat).iloc[-1])
    valid_regimes = regime_labels[valid]
    rm = valid_regimes == current_regime
    regime_accuracy = None
    if rm.sum() >= 35:
        regime_accuracy = float(accuracy_score(yv_cls[rm], (pp[rm] >= 0.5).astype(int)))

    # Quality: benchmark edge + calibration + ensemble agreement + regime consistency.
    mae_edge = 0.0 if baseline_mae <= 0 else float(np.clip(1 - mae / baseline_mae, -0.25, 0.40))
    auc_edge = 0.0 if auc is None else float(np.clip(auc - 0.5, -0.10, 0.20))
    calibration = float(np.clip(0.25 - brier, -0.12, 0.18))
    regime_bonus = 0.0 if regime_accuracy is None else float(np.clip(regime_accuracy - 0.5, -0.08, 0.12))
    quality = int(np.clip(
        38 + (direction_accuracy - baseline_accuracy) * 220 + mae_edge * 60 +
        auc_edge * 90 + calibration * 70 + model_agreement * 10 + regime_bonus * 50,
        0, 100,
    ))

    interval_half = max(1e-6, (high - low) / 2)
    min_return_edge = max(0.004, 0.14 * interval_half)
    prob_edge = abs(prob_up - 0.5)
    enough_edge = abs(expected) >= min_return_edge and prob_edge >= 0.07
    enough_quality = quality >= 55 and direction_accuracy > baseline_accuracy
    enough_agreement = model_agreement >= 0.55

    reasons = []
    if not enough_quality:
        reasons.append('backtest trop faible ou proche du benchmark')
    if not enough_edge:
        reasons.append('avantage prédit trop petit par rapport à l’incertitude')
    if not enough_agreement:
        reasons.append('désaccord important entre les modèles')
    if regime_accuracy is not None and regime_accuracy < 0.50:
        reasons.append('mauvaise fiabilité historique dans le régime actuel')

    if reasons:
        signal = 'ABSTENTION'
        abstention_reason = '; '.join(reasons)
    elif expected > 0 and prob_up >= 0.57:
        signal = 'SCÉNARIO HAUSSIER'
        abstention_reason = ''
    elif expected < 0 and prob_up <= 0.43:
        signal = 'SCÉNARIO BAISSIER'
        abstention_reason = ''
    else:
        signal = 'ABSTENTION'
        abstention_reason = 'les modèles ne donnent pas une direction suffisamment nette'

    confidence = int(np.clip(
        0.50 * quality + 25 * min(1.0, prob_edge / 0.18) + 15 * model_agreement +
        (10 * max(0.0, (regime_accuracy or 0.5) - 0.5) / 0.15 if regime_accuracy else 0),
        0, 100,
    ))
    if signal == 'ABSTENTION':
        confidence = min(confidence, 54)

    bt = pd.DataFrame({
        'actual_return': yv_reg,
        'predicted_return': pr,
        'prob_up': pp,
        'model_disagreement': pdsp,
        'regime': valid_regimes,
    }).tail(450)

    regime_used = any(str(c).startswith('regime_') for c in X.columns)
    note = (
        'Ensemble : gradient boosting + arbres extrêmement aléatoires + modèles linéaires robustes. '
        'Variables : momentum multi-horizon, moyennes mobiles, volatilité, RSI, MACD, bandes de Bollinger, '
        'drawdown, amplitude/ATR et volume.'
    )
    if regime_used:
        note += ' Régime historique : SPY, VIX et taux US 10 ans quand disponibles.'
    note += f' Validation walk-forward avec gap de {horizon} séances pour réduire les fuites temporelles.'

    return ForecastResult(
        horizon=horizon,
        expected_return=expected,
        probability_up=prob_up,
        low_return=low,
        high_return=high,
        direction_accuracy=direction_accuracy,
        baseline_accuracy=baseline_accuracy,
        mae=mae,
        baseline_mae=baseline_mae,
        brier=brier,
        quality_score=quality,
        samples=int(valid.sum()),
        backtest=bt,
        feature_importance_note=note,
        regime_features_used=regime_used,
        signal=signal,
        confidence_score=confidence,
        model_agreement=model_agreement,
        regime=current_regime,
        regime_accuracy=regime_accuracy,
        auc=auc,
        confident_accuracy=confident_accuracy,
        confident_coverage=confident_coverage,
        abstention_reason=abstention_reason,
    )
