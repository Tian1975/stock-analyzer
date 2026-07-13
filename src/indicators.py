"""
indicators.py — Calcula indicadors tècnics a partir de data/raw/*.json
(generats per download.py) i els desa tots junts a data/indicators.json.

Preu de referència: Close ajustat (auto_adjust=True ja aplicat a download.py,
per tant "close" ja incorpora dividends/splits).

Indicadors calculats per ticker:
- SMA20, SMA50, SMA200
- EMA20, EMA50
- RSI14
- MACD (línia, senyal, histograma) — EMA12/EMA26/EMA9 estàndard
- ATR14 (volatilitat basada en rang veritable)
- Volum mitjà 20 sessions
- Momentum (retorn % a 1/3/6 mesos aprox., en sessions bursàtils)
- Volatilitat anualitzada (desviació estàndard de retorns diaris * sqrt(252))

Ús: python src/indicators.py
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("indicators")

BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_PATH = BASE_DIR / "data" / "indicators.json"

# Sessions bursàtils aproximades per als horitzons de momentum
MOMENTUM_WINDOWS = {"1m": 21, "3m": 63, "6m": 126}


def load_raw_records() -> list[dict]:
    records = []
    for path in sorted(RAW_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("ok"):
            records.append(data)
    return records


def to_price_series(record: dict) -> pd.DataFrame:
    p = record["prices"]
    df = pd.DataFrame(
        {
            "open": p["open"],
            "high": p["high"],
            "low": p["low"],
            "close": p["close"],
            "volume": p["volume"],
        },
        index=pd.to_datetime(p["dates"]),
    )
    return df.sort_index()


def sma(series: pd.Series, window: int) -> float | None:
    if len(series) < window:
        return None
    return round(float(series.rolling(window).mean().iloc[-1]), 4)


def ema_series(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def ema_last(series: pd.Series, span: int) -> float | None:
    if len(series) < span:
        return None
    return round(float(ema_series(series, span).iloc[-1]), 4)


def rsi(series: pd.Series, window: int = 14) -> float | None:
    if len(series) < window + 1:
        return None
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    val = rsi_series.iloc[-1]
    if pd.isna(val):
        # avg_loss == 0 -> tot pujades -> RSI 100
        return 100.0 if avg_gain.iloc[-1] > 0 else None
    return round(float(val), 2)


def macd(series: pd.Series) -> dict | None:
    if len(series) < 35:  # 26 + marge per a l'EMA9 del senyal
        return None
    ema12 = ema_series(series, 12)
    ema26 = ema_series(series, 26)
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal_line
    return {
        "macd": round(float(macd_line.iloc[-1]), 4),
        "signal": round(float(signal_line.iloc[-1]), 4),
        "histogram": round(float(hist.iloc[-1]), 4),
    }


def atr(df: pd.DataFrame, window: int = 14) -> float | None:
    if len(df) < window + 1:
        return None
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    atr_val = tr.ewm(alpha=1 / window, adjust=False, min_periods=window).mean().iloc[-1]
    if pd.isna(atr_val):
        return None
    return round(float(atr_val), 4)


def avg_volume(series: pd.Series, window: int = 20) -> float | None:
    if len(series) < window:
        return None
    return round(float(series.rolling(window).mean().iloc[-1]), 0)


def momentum_pct(series: pd.Series, window: int) -> float | None:
    if len(series) < window + 1:
        return None
    past = series.iloc[-window - 1]
    now = series.iloc[-1]
    if past == 0:
        return None
    return round(100 * (now - past) / past, 2)


def annualized_volatility(series: pd.Series, window: int = 63) -> float | None:
    """Desviació estàndard dels retorns diaris, anualitzada (√252)."""
    if len(series) < window + 1:
        return None
    returns = series.pct_change().dropna().iloc[-window:]
    if len(returns) < window:
        return None
    vol = returns.std() * np.sqrt(252)
    return round(float(vol) * 100, 2)  # en percentatge


def week52_position(series: pd.Series) -> float | None:
    """Posició del preu actual dins del rang de 52 setmanes (0=mínim, 100=màxim)."""
    window = min(len(series), 252)
    if window < 20:
        return None
    recent = series.iloc[-window:]
    lo, hi = recent.min(), recent.max()
    if hi == lo:
        return 50.0
    now = series.iloc[-1]
    return round(100 * (now - lo) / (hi - lo), 1)


def compute_indicators_for_ticker(record: dict) -> dict:
    df = to_price_series(record)
    close = df["close"]

    momentum = {
        label: momentum_pct(close, window) for label, window in MOMENTUM_WINDOWS.items()
    }

    return {
        "ticker": record["ticker"],
        "region": record.get("region"),
        "as_of": df.index[-1].strftime("%Y-%m-%d"),
        "last_close": round(float(close.iloc[-1]), 4),
        "sessions_available": len(df),
        "trend": {
            "sma20": sma(close, 20),
            "sma50": sma(close, 50),
            "sma200": sma(close, 200),
            "ema20": ema_last(close, 20),
            "ema50": ema_last(close, 50),
        },
        "momentum": {
            "rsi14": rsi(close, 14),
            "macd": macd(close),
            "return_pct": momentum,
        },
        "volatility": {
            "atr14": atr(df, 14),
            "annualized_volatility_pct": annualized_volatility(close, 63),
            "week52_position_pct": week52_position(close),
        },
        "volume": {
            "avg_volume_20d": avg_volume(df["volume"], 20),
            "last_volume": int(df["volume"].iloc[-1]),
        },
    }


def main():
    start = datetime.now(timezone.utc)
    log.info("Carregant dades crues...")
    records = load_raw_records()
    log.info(f"{len(records)} tickers amb dades vàlides trobats a data/raw/")

    results = {}
    errors = []

    for record in records:
        ticker = record["ticker"]
        try:
            results[ticker] = compute_indicators_for_ticker(record)
        except Exception as e:
            log.error(f"{ticker}: error calculant indicadors ({e})")
            errors.append({"ticker": ticker, "error": str(e)})

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round((datetime.now(timezone.utc) - start).total_seconds(), 2),
        "tickers_processed": len(records),
        "tickers_ok": len(results),
        "tickers_failed": errors,
        "data": results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=None)

    log.info(f"Fet: {len(results)}/{len(records)} tickers amb indicadors calculats.")
    if errors:
        log.warning(f"Fallits: {[e['ticker'] for e in errors]}")


if __name__ == "__main__":
    main()
