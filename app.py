import io
import time
import requests
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="NSE F&O Scanner", layout="wide")
st.title("📊 NSE F&O Scanner")
st.caption("RSI • Ichimoku (Cloud + TK Cross) • CPR — multi-timeframe, full F&O universe")

IST = ZoneInfo("Asia/Kolkata")
NSE_LOTS_URL = "https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv"
INDEX_SET = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50", "NIFTYFPI", "SENSEX", "BANKEX"}
MIN_ROWS = 30

# interval, period  (Yahoo limits: 1m=7d, 5m/15m/30m=60d, 1h=730d)
TIMEFRAMES = {
    "1 Min": ("1m", "5d"),
    "5 Min": ("5m", "30d"),
    "15 Min": ("15m", "60d"),
    "30 Min": ("30m", "60d"),
    "1 Hour": ("1h", "180d"),
    "4 Hour": ("1h", "365d"),   # resampled from 1h
    "Daily": ("1d", "1y"),
    "Weekly": ("1wk", "5y"),
    "Monthly": ("1mo", "10y"),
}

# Offline fallback only - the app tries NSE's live F&O list first.
FALLBACK = """360ONE ABB ABCAPITAL ADANIENSOL ADANIENT ADANIGREEN ADANIPORTS ADANIPOWER ALKEM AMBER AMBUJACEM ANGELONE
APLAPOLLO APOLLOHOSP ASHOKLEY ASIANPAINT ASTRAL ATHERENERGY AUBANK AUROPHARMA AXISBANK BAJAJ-AUTO BAJAJFINSV BAJAJHLDNG
BAJFINANCE BANDHANBNK BANKBARODA BANKINDIA BDL BEL BHARATFORG BHARTIARTL BHEL BIOCON BLUESTARCO BOSCHLTD BPCL BRITANNIA
BSE CAMS CANBK CDSL CESC CGPOWER CHOLAFIN CIPLA COALINDIA COCHINSHIP COFORGE COLPAL CONCOR CROMPTON CUMMINSIND DABUR
DALBHARAT DELHIVERY DIVISLAB DIXON DLF DMART DRREDDY EICHERMOT ETERNAL EXIDEIND FEDERALBNK FORCEMOT FORTIS GAIL GLENMARK
GMRAIRPORT GODFRYPHLP GODREJCP GODREJPROP GRASIM HAL HAVELLS HCLTECH HDFCAMC HDFCBANK HDFCLIFE HEROMOTOCO HFCL HINDALCO
HINDPETRO HINDUNILVR HINDZINC HUDCO HYUNDAI ICICIBANK ICICIGI ICICIPRULI IDEA IDFCFIRSTB IEX IGL IIFL INDHOTEL INDIANB
INDIGO INDUSINDBK INDUSTOWER INFY INOXWIND IOC IRCTC IREDA IRFC ITC JINDALSTEL JIOFIN JSWENERGY JSWSTEEL JUBLFOOD
KALYANKJIL KAYNES KEI KFINTECH KOTAKBANK KPITTECH LAURUSLABS LICHSGFIN LICI LODHA LT LTF LTIM LUPIN M&M MANAPPURAM
MANKIND MARICO MARUTI MAXHEALTH MAZDOCK MCX MFSL MOTHERSON MOTILALOFS MPHASIS MUTHOOTFIN NAM-INDIA NATIONALUM NAUKRI
NBCC NCC NESTLEIND NHPC NMDC NTPC NUVAMA NYKAA OBEROIRLTY OFSS OIL ONGC PAGEIND PATANJALI PAYTM PERSISTENT PETRONET
PFC PGEL PIDILITIND PIIND PNB PNBHOUSING POLICYBZR POLYCAB POONAWALLA POWERGRID PPLPHARMA PREMIERENE PRESTIGE RBLBANK
RECLTD RELIANCE RVNL SAGILITY SAIL SAMMAANCAP SBICARD SBILIFE SBIN SHREECEM SHRIRAMFIN SIEMENS SOLARINDS SONACOMS SRF
SUNPHARMA SUPREMEIND SUZLON SWIGGY SYNGENE TATACONSUM TATAELXSI TATAPOWER TATASTEEL TATATECH TCS TECHM TIINDIA TITAN
TMPV TORNTPHARM TRENT TVSMOTOR ULTRACEMCO UNIONBANK UNITDSPR UNOMINDA UPL VBL VEDL VMM VOLTAS WAAREEENER WIPRO YESBANK
ZYDUSLIFE""".split()


