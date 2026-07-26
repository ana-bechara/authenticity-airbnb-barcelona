"""
Barcelona Authenticity Ranking - Interactive Demo
Run:
    pip install streamlit folium streamlit-folium pandas plotly
    streamlit run app.py
Files needed: listings_scored.csv, top100_reviews.json
"""

import json
import pandas as pd
import plotly.graph_objects as go
import folium
import streamlit as st
from streamlit_folium import st_folium

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter','Helvetica Neue',sans-serif; }
  h1 { color: #FF5A5F !important; }
  h2, h3, h4 { color: #222 !important; }
  button[data-baseweb="tab"][aria-selected="true"] {
    color: #FF5A5F !important; border-bottom: 2px solid #FF5A5F !important;
  }
  [data-testid="metric-container"] {
    background:#fff; border:1px solid #ebebeb; border-radius:12px;
    padding:14px 18px; box-shadow:0 2px 8px rgba(0,0,0,.06);
  }
  [data-testid="metric-container"] label { color:#717171 !important; font-size:12px !important; }
  [data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size:22px !important; font-weight:600 !important; color:#222 !important;
  }
  [data-testid="stSidebar"] { background:#f7f7f7; }
  details summary { color:#FF5A5F !important; font-weight:600; }
  .stAlert { border-radius:10px !important; }
  hr { border-color:#ebebeb !important; }
</style>
""", unsafe_allow_html=True)

# ── Config ────────────────────────────────────────────────────────────────────
DATA_PATH    = "listings_scored.csv"
REVIEWS_PATH = "top100_reviews.json"
TOP_K = 100
TOP_N = 10

C_RISER  = "#2a9d8f"
C_FALLER = "#e76f51"
C_STABLE = "#264653"
C_TOP10F = "#FF5A5F"
C_TOP10B = "#457b9d"
C_TOPK   = "#a8c5da"
C_GREY   = "#bbbbbb"   # was all-listings colour, now base-only
C_ALL    = "#e07b39"   # was grey, now more visible warm tone for all listings

SUBSCORE_COLS   = ["host_quality_subscore","review_quality_subscore","context_subscore",
                   "sbert_text_score","host_authenticity_subscore_derived"]
SUBSCORE_LABELS = ["★ Host quality","★ Review quality","★ Context","★ SBERT text","★ Host auth"]

st.set_page_config(page_title="Barcelona Authenticity Ranking",
                   page_icon="🏘️", layout="wide")

# ── Load ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    df["host_is_superhost"] = df["host_is_superhost"].fillna(0).astype(int)
    # host_authenticity_subscore was not exported to CSV but can be derived:
    # authenticity_score = 0.50 * sbert_text_score + 0.50 * host_auth
    # => host_auth = (authenticity_score - 0.50 * sbert_text_score) / 0.50
    mask = df["authenticity_score"].notna() & df["sbert_text_score"].notna()
    df["host_authenticity_subscore_derived"] = float("nan")
    df.loc[mask, "host_authenticity_subscore_derived"] = (
        (df.loc[mask,"authenticity_score"] - 0.50 * df.loc[mask,"sbert_text_score"]) / 0.50
    )
    return df

@st.cache_data
def load_reviews(path):
    try:
        with open(path,"r",encoding="utf-8") as f:
            return {int(k):v for k,v in json.load(f).items()}
    except FileNotFoundError:
        return {}

with st.spinner("Loading data…"):
    df_full  = load_data(DATA_PATH)
    reviews  = load_reviews(REVIEWS_PATH)

TOTAL = len(df_full)
ALL_DISTRICTS = sorted(df_full["neighbourhood_group_cleansed"].dropna().unique())

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("# 🏘️ Barcelona Authenticity Ranking")
st.markdown(
    "<p style='font-size:15px;color:#555;margin-top:-12px;margin-bottom:20px'>"
    "A knowledge-based recommender that surfaces locally-run Airbnb listings "
    "over commercially managed ones - ranked by quality <em>and</em> authenticity.</p>",
    unsafe_allow_html=True,
)

# ── Session state defaults ────────────────────────────────────────────────────
DEFAULTS = dict(guests=2, min_nights=4, sup_only=False,
                min_rating=1.0, max_host_listings=50, auth_weight=0.30,
                view="Base ranking")
for k,v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v
for d in ALL_DISTRICTS:
    if f"dist_{d}" not in st.session_state:
        st.session_state[f"dist_{d}"] = True

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("# 🔍 Filters & Weights")
st.sidebar.caption(
    "Set your trip profile. The system filters listings that don't match, "
    "then ranks the best 100 by quality and authenticity."
)

if st.sidebar.button("↺ Reset all filters to default", use_container_width=True):
    for k,v in DEFAULTS.items():
        st.session_state[k] = v
    for d in ALL_DISTRICTS:
        st.session_state[f"dist_{d}"] = True
    st.rerun()

st.sidebar.markdown("### Trip profile")
guests     = st.sidebar.slider("Guests", 1, int(df_full["accommodates"].max()),
                                key="guests")
all_room_types = sorted(df_full["room_type"].dropna().unique())
sel_room_types = st.sidebar.multiselect(
    "Room type (leave empty for all)",
    all_room_types,
    default=[],
    key="room_types",
    help="Select one or more room types. Leave empty to include all types."
)
min_nights = st.sidebar.slider("Minimum stay (nights)", 1, 30, key="min_nights")
sup_only   = st.sidebar.checkbox("Superhost only", key="sup_only")

st.sidebar.markdown("### Further filters")
st.sidebar.markdown("**Districts**")
col_a, col_b = st.sidebar.columns(2)
if col_a.button("✓ All",  key="sel_all",  use_container_width=True):
    for d in ALL_DISTRICTS: st.session_state[f"dist_{d}"] = True
    st.rerun()
if col_b.button("✗ None", key="sel_none", use_container_width=True):
    for d in ALL_DISTRICTS: st.session_state[f"dist_{d}"] = False
    st.rerun()
sel_districts = []
for d in ALL_DISTRICTS:
    if st.sidebar.checkbox(d, key=f"dist_{d}"):
        sel_districts.append(d)

min_rating = st.sidebar.slider(
    "Minimum Airbnb guest rating (1–5)", 1.0, 5.0, step=0.1,
    key="min_rating",
    help="Filters on review_scores_rating - the aggregated guest rating from Airbnb."
)
max_host_listings = st.sidebar.slider(
    "Max host listings (1 = individual host only)", 1, 50,
    key="max_host_listings"
)

st.sidebar.markdown("### Ranking weight")
auth_weight = st.sidebar.slider(
    "Authenticity weight in final score", 0.00, 1.00, step=0.05,
    key="auth_weight",
    help="Final score = (1−w)×base + w×auth. Only affects Stage 3 scored listings."
)
base_weight = round(1.0 - auth_weight, 2)
st.sidebar.caption(f"Final = **{base_weight}** × base + **{auth_weight}** × auth")

# ── Filter & rank ─────────────────────────────────────────────────────────────
df_f = df_full.copy()
df_f = df_f[df_f["accommodates"] >= guests]
df_f = df_f[df_f["minimum_minimum_nights"] <= min_nights]
if sel_room_types:
    df_f = df_f[df_f["room_type"].isin(sel_room_types)]
if sup_only:
    df_f = df_f[df_f["host_is_superhost"] == 1]
if sel_districts:
    df_f = df_f[df_f["neighbourhood_group_cleansed"].isin(sel_districts)]
df_f = df_f[df_f["review_scores_rating"] >= min_rating]
df_f = df_f[df_f["calculated_host_listings_count"] <= max_host_listings]

df_base = (
    df_f.nlargest(TOP_K, "base_score_default")
    .reset_index(drop=True)
    .assign(base_rank=range(1, min(TOP_K, len(df_f))+1))
)
n_s3 = df_base["authenticity_score"].notna().sum()
df_base = df_base.copy()
df_base["final_score_dynamic"] = (
    base_weight * df_base["base_score_default"] +
    auth_weight * df_base["authenticity_score"].fillna(df_base["base_score_default"])
)

if n_s3 > 0:
    # Listings WITH auth scores are sorted by final_score_dynamic (base + auth signal).
    # Listings WITHOUT auth scores are sorted by base_score_default and appended
    # below - they must not appear in the final Top-10 since they were never
    # re-ranked by authenticity.
    scored_mask   = df_base["authenticity_score"].notna()
    df_scored     = (df_base[scored_mask]
                     .sort_values("final_score_dynamic", ascending=False)
                     .reset_index(drop=True))
    df_unscored   = (df_base[~scored_mask]
                     .sort_values("base_score_default", ascending=False)
                     .reset_index(drop=True))
    df_final      = pd.concat([df_scored, df_unscored], ignore_index=True)
    df_final["final_rank"] = range(1, len(df_final)+1)
else:
    df_final = df_base.assign(final_rank=df_base["base_rank"])

base_top10  = set(df_base.nlargest(TOP_N,"base_score_default")["id"])
final_top10 = set(df_final.head(TOP_N)["id"])
stable  = base_top10 & final_top10
entered = final_top10 - base_top10
exited  = base_top10 - final_top10

rank_map = {}
for _, row in df_base.iterrows():
    lid = row["id"]
    fr  = df_final[df_final["id"]==lid]
    rank_map[lid] = (
        int(row["base_rank"]),
        int(fr["final_rank"].iloc[0]) if len(fr) else int(row["base_rank"])
    )

top10_rows = df_final.head(TOP_N)
MAP_CENTER = ([top10_rows["latitude"].mean(), top10_rows["longitude"].mean()]
              if len(top10_rows) else [41.4035, 2.1560])

# ── Map helpers ───────────────────────────────────────────────────────────────
def make_icon(shape, colour, size=13):
    if shape == "triangle-up":
        css = (f"width:0;height:0;border-left:{size//2}px solid transparent;"
               f"border-right:{size//2}px solid transparent;"
               f"border-bottom:{size}px solid {colour};")
    elif shape == "triangle-down":
        css = (f"width:0;height:0;border-left:{size//2}px solid transparent;"
               f"border-right:{size//2}px solid transparent;"
               f"border-top:{size}px solid {colour};")
    elif shape == "square":
        css = f"width:{size}px;height:{size}px;background:{colour};"
    else:
        css = f"width:{size}px;height:{size}px;border-radius:50%;background:{colour};"
    return folium.DivIcon(html=f"<div style='{css}'></div>",
                          icon_size=(size,size), icon_anchor=(size//2,size//2))

def pin_style(lid, rank, is_final, scored):
    if is_final:
        if lid in entered: return "triangle-up",   C_RISER,  16
        if lid in exited:  return "triangle-down",  C_FALLER, 16
        if lid in stable:  return "square",          C_STABLE, 14
        if rank <= TOP_N:  return "circle",          C_TOP10F, 10
        if scored:         return "circle",          C_TOPK,    7
        return               "circle",               C_GREY,    6
    else:
        if lid in base_top10: return "circle", C_TOP10B, 10
        if scored:            return "circle", C_TOPK,    7
        return                "circle",        C_GREY,    6

def make_popup(row, br, fr):
    scored = pd.notna(row.get("authenticity_score"))
    name   = str(row.get("name","") or "")
    url    = str(row.get("listing_url","") or "")
    sup    = "Yes ✅" if row["host_is_superhost"] else "No"
    url_btn = (f"<a href='{url}' target='_blank' style='display:inline-block;"
               f"padding:5px 12px;background:#FF5A5F;color:white;border-radius:6px;"
               f"font-size:11px;text-decoration:none;font-weight:600'>"
               f"View on Airbnb ↗</a>" if url else "")
    auth_str = (
        f"<b>★ Auth:</b> {row['authenticity_score']:.3f} "
        f"(★ text {row['sbert_text_score']:.2f} · "
        f"★ host auth {row.get('host_authenticity_subscore_derived', float('nan')):.2f})<br>"
        f"<b>★ Final:</b> {row['final_score_dynamic']:.3f} "
        f"({base_weight}×base + {auth_weight}×auth)"
        if scored else
        "<span style='color:#aaa'>Auth score not available for this listing</span>"
    )
    return f"""
    <div style='font-family:Inter,sans-serif;font-size:12px;min-width:240px;max-width:290px'>
      <b style='font-size:13px;color:#222'>{name[:55]}</b><br>
      <span style='color:#717171'>{row['neighbourhood_cleansed']}</span>
      <div style='margin:7px 0'>{url_btn}</div>
      <hr style='border-color:#ebebeb;margin:6px 0'>
      <span style='font-size:10px;color:#717171;text-transform:uppercase;letter-spacing:.5px'>From the data</span><br>
      <b>Room:</b> {row['room_type']} · {int(row['accommodates'])} guests<br>
      <b>Superhost:</b> {sup} · <b>Rating:</b> {row['review_scores_rating']:.2f} ⭐<br>
      <b>Host listings:</b> {int(row['calculated_host_listings_count'])}<br>
      <hr style='border-color:#ebebeb;margin:6px 0'>
      <span style='font-size:10px;color:#717171;text-transform:uppercase;letter-spacing:.5px'>Computed scores</span><br>
      <b>★ Base:</b> {row['base_score_default']:.3f}
      (★ host {row['host_quality_subscore']:.2f} · ★ review {row['review_quality_subscore']:.2f}
       · ★ context {row['context_subscore']:.2f})<br>
      {auth_str}
    </div>"""

def build_map(data, rank_col, is_final, center, zoom=15):
    m = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB positron")
    if show_all:
        samp = df_full.sample(min(5000,len(df_full)), random_state=42)
        for _, r in samp.iterrows():
            folium.CircleMarker([r["latitude"],r["longitude"]], radius=2,
                color=C_ALL, fill=True, fill_color=C_ALL,
                fill_opacity=0.5, weight=0).add_to(m)
    for _, row in data.iterrows():
        lid    = row["id"]
        rank   = int(row[rank_col])
        scored = pd.notna(row.get("authenticity_score"))
        br, fr = rank_map.get(lid,(rank,rank))
        shape, colour, size = pin_style(lid, rank, is_final, scored)
        folium.Marker(
            location=[row["latitude"],row["longitude"]],
            icon=make_icon(shape,colour,size),
            popup=folium.Popup(make_popup(row,br,fr), max_width=300),
            tooltip=(
                f"{'▲ ' if lid in entered else '▼ ' if lid in exited else ''}"
                f"Base rank: #{br} → Final rank: #{fr} · {row['neighbourhood_cleansed']}"
            ),
        ).add_to(m)

    if is_final:
        items = [
            (C_RISER,  "triangle-up",   "Entered Top-10 after auth re-ranking"),
            (C_FALLER, "triangle-down",  "Exited Top-10 after auth re-ranking"),
            (C_STABLE, "square",         "Stable in both Top-10s"),
            (C_TOPK,   "circle",         "Top-100 with auth score"),
            (C_GREY,   "circle",         "Top-100 base score only"),
        ]
    else:
        items = [
            (C_TOP10B, "circle", "Top-10 base ranking"),
            (C_TOPK,   "circle", "Top-100 with auth score"),
            (C_GREY,   "circle", "Top-100 base score only"),
        ]
    if show_all:
        items.append((C_ALL,"circle","All listings"))

    def icon_html(shape, colour):
        s = 10
        if shape=="triangle-up":
            return (f"<div style='width:0;height:0;display:inline-block;"
                    f"border-left:{s//2}px solid transparent;"
                    f"border-right:{s//2}px solid transparent;"
                    f"border-bottom:{s}px solid {colour};margin-right:5px'></div>")
        if shape=="triangle-down":
            return (f"<div style='width:0;height:0;display:inline-block;"
                    f"border-left:{s//2}px solid transparent;"
                    f"border-right:{s//2}px solid transparent;"
                    f"border-top:{s}px solid {colour};margin-right:5px'></div>")
        if shape=="square":
            return (f"<div style='width:{s}px;height:{s}px;display:inline-block;"
                    f"background:{colour};margin-right:5px;vertical-align:middle'></div>")
        return (f"<div style='width:{s}px;height:{s}px;border-radius:50%;"
                f"display:inline-block;background:{colour};"
                f"margin-right:5px;vertical-align:middle'></div>")

    rows_html = "".join(
        f"<div style='display:flex;align-items:center;margin:3px 0'>"
        f"{icon_html(sh,c)}<span>{lbl}</span></div>"
        for c,sh,lbl in items
    )
    m.get_root().html.add_child(folium.Element(
        f"<div style='position:fixed;bottom:30px;right:10px;z-index:1000;"
        f"background:white;padding:12px 16px;border-radius:12px;"
        f"font-family:Inter,sans-serif;font-size:12px;"
        f"box-shadow:0 2px 12px rgba(0,0,0,.12)'>"
        f"<b style='font-size:13px'>Legend</b><br><br>{rows_html}"
        f"<div style='color:#aaa;font-size:10px;margin-top:6px'>"
        f"Hover: Base rank → Final rank</div></div>"
    ))
    return m

# ── Plotly helpers ────────────────────────────────────────────────────────────
def make_scatter(df_t100):
    def membership(lid):
        if lid in entered:     return "Entered Top-10"
        if lid in exited:      return "Exited Top-10"
        if lid in stable:      return "Stable Top-10"
        if lid in final_top10: return "Final Top-10"
        if lid in base_top10:  return "Base Top-10"
        return "Rest of Top-100"

    df_p = df_t100.dropna(subset=["authenticity_score"]).copy()
    df_p["group"]      = df_p["id"].apply(membership)
    df_p["name_short"] = df_p["name"].str[:35].fillna("")
    df_p["br"]         = df_p["id"].apply(lambda x: rank_map.get(x,(0,0))[0])
    df_p["fr"]         = df_p["id"].apply(lambda x: rank_map.get(x,(0,0))[1])

    style_map = {
        "Entered Top-10":  (C_RISER,  "triangle-up",   12),
        "Exited Top-10":   (C_FALLER, "triangle-down",  12),
        "Stable Top-10":   (C_STABLE, "square",         12),
        "Final Top-10":    (C_TOP10F, "circle",         10),
        "Base Top-10":     (C_TOP10B, "circle",         10),
        "Rest of Top-100": (C_TOPK,   "circle",          8),
    }

    fig = go.Figure()
    for group, (colour, symbol, msize) in style_map.items():
        sub = df_p[df_p["group"]==group]
        if len(sub)==0: continue
        fig.add_trace(go.Scatter(
            x=sub["base_score_default"], y=sub["authenticity_score"],
            mode="markers", name=group,
            marker=dict(color=colour, symbol=symbol, size=msize,
                        line=dict(width=1,color="white")),
            customdata=sub[["name_short","br","fr","neighbourhood_cleansed"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>%{customdata[3]}<br>"
                "Base rank: #%{customdata[1]} → Final rank: #%{customdata[2]}<br>"
                "Base: %{x:.3f}  Auth: %{y:.3f}<extra></extra>"
            ),
        ))

    mean_base = df_p["base_score_default"].mean()
    mean_auth = df_p["authenticity_score"].mean()
    fig.add_vline(x=mean_base, line_dash="dot", line_color="#aaa",
                  annotation_text=f"Mean base ({mean_base:.3f})",
                  annotation_position="top")
    fig.add_hline(y=mean_auth, line_dash="dot", line_color="#aaa",
                  annotation_text=f"Mean auth ({mean_auth:.3f})",
                  annotation_position="right")
    fig.update_layout(
        title="Base score vs Authenticity score - Top-100",
        xaxis_title="Base score", yaxis_title="Authenticity score",
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Inter, sans-serif"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0")
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig

def make_radar(row):
    # Use derived host_authenticity_subscore (exact reverse of scoring formula)
    vals = []
    for col in SUBSCORE_COLS:
        v = row.get(col)
        vals.append(float(v) if pd.notna(v) else 0.0)
    means = [float(df_base[col].mean()) if col in df_base.columns else 0.0
             for col in SUBSCORE_COLS]
    labels = SUBSCORE_LABELS + [SUBSCORE_LABELS[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=means+[means[0]], theta=labels, fill="toself", name="Top-100 mean",
        fillcolor="rgba(168,197,218,0.3)", line=dict(color=C_TOPK,width=1.5),
    ))
    fig.add_trace(go.Scatterpolar(
        r=vals+[vals[0]], theta=labels, fill="toself",
        name=str(row.get("name","Selected"))[:30],
        fillcolor="rgba(255,90,95,0.2)", line=dict(color=C_TOP10F,width=2),
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,1])),
        showlegend=True, height=400,
        title="Subscore profile vs Top-100 mean",
        font=dict(family="Inter, sans-serif"), paper_bgcolor="white",
    )
    return fig, vals

def make_t10(ids, rank_label):
    rows = []
    for i, lid in enumerate(ids,1):
        r = df_base[df_base["id"]==lid]
        if not len(r): continue
        r = r.iloc[0]
        status = ("🟢 entered final" if lid in entered else
                  "🔴 exited final"  if lid in exited  else "⚫ stable")
        rows.append({
            rank_label: i,
            "Name": str(r.get("name","") or "")[:40],
            "Neighbourhood": r["neighbourhood_cleansed"],
            "Host listings": int(r["calculated_host_listings_count"]),
            "★ Base score": round(float(r["base_score_default"]),3),
            "★ Auth score": (round(float(r["authenticity_score"]),3)
                           if pd.notna(r.get("authenticity_score")) else "n/a"),
            "Status": status,
            "URL": str(r.get("listing_url","") or ""),
        })
    return pd.DataFrame(rows)

# ── Session state: persist view selection across reruns ───────────────────────
if "view" not in st.session_state:
    st.session_state["view"] = "Base ranking"

# ══════════════════════════════════════════════════════════════════════════════
# TABS - use session_state to track active tab and prevent reset
# ══════════════════════════════════════════════════════════════════════════════
tab_intro, tab_map, tab_analysis, tab_table, tab_compare = st.tabs(
    ["📖 About","🗺️ Map & Results","📈 Analysis","📋 Table","📊 Comparison"])

# ── ABOUT ─────────────────────────────────────────────────────────────────────
with tab_intro:
    st.markdown("## Why authenticity?")
    st.markdown("""
Short-term rental platforms serve a wide range of travellers, and not all of them are
looking for the same experience. For guests who want something beyond a well-rated
apartment - a stay that feels genuinely rooted in the city, with a host who knows the
neighbourhood and a street where people actually live - standard ranking systems make
that hard to find. Existing algorithms optimise for conversion signals that commercial
multi-listing operators can match as well as any individual host, pushing locally-embedded
listings down in visibility regardless of their quality.

This system offers an **optional** authenticity layer on top of quality ranking. It
reorders results to favour **individual hosts** over portfolio operators, hosts
**resident in Barcelona** over remote managers, and listings whose **review language**
reflects genuine local life rather than a managed short stay. The authenticity weight
is fully adjustable: set it to zero and you get a pure quality ranking; increase it
and authenticity progressively shapes the results.

The approach also addresses a broader structural problem. Barcelona faces severe
overtourism pressure concentrated in a handful of central districts, driven in part
by the dominance of commercial operators in the most visible search positions. By making
locally-run listings more discoverable, this system redistributes visibility - and
potentially revenue - toward individual residents rather than large operators. In a city
where short-term rental licences expire from 2028 onwards, a platform that can credibly
surface authentic, locally-hosted stays has a clear differentiating proposition - and a
meaningful contribution to make to the communities it operates in.
    """)
    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### How it works")
        st.markdown("""
**Stage 1 - Pre-filter**: removes listings not matching the trip profile
(guests, room type, minimum stay, district, rating, host scale).

**Stage 2 - Base ranking**: scores all eligible listings on host quality (0.30),
review quality (0.40), and neighbourhood context (0.30). Selects Top-100 candidates.

**Stage 3 - Final ranking**: re-ranks the Top-100 using an authenticity score
combining Sentence-BERT (SBERT) review semantics (0.50) and host structural
signals (0.50).

**Final score** = (1−w) × base score + w × authenticity score,
where w is the **authenticity weight** slider in the sidebar (default 0.30).
        """)

    with c2:
        st.markdown("### Score breakdown")
        st.markdown("""
**Base score** = 0.30 × host quality + 0.40 × review quality + 0.30 × context

| Subscore | Features and weights |
|---|---|
| Host quality | Equal mean of: response rate, acceptance rate, superhost status, response time, identity verified, bathrooms per guest |
| Review quality | 0.70 × rating + 0.30 × reviews in last 12 months |
| Context | Equal mean of: transport stop proximity (250m), Points of Interest proximity (500m), district security incidents |

**Authenticity score** = 0.50 × SBERT text + 0.50 × host auth

| Subscore | Method |
|---|---|
| SBERT text | Mean of top-3 contrast scores per listing: cos(review, positive prototype) − cos(review, negative prototype) |
| Host auth | Equal mean of: 1/log(1+n_listings) scale penalty + Barcelona residency flag (1.0/0.5/0.0) |
        """)

    st.markdown("---")
    st.markdown("### Methodology")
    st.markdown("""
<table style='width:100%;border-collapse:collapse;font-family:Inter,sans-serif;font-size:13px'>
<tr>
  <td style='width:22%;background:#f7f7f7;border:2px solid #cccccc;border-radius:8px;
             padding:14px 16px;vertical-align:top'>
    <div style='color:#888;font-size:10px;text-transform:uppercase;
                letter-spacing:.6px;margin-bottom:6px'>Stage 1</div>
    <div style='font-size:15px;font-weight:700;color:#444;margin-bottom:10px'>Pre-filter</div>
    <div style='color:#555;line-height:1.6'>
      Hard constraints<br>
      ▸ Guests ≥ N<br>
      ▸ Room type<br>
      ▸ Min stay<br>
      ▸ Availability<br>
      <br><b>18,177 → filtered pool</b>
    </div>
  </td>
  <td style='width:4%;text-align:center;vertical-align:middle;
             font-size:22px;color:#FF5A5F;font-weight:700'>→</td>
  <td style='width:22%;background:#fff1f1;border:2px solid #FF5A5F;border-radius:8px;
             padding:14px 16px;vertical-align:top'>
    <div style='color:#FF5A5F;font-size:10px;text-transform:uppercase;
                letter-spacing:.6px;margin-bottom:6px'>Stage 2</div>
    <div style='font-size:15px;font-weight:700;color:#222;margin-bottom:10px'>Base Ranking</div>
    <div style='color:#555;line-height:1.6'>
      base = 0.30 × host<br>
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ 0.40 × review<br>
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ 0.30 × context<br>
      <br><b>Filtered pool → Top-100</b>
    </div>
  </td>
  <td style='width:4%;text-align:center;vertical-align:middle;
             font-size:22px;color:#FF5A5F;font-weight:700'>→</td>
  <td style='width:22%;background:#fff8f0;border:2px solid #e07b39;border-radius:8px;
             padding:14px 16px;vertical-align:top'>
    <div style='color:#e07b39;font-size:10px;text-transform:uppercase;
                letter-spacing:.6px;margin-bottom:6px'>Stage 3</div>
    <div style='font-size:15px;font-weight:700;color:#222;margin-bottom:10px'>Final Ranking</div>
    <div style='color:#555;line-height:1.6'>
      auth = 0.50 × SBERT<br>
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ 0.50 × host signals<br>
      <br>
      final = (1−w) × base<br>
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ w × auth<br>
      <br><b>Top-100 → Final ranking</b>
    </div>
  </td>
  <td style='width:4%;text-align:center;vertical-align:middle;
             font-size:22px;color:#2a9d8f;font-weight:700'>→</td>
  <td style='width:22%;background:#f0faf8;border:2px solid #2a9d8f;border-radius:8px;
             padding:14px 16px;vertical-align:top'>
    <div style='color:#2a9d8f;font-size:10px;text-transform:uppercase;
                letter-spacing:.6px;margin-bottom:6px'>Output</div>
    <div style='font-size:15px;font-weight:700;color:#222;margin-bottom:10px'>Ranked Results</div>
    <div style='color:#555;line-height:1.6'>
      Top-10 on map<br>
      and detail table<br>
      <br>
      Auth weight<br>
      adjustable in sidebar
    </div>
  </td>
</tr>
</table>
""", unsafe_allow_html=True)

    st.markdown("---")
    leg_col, src_col = st.columns(2)
    with leg_col:
        st.markdown("### How to read the map")
        def svg_c(c,s=14): return f"<svg width='{s}' height='{s}'><circle cx='{s//2}' cy='{s//2}' r='{s//2-1}' fill='{c}'/></svg>"
        def svg_tu(c,s=14): return f"<svg width='{s}' height='{s}'><polygon points='{s//2},0 0,{s} {s},{s}' fill='{c}'/></svg>"
        def svg_td(c,s=14): return f"<svg width='{s}' height='{s}'><polygon points='0,0 {s},0 {s//2},{s}' fill='{c}'/></svg>"
        def svg_sq(c,s=12): return f"<svg width='{s}' height='{s}'><rect width='{s}' height='{s}' fill='{c}'/></svg>"
        legend_rows = [
            (svg_tu(C_RISER),  "Entered Top-10 after auth re-ranking"),
            (svg_td(C_FALLER), "Exited Top-10 after auth re-ranking"),
            (svg_sq(C_STABLE), "Stable in both Top-10s"),
            (svg_c(C_TOP10B),  "Top-10 base ranking"),
            (svg_c(C_TOPK),    "Top-100 with auth score"),
            (svg_c(C_GREY),    "Top-100 base score only"),
            (svg_c(C_ALL),     "All listings (sidebar toggle)"),
        ]
        rows_html = "".join(
            f"<tr><td style='padding:5px 10px;text-align:center'>{icon}</td>"
            f"<td style='padding:5px 10px;color:#333'>{label}</td></tr>"
            for icon,label in legend_rows
        )
        st.markdown(
            f"<table style='border-collapse:collapse;font-family:Inter,sans-serif;font-size:13px'>"
            f"<tr style='background:#f7f7f7'><th style='padding:6px 10px'>Symbol</th>"
            f"<th style='padding:6px 10px;text-align:left'>Meaning</th></tr>"
            f"{rows_html}</table>", unsafe_allow_html=True)
        st.markdown("<p style='color:#717171;font-size:12px;margin-top:8px'>"
                    "Hover: Base rank → Final rank. Click for full details.</p>",
                    unsafe_allow_html=True)

    with src_col:
        st.markdown("### Data sources")
        st.markdown("""
| Source | Used for | Link |
|---|---|---|
| Inside Airbnb - listings.csv | Primary dataset: listing attributes, host profile, ratings - used across all scoring stages | [insideairbnb.com](https://insideairbnb.com/es/get-the-data/) |
| Inside Airbnb - reviews.csv | Review text for SBERT encoding | [insideairbnb.com](https://insideairbnb.com/es/get-the-data/) |
| T-Mobilitat - stops.txt | Transport stop coordinates for proximity scoring | [t-mobilitat.cat](https://t-mobilitat.cat/web/t-mobilitat/dades-obertes/cataleg-dades/informacio-estatica) |
| Open Data BCN - points of interest | POI coordinates for proximity scoring | [opendata-ajuntament.barcelona.cat](https://opendata-ajuntament.barcelona.cat/data/es/dataset/punts-informacio-turistica/resource/31431b23-d5b9-42b8-bcd0-a84da9d8c7fa) |
| Portal de Dades BCN - incidents 2025 | District-level security incidents for context scoring | [portaldades.ajuntament.barcelona.cat](https://portaldades.ajuntament.barcelona.cat/ca/estad%C3%ADstiques/co6rdrzcdj?view=table) |
| Idescat - household income 2022 | Neighbourhood income for bias audit only (not used in ranking) | [idescat.cat](https://www.idescat.cat) |
        """)

# ── MAP ───────────────────────────────────────────────────────────────────────


with tab_map:
    st.markdown("# 🗺️ Map & Results")
    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("Total listings", f"{TOTAL:,}")
    m2.metric("After filter", f"{len(df_f):,}")
    m3.metric("Top-100", len(df_base))
    m4.metric("With auth scores", n_s3)
    m5.metric("Superhosts in Top-10",
              int(df_final.head(TOP_N)["host_is_superhost"].sum()))

    if n_s3 == 0:
        st.warning("⚠️ No auth scores for this filter. Showing base ranking only. "
                   "Auth scores precomputed for: 4 guests, Entire home/apt, 4 nights.")
    elif n_s3 < TOP_K:
        st.info(f"ℹ️ Auth scores for {n_s3}/{len(df_base)} listings. Grey = base only.")

    ctrl1, ctrl2, ctrl3 = st.columns([3,1,1])
    with ctrl1:
        view = st.radio("", ["Base ranking","Final ranking (+ authenticity)"],
                        horizontal=True, label_visibility="collapsed",
                        key="view")
    with ctrl2:
        fit_top10 = st.button("🎯 Fit to Top-10", use_container_width=True)
    with ctrl3:
        show_all = st.checkbox("Show all listings", key="show_all")
    is_final = "Final" in st.session_state.get("view","Base ranking")

    if fit_top10 and len(top10_rows) > 0:
        lat_min, lat_max = top10_rows["latitude"].min(), top10_rows["latitude"].max()
        lon_min, lon_max = top10_rows["longitude"].min(), top10_rows["longitude"].max()
        fit_center = [(lat_min+lat_max)/2, (lon_min+lon_max)/2]
        span = max(lat_max-lat_min, lon_max-lon_min, 0.005)
        fit_zoom = max(12, min(16, int(14-(span/0.02))))
    else:
        fit_center, fit_zoom = MAP_CENTER, 15

    with st.spinner("Building map…"):
        map_data = df_final if is_final else df_base
        map_rank_col = "final_rank" if is_final else "base_rank"
        map_result = st_folium(
            build_map(map_data, map_rank_col, is_final, fit_center, fit_zoom),
            width=None, height=520,
            key=f"map_{is_final}_{fit_top10}_{auth_weight}",
            returned_objects=["last_object_clicked"],
        )

    st.caption("📋 Full Top-100 ordered by final rank is available in the **Table** tab. ★ = model-computed score.")
    clicked = (map_result or {}).get("last_object_clicked")
    clicked_lid = None
    if clicked:
        lat, lon = clicked.get("lat"), clicked.get("lng")
        if lat and lon:
            dists = ((df_base["latitude"]-lat)**2 + (df_base["longitude"]-lon)**2)
            clicked_lid = int(df_base.loc[dists.idxmin(),"id"])

    if clicked_lid and reviews:
        r_row = df_base[df_base["id"]==clicked_lid].iloc[0]
        lname = str(r_row.get("name","") or f"Listing {clicked_lid}")
        revs  = reviews.get(clicked_lid,[])
        with st.expander(f"📝 Reviews - {lname[:60]}", expanded=False):
            st.caption("Top-3 longest English or Spanish reviews, "
                       "filtered to remove short generic content.")
            if revs:
                for i, rev in enumerate(revs,1):
                    st.markdown(
                        f"<div style='background:#f7f7f7;border-radius:10px;"
                        f"padding:12px 14px;margin-bottom:8px;font-size:13px;"
                        f"line-height:1.6'><b>Review {i}</b><br>{rev}</div>",
                        unsafe_allow_html=True)
            else:
                st.info("No qualifying English/Spanish reviews for this listing.")
    elif reviews:
        st.markdown("<p style='color:#aaa;font-size:13px'>"
                    "📝 Click a pin to see its reviews.</p>",
                    unsafe_allow_html=True)

    st.markdown("---")
    t10_cfg = {"URL": st.column_config.LinkColumn("Link", display_text="Open ↗")}
    st.caption("★ indicates a computed score derived by the ranking model.")
    st.markdown("#### Base ranking Top-10")
    st.dataframe(make_t10(list(df_base.nlargest(TOP_N,"base_score_default")["id"]),"Base rank"),
                 use_container_width=True, hide_index=True, column_config=t10_cfg)
    st.markdown("#### Final ranking Top-10")
    st.dataframe(make_t10(list(df_final.head(TOP_N)["id"]),"Final rank"),
                 use_container_width=True, hide_index=True, column_config=t10_cfg)

    if n_s3 >= TOP_N:
        st.markdown("#### Rank shift")
        merged = (
            df_final[["id","neighbourhood_cleansed","final_rank",
                       "base_score_default","authenticity_score","final_score_dynamic"]]
            .merge(df_base[["id","base_rank"]], on="id")
        )
        merged["Δ Rank"] = merged["base_rank"] - merged["final_rank"]
        merged = merged.sort_values("Δ Rank", ascending=False)
        rcols  = ["neighbourhood_cleansed","base_rank","final_rank","Δ Rank","authenticity_score"]
        rnames = {"neighbourhood_cleansed":"Neighbourhood","base_rank":"Base rank",
                  "final_rank":"Final rank","authenticity_score":"★ Auth score"}

        def colour_shift(df_s):
            def rc(row):
                if row["Δ Rank"] > 0: return ["background-color:#d4f7d4"]*len(row)
                if row["Δ Rank"] < 0: return ["background-color:#fde8e8"]*len(row)
                return [""]*len(row)
            return df_s.style.apply(rc, axis=1)

        rs1, rs2 = st.columns(2)
        with rs1:
            st.markdown("**▲ Top 5 risers**")
            st.dataframe(colour_shift(merged.head(5)[rcols].rename(columns=rnames)
                         .reset_index(drop=True)), use_container_width=True)
        with rs2:
            st.markdown("**▼ Top 5 fallers**")
            st.dataframe(colour_shift(merged.tail(5).sort_values("Δ Rank")[rcols]
                         .rename(columns=rnames).reset_index(drop=True)),
                         use_container_width=True)

# ── ANALYSIS ──────────────────────────────────────────────────────────────────
with tab_analysis:
    st.markdown("# 📈 Analysis")
    sc_col, rad_col = st.columns(2)

    with sc_col:
        st.markdown("### Scatter: base score vs authenticity score")
        st.caption("Each point = one Top-100 listing. Shapes match map legend. "
                   "Hover for name and ranks. Dashed lines = Top-100 means.")
        if n_s3 > 0:
            st.plotly_chart(make_scatter(df_base), use_container_width=True)
        else:
            st.info("No auth scores available for this filter.")

    with rad_col:
        st.markdown("### Radar: subscore profile")
        st.caption("Select a Top-10 listing to compare its subscore profile "
                   "against the Top-100 mean.")
        top10_options = []
        for lid in df_final.head(TOP_N)["id"]:
            r = df_base[df_base["id"]==lid]
            if not len(r): continue
            name = str(r.iloc[0].get("name","") or f"ID {lid}")[:45]
            top10_options.append((lid, name))

        if top10_options:
            sel_name = st.selectbox("Select listing", [n for _,n in top10_options],
                                    label_visibility="collapsed")
            sel_lid  = next(lid for lid,n in top10_options if n==sel_name)
            r_row    = df_base[df_base["id"]==sel_lid]
            if len(r_row):
                radar_row = r_row.iloc[0]
                fig_r, vals = make_radar(radar_row)
                st.plotly_chart(fig_r, use_container_width=True)

                # Debug table
                with st.expander("🔍 Raw subscore values for this listing"):
                    debug_df = pd.DataFrame({
                        "Subscore":   SUBSCORE_LABELS,
                        "This listing": [f"{v:.4f}" for v in vals],
                        "Top-100 mean": [
                            f"{df_base[col].mean():.4f}" if col in df_base.columns else "N/A"
                            for col in SUBSCORE_COLS
                        ],
                        "How computed": [
                            "Normalised mean of 6 host features",
                            "0.70 × rating + 0.30 × reviews_ltm",
                            "Equal mean of transport + POI + security proximity",
                            "Top-3 mean contrast score vs prototypes (SBERT)",
                            "(auth_score − 0.5×sbert_score) / 0.5 - derived since not exported to CSV"
                            if pd.notna(radar_row.get("authenticity_score")) else
                            "Cannot derive - authenticity_score is NaN for this listing",
                        ],
                    })
                    st.dataframe(debug_df, use_container_width=True, hide_index=True)
                    if vals[4] == 0.0:
                        st.warning("Host auth = 0.0 - this listing may have NaN "
                                   "authenticity_score or sbert_text_score.")
        else:
            st.info("No Top-10 listings available for this filter.")

# ── TABLE ─────────────────────────────────────────────────────────────────────
with tab_table:
    st.markdown("# 📋 Top-100 Detail Table")
    st.caption("Sorted by final score. Pink rows = Top-10.")
    tbl = df_final[[
        "final_rank","id","name","neighbourhood_cleansed","room_type","accommodates",
        "host_is_superhost","review_scores_rating","calculated_host_listings_count",
        "host_quality_subscore","review_quality_subscore","context_subscore",
        "base_score_default","sbert_text_score","host_authenticity_subscore_derived",
        "authenticity_score","final_score_dynamic","listing_url",
    ]].copy()
    tbl["id"] = tbl["id"].astype(str)
    tbl.columns = [
        "Rank","ID","Name","Neighbourhood","Room","Guests","Superhost","Rating",
        "Host listings","★ Host Q","★ Review Q","★ Context",
        "★ Base score","★ SBERT","★ Host auth","★ Auth score","★ Final score","URL",
    ]
    tbl["Superhost"] = tbl["Superhost"].map({1:"Yes",0:"No"})
    for col in ["Rating","★ Host Q","★ Review Q","★ Context","★ Base score",
                "★ SBERT","★ Host auth","★ Auth score","★ Final score"]:
        tbl[col] = pd.to_numeric(tbl[col], errors="coerce").round(3)

    def hl(row):
        return (["background-color:#fff1f1"]*len(row)
                if row["Rank"] <= TOP_N else [""]*len(row))

    st.dataframe(tbl.style.apply(hl, axis=1), use_container_width=True, height=580,
                 column_config={"URL": st.column_config.LinkColumn("Airbnb",display_text="Open ↗")})
    csv_bytes = tbl.drop(columns=["URL"]).to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Top-100 as CSV", csv_bytes,
                       "barcelona_top100_authenticity.csv", "text/csv")

# ── COMPARISON ────────────────────────────────────────────────────────────────
with tab_compare:
    st.markdown("# 📊 Comparison")
    st.caption("★ indicates a computed score derived by the ranking model, as opposed to a raw dataset attribute.")

    st.markdown("#### District distribution across ranking tiers")
    st.caption("Percentages show share of each tier coming from that district - each column sums to 100%.")
    all_d  = df_full["neighbourhood_group_cleansed"].value_counts().rename("All listings")
    topk_d = df_base["neighbourhood_group_cleansed"].value_counts().rename("Top-100 count")
    t10b_d = (df_base[df_base["id"].isin(base_top10)]["neighbourhood_group_cleansed"]
              .value_counts().rename("Top-10 base count"))
    t10f_d = (df_final[df_final["id"].isin(final_top10)]["neighbourhood_group_cleansed"]
              .value_counts().rename("Top-10 final count"))
    dist_df = pd.concat([all_d,topk_d,t10b_d,t10f_d], axis=1).fillna(0).astype(int)
    dist_df["% of Top-100"] = (
        dist_df["Top-100 count"] / dist_df["Top-100 count"].sum() * 100).round(1)
    dist_df["% of Top-10 (base)"] = (
        dist_df["Top-10 base count"] / dist_df["Top-10 base count"].sum() * 100).round(1)
    dist_df["% of Top-10 (final)"] = (
        dist_df["Top-10 final count"] / dist_df["Top-10 final count"].sum() * 100).round(1)
    st.dataframe(
        dist_df.reset_index().rename(columns={"neighbourhood_group_cleansed":"District"}),
        use_container_width=True)

    st.markdown("#### Key metrics across tiers")
    def tier_metrics(dft):
        return {
            "Superhost rate":     f"{dft['host_is_superhost'].mean()*100:.1f}%",
            "Mean rating":        f"{dft['review_scores_rating'].mean():.2f}",
            "Mean host listings": f"{dft['calculated_host_listings_count'].mean():.1f}",
            "★ Mean base score":  f"{dft['base_score_default'].mean():.3f}",
        }
    tiers = {
        "All listings":   df_full,
        "Top-100":        df_base,
        "Top-10 (base)":  df_base[df_base["id"].isin(base_top10)],
        "Top-10 (final)": df_final[df_final["id"].isin(final_top10)],
    }
    mdf = pd.DataFrame({k:tier_metrics(v) for k,v in tiers.items()}).T
    mdf.index.name = "Tier"
    st.dataframe(mdf.reset_index(), use_container_width=True)

    if n_s3 >= TOP_N and (entered or exited):
        st.markdown("#### Listings that changed in the Top-10")
        ec1, ec2 = st.columns(2)
        cols_s  = ["id","neighbourhood_cleansed","base_score_default",
                   "authenticity_score","final_score_dynamic"]
        col_ren = {"neighbourhood_cleansed":"Neighbourhood","base_score_default":"★ Base",
                   "authenticity_score":"★ Auth","final_score_dynamic":"★ Final"}
        def add_link(df):
            df = df.copy()
            df["Airbnb"] = df["id"].apply(
                lambda i: f"https://www.airbnb.com/rooms/{int(i)}")
            df["id"] = df["id"].astype(str)
            return df

        with ec1:
            st.markdown("**▲ Entered final Top-10**")
            ent = df_final[df_final["id"].isin(entered)][cols_s].copy()
            ent = add_link(ent).rename(columns=col_ren).reset_index(drop=True)
            st.dataframe(ent, use_container_width=True,
                         column_config={"Airbnb": st.column_config.LinkColumn("Airbnb ↗")})
        with ec2:
            st.markdown("**▼ Exited final Top-10**")
            ex = df_base[df_base["id"].isin(exited)][cols_s].copy()
            ex = add_link(ex).rename(columns=col_ren).reset_index(drop=True)
            st.dataframe(ex, use_container_width=True,
                         column_config={"Airbnb": st.column_config.LinkColumn("Airbnb ↗")})

st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#aaa;font-size:12px'>"
    "TFM - Authenticity-Aware Ranking of Airbnb Listings in Barcelona · "
    "Data: Inside Airbnb, Open Data BCN, Mossos d'Esquadra · "
    "Model: SBERT prototype matching + manually defined composite scoring</p>",
    unsafe_allow_html=True)