_SECTORS = {
    "Private Banks": "AXISBANK BANDHANBNK FEDERALBNK HDFCBANK ICICIBANK IDFCFIRSTB INDUSINDBK KOTAKBANK RBLBANK YESBANK AUBANK",
    "PSU Banks": "BANKBARODA BANKINDIA CANBK INDIANB PNB SBIN UNIONBANK",
    "NBFC & Financials": "ABCAPITAL BAJFINANCE BAJAJFINSV BAJAJHLDNG CHOLAFIN HUDCO IIFL IREDA IRFC JIOFIN LICHSGFIN LTF MANAPPURAM MFSL MUTHOOTFIN PFC PNBHOUSING POONAWALLA RECLTD SAMMAANCAP SBICARD SHRIRAMFIN",
    "Capital Markets": "360ONE ANGELONE BSE CAMS CDSL HDFCAMC IEX KFINTECH MCX MOTILALOFS NAM-INDIA NUVAMA",
    "Insurance": "HDFCLIFE ICICIGI ICICIPRULI LICI SBILIFE",
    "IT & Software": "COFORGE HCLTECH INFY KPITTECH LTIM MPHASIS OFSS PERSISTENT TATAELXSI TATATECH TCS TECHM WIPRO SAGILITY",
    "New-age & Internet": "ETERNAL NYKAA SWIGGY PAYTM POLICYBZR NAUKRI",
    "Automobiles": "ASHOKLEY BAJAJ-AUTO EICHERMOT HEROMOTOCO HYUNDAI M&M MARUTI TMPV TATAMOTORS TVSMOTOR FORCEMOT ATHERENERGY",
    "Auto Ancillaries": "BHARATFORG BOSCHLTD EXIDEIND MOTHERSON SONACOMS TIINDIA UNOMINDA",
    "Pharma & Healthcare": "ALKEM APOLLOHOSP AUROPHARMA BIOCON CIPLA DIVISLAB DRREDDY FORTIS GLENMARK LAURUSLABS LUPIN MANKIND MAXHEALTH PPLPHARMA SYNGENE TORNTPHARM ZYDUSLIFE",
    "FMCG": "BRITANNIA COLPAL DABUR GODREJCP HINDUNILVR ITC MARICO NESTLEIND PATANJALI TATACONSUM UNITDSPR VBL GODFRYPHLP",
    "Metals & Mining": "COALINDIA HINDALCO HINDZINC JINDALSTEL JSWSTEEL NATIONALUM NMDC SAIL TATASTEEL VEDL APLAPOLLO",
    "Oil & Gas": "BPCL GAIL HINDPETRO IGL IOC OIL ONGC PETRONET RELIANCE",
    "Power & Renewables": "ADANIENSOL ADANIGREEN ADANIPOWER CESC JSWENERGY NHPC NTPC POWERGRID TATAPOWER INOXWIND SUZLON WAAREEENER PREMIERENE",
    "Capital Goods": "ABB BHEL CGPOWER CUMMINSIND HAVELLS POLYCAB KEI SIEMENS SOLARINDS SUPREMEIND ASTRAL",
    "Defence": "BDL BEL HAL MAZDOCK COCHINSHIP",
    "Consumer Durables & Electronics": "AMBER BLUESTARCO CROMPTON DIXON KAYNES PGEL VOLTAS HFCL",
    "Retail & Consumer": "DMART TRENT TITAN KALYANKJIL JUBLFOOD VMM PAGEIND INDHOTEL IRCTC",
    "Infrastructure & Construction": "LT NBCC NCC RVNL",
    "Logistics & Transport": "ADANIPORTS CONCOR DELHIVERY GMRAIRPORT INDIGO",
    "Cement": "AMBUJACEM DALBHARAT GRASIM SHREECEM ULTRACEMCO",
    "Realty": "DLF GODREJPROP LODHA OBEROIRLTY PRESTIGE",
    "Telecom": "BHARTIARTL IDEA INDUSTOWER",
    "Chemicals & Paints": "PIDILITIND PIIND SRF UPL ASIANPAINT",
    "Conglomerates": "ADANIENT",
}
SECTOR_OF = {s: sec for sec, names in _SECTORS.items() for s in names.split()}  # unmapped -> "Others"


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def load_universe():
    try:
        r = requests.get(NSE_LOTS_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = [c.strip().upper() for c in df.columns]
        syms = [s.strip().upper() for s in df["SYMBOL"].astype(str)]
        syms = [s for s in syms if s and s not in INDEX_SET and s not in ("SYMBOL", "NAN")]
        syms = list(dict.fromkeys(syms))
        if len(syms) >= 100:
            return syms, "NSE live F&O list"
    except Exception:
        pass
    return FALLBACK, "built-in fallback list (NSE fetch failed)"


# ---------------- Sidebar ----------------
st.sidebar.header("🕒 Timeframes")
sel_tfs = st.sidebar.multiselect("Select one or more", list(TIMEFRAMES), default=["Daily"])
if len(sel_tfs) > 1:
    st.sidebar.caption("Multiple timeframes → a Confluence tab shows stocks matching on all.")

st.sidebar.header("⚙️ Parameters")
rsi_period = st.sidebar.number_input("RSI period", 5, 30, 14)
rsi_bull = st.sidebar.slider("Bullish RSI above", 50, 70, 55)
rsi_bear = st.sidebar.slider("Bearish RSI below", 30, 50, 45)
tk_lookback = st.sidebar.slider("Fresh TK cross within last N candles", 1, 10, 3)
bo_lookback = st.sidebar.slider("Breakout within last N candles", 1, 10, 3,
                                help="A breakout = candle closes beyond the CPR / cloud level after closing on the other side, and still holds beyond it now.")
cpr_narrow = st.sidebar.slider("Narrow CPR width (% of pivot)", 0.05, 1.0, 0.30, step=0.05)
cpr_basis = st.sidebar.radio("CPR based on", ["Daily", "Weekly", "Monthly"], horizontal=True)
cpr_mode = st.sidebar.radio("CPR levels for", ["Current session", "Next session"],
                            help="Current = previous completed period. Next = latest completed period (use after close).")

st.sidebar.markdown("---")
st.sidebar.header("🎯 Conditions (AND)")
direction = st.sidebar.radio("Direction", ["Bullish", "Bearish"], horizontal=True)
c_rsi = st.sidebar.checkbox("RSI confirms direction")
c_cloud = st.sidebar.checkbox("Price above/below Ichimoku cloud")
c_tk = st.sidebar.checkbox("Fresh TK cross in direction")
c_tkstate = st.sidebar.checkbox("Tenkan above/below Kijun (any age)")
c_cpr_narrow = st.sidebar.checkbox("Narrow CPR")
c_cpr_pos = st.sidebar.checkbox("Price above TC / below BC")
st.sidebar.caption("Breakouts (best on intraday timeframes)")
c_cpr_bo = st.sidebar.checkbox("CPR breakout (close above TC / below BC)")
c_cloud_bo = st.sidebar.checkbox("Ichimoku cloud breakout (close above / below cloud)")
bull = direction == "Bullish"
any_filter = any([c_rsi, c_cloud, c_tk, c_tkstate, c_cpr_narrow, c_cpr_pos, c_cpr_bo, c_cloud_bo])

st.sidebar.markdown("---")
st.sidebar.header("📋 Stock universe")
universe, source = load_universe()
mode_u = st.sidebar.radio("Universe", ["All F&O stocks", "Custom list"])
if mode_u == "Custom list":
    txt = st.sidebar.text_area("Symbols (comma/space separated)", "RELIANCE, TCS, SBIN", height=120)
    symbols = [s.strip().upper() for s in txt.replace(",", " ").split() if s.strip()]
else:
    symbols = universe
    st.sidebar.caption(f"{len(symbols)} stocks • source: {source}")

all_secs = sorted({SECTOR_OF.get(s, "Others") for s in symbols})
sel_secs = st.sidebar.multiselect("Sectors", all_secs, default=all_secs)
symbols = [s for s in symbols if SECTOR_OF.get(s, "Others") in sel_secs]
st.sidebar.caption(f"Scanning {len(symbols)} stocks in {len(sel_secs)} sector(s)")

st.sidebar.markdown("---")
auto = st.sidebar.checkbox("Auto-refresh")
auto_secs = st.sidebar.number_input("Every (seconds)", 30, 900, 120, step=30)
if st.sidebar.button("🔄 Refresh now"):
    st.cache_data.clear()

if not sel_tfs:
    st.warning("Select at least one timeframe in the sidebar.")
    st.stop()
if not symbols:
    st.warning("No stocks selected. Pick at least one sector or symbol.")
    st.stop()
tickers = [f"{s}.NS" for s in symbols]


# ---------------- Data ----------------
def flatten(df):
    if isinstance(df.columns, pd.MultiIndex):
        for lvl in range(df.columns.nlevels):
            if "Close" in df.columns.get_level_values(lvl):
                df = df.copy()
                df.columns = df.columns.get_level_values(lvl)
                break
    return df


@st.cache_data(ttl=120, show_spinner=False)
def download_raw(tickers_t, interval, period):
    out = {}
    tk = list(tickers_t)
    for i in range(0, len(tk), 40):
        chunk = tk[i:i + 40]
        try:
            data = yf.download(chunk, period=period, interval=interval, group_by="ticker",
                               auto_adjust=False, progress=False, threads=True)
        except Exception:
            continue
        for t in chunk:
            try:
                df = flatten(data[t] if len(chunk) > 1 else data)
                df = df[["Open", "High", "Low", "Close"]].dropna()
                if len(df):
                    out[t] = df
            except Exception:
                pass
    return out


def to_4h(df):
    return df.resample("4h", offset="1h15min").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()


def get_tf_data(tf):
    interval, period = TIMEFRAMES[tf]
    raw = download_raw(tuple(tickers), interval, period)
    if tf == "4 Hour":
        raw = {t: to_4h(d) for t, d in raw.items()}
    return raw


# ---------------- Indicators ----------------
def wilder_rsi(close, n):
    d = close.diff()
    gain = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(100)


def cpr_levels(daily):
    d = daily.copy()
    if d.index.tz is not None:
        d.index = d.index.tz_localize(None)
    freq = {"Daily": "D", "Weekly": "W-FRI", "Monthly": "M"}[cpr_basis]
    g = d.groupby(d.index.to_period(freq)).agg({"High": "max", "Low": "min", "Close": "last"})
    if len(g) < 2:
        return None
    now = datetime.now(IST)
    today = now.date()
    end = g.index[-1].end_time.date()
    ongoing = end >= today
    completed = end < today or (end == today and now.hour >= 16)
    if cpr_mode == "Current session":
        i = -2 if ongoing else -1
    else:
        i = -1 if completed else -2
    s = g.iloc[i]
    pivot = (s["High"] + s["Low"] + s["Close"]) / 3
    bc_raw = (s["High"] + s["Low"]) / 2
    tc_raw = 2 * pivot - bc_raw
    return float(pivot), float(max(tc_raw, bc_raw)), float(min(tc_raw, bc_raw))


def analyse(df, cpr):
    hi, lo, cl = df["High"], df["Low"], df["Close"]
    rsi = wilder_rsi(cl, rsi_period)
    tenkan = (hi.rolling(9).max() + lo.rolling(9).min()) / 2
    kijun = (hi.rolling(26).max() + lo.rolling(26).min()) / 2
    span_a = ((tenkan + kijun) / 2).shift(26)
    span_b = ((hi.rolling(52).max() + lo.rolling(52).min()) / 2).shift(26)

    spread = tenkan - kijun
    bcross = bool(((spread.shift(1) <= 0) & (spread > 0)).tail(tk_lookback).any())
    scross = bool(((spread.shift(1) >= 0) & (spread < 0)).tail(tk_lookback).any())

    ltp, prev = float(cl.iloc[-1]), float(cl.iloc[-2])
    a, b = float(span_a.iloc[-1]), float(span_b.iloc[-1])
    cloud_ok = not (np.isnan(a) or np.isnan(b))
    above = cloud_ok and ltp > max(a, b)
    below = cloud_ok and ltp < min(a, b)
    tk_ok = not np.isnan(spread.iloc[-1])

    cl_prev = cl.shift(1)
    top = pd.concat([span_a, span_b], axis=1).max(axis=1, skipna=False)
    bot = pd.concat([span_a, span_b], axis=1).min(axis=1, skipna=False)
    cloud_bo_bull = bool(((cl_prev <= top.shift(1)) & (cl > top)).tail(bo_lookback).any()) and bool(above)
    cloud_bo_bear = bool(((cl_prev >= bot.shift(1)) & (cl < bot)).tail(bo_lookback).any()) and bool(below)

    def bo_label(bu, be):
        return "Bullish ↑ 🚀" if bu else "Bearish ↓ 🔻" if be else "—"
    tk_bull = tk_ok and spread.iloc[-1] > 0

    row = {
        "LTP": round(ltp, 2),
        "Chg %": round((ltp / prev - 1) * 100, 2),
        "RSI": round(float(rsi.iloc[-1]), 1),
        "TK": "N/A" if not tk_ok else "Bull Cross 🔥" if bcross else "Bear Cross 🔻" if scross
              else ("Bullish" if tk_bull else "Bearish"),
        "Cloud": "N/A" if not cloud_ok else "Above 🟢" if above else "Below 🔴" if below else "Inside ⚪",
        "Cloud Breakout": bo_label(cloud_bo_bull, cloud_bo_bear),
        "_cloud_bo_bull": cloud_bo_bull, "_cloud_bo_bear": cloud_bo_bear,
        "_rsi": float(rsi.iloc[-1]), "_above": above, "_below": below,
        "_bcross": bcross, "_scross": scross, "_tkbull": tk_bull, "_tkok": tk_ok, "_ltp": ltp,
    }
    if cpr:
        pivot, tc, bc = cpr
        w = (tc - bc) / pivot * 100
        cpr_bo_bull = bool(((cl_prev <= tc) & (cl > tc)).tail(bo_lookback).any()) and ltp > tc
        cpr_bo_bear = bool(((cl_prev >= bc) & (cl < bc)).tail(bo_lookback).any()) and ltp < bc
        row.update({
            "CPR Breakout": bo_label(cpr_bo_bull, cpr_bo_bear),
            "_cpr_bo_bull": cpr_bo_bull, "_cpr_bo_bear": cpr_bo_bear,
            "CPR Width %": round(w, 3),
            "CPR": "Narrow" if w <= cpr_narrow else "Wide",
            "CPR Pos": "Above CPR" if ltp > tc else "Below CPR" if ltp < bc else "Inside CPR",
            "Pivot": round(pivot, 2), "TC": round(tc, 2), "BC": round(bc, 2),
            "_narrow": w <= cpr_narrow, "_tc": tc, "_bc": bc,
        })
    else:
        row.update({"_narrow": False, "_tc": np.nan, "_bc": np.nan, "CPR Breakout": "—",
                    "_cpr_bo_bull": False, "_cpr_bo_bear": False})
    return row


def match(r):
    c = []
    if c_rsi:
        c.append(r["_rsi"] > rsi_bull if bull else r["_rsi"] < rsi_bear)
    if c_cloud:
        c.append(r["_above"] if bull else r["_below"])
    if c_tk:
        c.append(r["_bcross"] if bull else r["_scross"])
    if c_tkstate:
        c.append(r["_tkok"] and (r["_tkbull"] if bull else not r["_tkbull"]))
    if c_cpr_narrow:
        c.append(r["_narrow"])
    if c_cpr_pos:
        c.append(bool(r["_ltp"] > r["_tc"]) if bull else bool(r["_ltp"] < r["_bc"]))
    if c_cpr_bo:
        c.append(r["_cpr_bo_bull"] if bull else r["_cpr_bo_bear"])
    if c_cloud_bo:
        c.append(r["_cloud_bo_bull"] if bull else r["_cloud_bo_bear"])
    return bool(c) and all(c)


# ---------------- Run ----------------
with st.spinner("Loading daily data for CPR..."):
    daily_raw = download_raw(tuple(tickers), "1d", "1y")
cprs = {}
for s, t in zip(symbols, tickers):
    try:
        cprs[s] = cpr_levels(daily_raw[t])
    except Exception:
        cprs[s] = None

results, failed_by_tf = {}, {}
for tf in sel_tfs:
    with st.spinner(f"Scanning {tf}..."):
        data = get_tf_data(tf)
    rows, failed = [], []
    for s, t in zip(symbols, tickers):
        df = data.get(t)
        if df is None or len(df) < MIN_ROWS:
            failed.append(s)
            continue
        try:
            rows.append({"Symbol": s, "Sector": SECTOR_OF.get(s, "Others"), **analyse(df, cprs.get(s))})
        except Exception:
            failed.append(s)
    res = pd.DataFrame(rows)
    if not res.empty:
        res["Signal"] = res.apply(lambda r: "🚨 MATCH" if match(r) else "", axis=1)
    results[tf], failed_by_tf[tf] = res, failed


def show_table(tf):
    res = results[tf]
    if res.empty:
        st.error(f"No data for {tf}. Yahoo may be rate-limiting or the market is closed for this interval.")
        return
    m = res[res["Signal"] != ""]
    if any_filter:
        if len(m):
            st.success(f"{len(m)} {direction.lower()} match(es): " + ", ".join(m["Symbol"]))
        else:
            st.info("No stocks match all selected conditions.")
    only = st.toggle("Matches only", key=f"only_{tf}")
    view = m if (only and any_filter) else res
    cols = [c for c in view.columns if not c.startswith("_")]
    view = view[cols].sort_values(["Signal", "RSI"], ascending=[False, False])
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.download_button("⬇️ CSV", view.to_csv(index=False), f"fno_{tf.replace(' ', '')}.csv",
                       "text/csv", key=f"dl_{tf}")
    if failed_by_tf[tf]:
        st.caption(f"No/insufficient data ({len(failed_by_tf[tf])}): " + ", ".join(failed_by_tf[tf]))


if not any_filter:
    st.info("Tick conditions in the sidebar to activate the scanner.")


def show_sectors():
    tf = st.selectbox("Timeframe for sector view", sel_tfs, key="sec_tf")
    res = results[tf]
    if res.empty:
        st.error(f"No data for {tf}.")
        return
    g = res.groupby("Sector")
    summ = pd.DataFrame({
        "Stocks": g.size(),
        "Avg Chg %": g["Chg %"].mean().round(2),
        "Avg RSI": g["RSI"].mean().round(1),
        "% RSI > bull": (g["_rsi"].apply(lambda x: (x > rsi_bull).mean()) * 100).round(0),
        "% Above Cloud": (g["_above"].mean() * 100).round(0),
        "% TK Bullish": (g["_tkbull"].mean() * 100).round(0),
        "Matches": g["Signal"].apply(lambda x: (x != "").sum()),
    }).sort_values("Avg Chg %", ascending=False).reset_index()
    st.caption("Sector breadth: strongest sectors first (by average % change on this timeframe).")
    st.bar_chart(summ.set_index("Sector")["Avg Chg %"])
    st.dataframe(summ, use_container_width=True, hide_index=True)
    pick = st.selectbox("Drill into sector", ["All"] + list(summ["Sector"]), key="sec_pick")
    if pick != "All":
        d = res[res["Sector"] == pick]
        cols = [c for c in d.columns if not c.startswith("_")]
        st.dataframe(d[cols].sort_values("RSI", ascending=False), use_container_width=True, hide_index=True)


def show_confluence():
    conf = None
    for tf in sel_tfs:
        r = results[tf]
        if r.empty:
            continue
        part = r[["Symbol", "Signal"]].rename(columns={"Signal": tf})
        part[tf] = part[tf].map(lambda x: "✅" if x else "—")
        conf = part if conf is None else conf.merge(part, on="Symbol", how="outer")
    if conf is None or not any_filter:
        st.info("Enable conditions to see confluence.")
        return
    conf = conf.fillna("—")
    conf["Matched"] = conf[sel_tfs].apply(lambda r: (r == "✅").sum(), axis=1)
    conf["All TFs"] = np.where(conf["Matched"] == len(sel_tfs), "🚨 ALL", "")
    base = next((results[t] for t in sel_tfs if not results[t].empty), None)
    if base is not None:
        conf = conf.merge(base[["Symbol", "Sector", "LTP", "RSI"]], on="Symbol", how="left")
    conf = conf.sort_values("Matched", ascending=False)
    full = conf[conf["All TFs"] != ""]
    if len(full):
        st.success(f"{len(full)} stock(s) match on ALL timeframes: " + ", ".join(full["Symbol"]))
        st.toast("Confluence match found!", icon="🚨")
    st.dataframe(conf, use_container_width=True, hide_index=True)


labels = ["🏭 Sectors"] + (["🎯 Confluence"] if len(sel_tfs) > 1 else []) + sel_tfs
tabs = st.tabs(labels)
with tabs[0]:
    show_sectors()
idx = 1
if len(sel_tfs) > 1:
    with tabs[1]:
        show_confluence()
    idx = 2
for tab, tf in zip(tabs[idx:], sel_tfs):
    with tab:
        show_table(tf)

st.caption(f"Updated {datetime.now(IST):%d %b %Y %H:%M IST} • Yahoo Finance data (may be delayed) • Not investment advice.")

if auto:
    time.sleep(int(auto_secs))
    st.cache_data.clear()
    st.rerun()
