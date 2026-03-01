import requests
import streamlit as st

# =============================
# CONFIG
# =============================
API_BASE = "https://movie-rec-466x.onrender.com" or "http://127.0.0.1:8000"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"

st.set_page_config(
    page_title="CineVerse",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================
# GLOBAL CSS — Cinematic Dark Luxury
# =============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=Outfit:wght@300;400;500;600&display=swap');

:root {
    --bg:       #080b12;
    --surface:  #0f1420;
    --card:     #141926;
    --border:   rgba(255,255,255,0.07);
    --gold:     #c9a84c;
    --gold-dim: #8a6f30;
    --text:     #e8e4dc;
    --muted:    #7a7f8e;
    --radius:   14px;
}

/* ── Base ── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"], .main {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Outfit', sans-serif;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

/* ── Block container ── */
.block-container {
    padding-top: 1.8rem !important;
    padding-bottom: 3rem !important;
    max-width: 1400px !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--gold-dim); border-radius: 99px; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* ── Logo ── */
.logo {
    font-family: 'Cormorant Garamond', serif;
    font-size: 2.2rem; font-weight: 300;
    letter-spacing: 0.1em; color: #fff;
    margin-bottom: 4px;
}
.logo span { color: var(--gold); font-style: italic; }
.logo-sub {
    font-size: 11px; letter-spacing: 2px;
    text-transform: uppercase; color: var(--muted);
    margin-bottom: 24px;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; }

/* ── Text inputs ── */
[data-testid="stTextInput"] input {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 99px !important;
    color: var(--text) !important;
    padding: 12px 22px !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 15px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--gold) !important;
    box-shadow: 0 0 0 3px rgba(201,168,76,0.12) !important;
}
[data-testid="stTextInput"] label { color: var(--muted) !important; font-size: 13px !important; }

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-family: 'Outfit', sans-serif !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, var(--gold) 0%, #a07c2e 100%) !important;
    color: #000 !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 99px !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 12px !important;
    letter-spacing: 0.5px !important;
    padding: 8px 20px !important;
    transition: opacity 0.2s, transform 0.15s !important;
    width: 100% !important;
}
.stButton > button:hover {
    opacity: 0.85 !important;
    transform: translateY(-1px) !important;
}

/* ── Movie card wrapper ── */
.movie-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    transition: transform 0.28s ease, box-shadow 0.28s ease, border-color 0.28s ease;
    margin-bottom: 4px;
}
.movie-card:hover {
    transform: translateY(-5px) scale(1.01);
    box-shadow: 0 18px 45px rgba(0,0,0,0.55), 0 0 0 1px var(--gold-dim);
    border-color: var(--gold-dim);
}
.poster-placeholder {
    width: 100%;
    aspect-ratio: 2/3;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #0f1420, #1a2035);
    color: var(--muted);
    font-size: 13px;
    text-align: center;
    padding: 16px;
    gap: 8px;
}
.card-body { padding: 8px 10px 10px; }
.card-title {
    font-size: 12.5px; font-weight: 500;
    color: var(--text); margin: 0 0 3px 0;
    white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; line-height: 1.3;
}
.card-year { font-size: 11px; color: var(--muted); }

/* ── Section headers ── */
.section-head {
    display: flex; align-items: baseline; gap: 14px;
    margin: 28px 0 16px 0;
    border-bottom: 1px solid var(--border);
    padding-bottom: 10px;
}
.section-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.7rem; font-weight: 400;
    color: var(--text); margin: 0;
}
.section-sub {
    font-size: 11px; color: var(--muted);
    letter-spacing: 1.2px; text-transform: uppercase;
}
.gold-line {
    height: 2px; width: 36px;
    background: linear-gradient(90deg, var(--gold), transparent);
    border-radius: 2px; margin-bottom: 4px;
}

/* ── Hero banner ── */
.hero {
    position: relative; width: 100%;
    min-height: 300px; border-radius: 20px;
    overflow: hidden; display: flex;
    align-items: flex-end; margin-bottom: 32px;
    box-shadow: 0 24px 70px rgba(0,0,0,0.65);
}
.hero-backdrop {
    position: absolute; inset: 0;
    background-size: cover; background-position: center 25%;
    filter: brightness(0.38);
    transition: transform 7s ease;
}
.hero:hover .hero-backdrop { transform: scale(1.03); }
.hero-overlay {
    position: absolute; inset: 0;
    background: linear-gradient(to top,
        rgba(8,11,18,0.97) 0%,
        rgba(8,11,18,0.5) 45%,
        transparent 100%);
}
.hero-content {
    position: relative; z-index: 2;
    padding: 30px 36px; width: 100%;
}
.hero-badge {
    display: inline-block;
    background: var(--gold); color: #000;
    font-size: 9px; font-weight: 700;
    letter-spacing: 2.5px; text-transform: uppercase;
    padding: 4px 12px; border-radius: 4px;
    margin-bottom: 10px;
}
.hero-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: clamp(1.8rem, 4vw, 3.2rem);
    font-weight: 300; line-height: 1.1;
    color: #fff; margin: 0 0 10px 0;
    text-shadow: 0 2px 24px rgba(0,0,0,0.8);
}
.hero-meta {
    display: flex; gap: 16px; flex-wrap: wrap;
    font-size: 13px; color: rgba(255,255,255,0.6);
    align-items: center; margin-bottom: 10px;
}
.hero-overview {
    font-size: 13.5px; line-height: 1.65;
    color: rgba(255,255,255,0.68);
    max-width: 560px;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

/* ── Genre tags ── */
.genre-tag {
    display: inline-block;
    background: rgba(201,168,76,0.1);
    border: 1px solid var(--gold-dim);
    color: var(--gold);
    font-size: 10px; letter-spacing: 0.8px;
    text-transform: uppercase;
    padding: 3px 10px; border-radius: 4px; margin: 2px;
}

/* ── Detail card ── */
.detail-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px 26px;
}
.detail-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 2rem; font-weight: 300;
    color: #fff; margin: 0 0 8px 0; line-height: 1.15;
}
.detail-overview {
    font-size: 14px; line-height: 1.75;
    color: rgba(232,228,220,0.8);
}

/* ── Stat boxes ── */
.stat-row { display: flex; gap: 10px; flex-wrap: wrap; margin: 12px 0; }
.stat-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px; padding: 10px 16px;
    display: flex; flex-direction: column; gap: 2px;
}
.stat-label { font-size: 10px; letter-spacing: 1.2px; text-transform: uppercase; color: var(--muted); }
.stat-value { font-size: 17px; font-weight: 600; color: var(--text); }

/* ── Rec label ── */
.rec-label {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.35rem; font-weight: 400;
    color: var(--text); margin: 20px 0 12px 0;
    border-left: 3px solid var(--gold);
    padding-left: 12px;
}

/* ── Small muted ── */
.small-muted { color: var(--muted); font-size: 0.88rem; }

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    background: var(--surface) !important;
    border-radius: 10px !important;
    padding: 4px !important;
    border: 1px solid var(--border) !important;
}
[data-testid="stTabs"] [role="tab"] {
    color: var(--muted) !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 13px !important;
    border-radius: 8px !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: var(--gold) !important;
    color: #000 !important;
    font-weight: 600 !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
    background: var(--surface) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
    border-radius: 10px !important;
}

/* ── Animations ── */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}
.fade-up { animation: fadeUp 0.4s ease forwards; }
</style>
""", unsafe_allow_html=True)


# =============================
# STATE + ROUTING
# =============================
if "view" not in st.session_state:
    st.session_state.view = "home"
if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None

qp_view = st.query_params.get("view")
qp_id   = st.query_params.get("id")
if qp_view in ("home", "details"):
    st.session_state.view = qp_view
if qp_id:
    try:
        st.session_state.selected_tmdb_id = int(qp_id)
        st.session_state.view = "details"
    except:
        pass


def goto_home():
    st.session_state.view = "home"
    st.query_params["view"] = "home"
    if "id" in st.query_params:
        del st.query_params["id"]
    st.rerun()


def goto_details(tmdb_id: int):
    st.session_state.view      = "details"
    st.session_state.selected_tmdb_id = int(tmdb_id)
    st.query_params["view"]    = "details"
    st.query_params["id"]      = str(int(tmdb_id))
    st.rerun()


# =============================
# API HELPERS
# =============================
@st.cache_data(ttl=30)
def api_get_json(path: str, params: dict | None = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=25)
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}: {r.text[:300]}"
        return r.json(), None
    except Exception as e:
        return None, f"Request failed: {e}"


def to_cards_from_tfidf_items(tfidf_items):
    """Convert TF-IDF recommendation items into simple poster-card dicts."""
    cards = []
    for x in tfidf_items or []:
        tmdb = x.get("tmdb") or {}
        if tmdb.get("tmdb_id"):
            cards.append({
                "tmdb_id":    tmdb["tmdb_id"],
                "title":      tmdb.get("title") or x.get("title") or "Untitled",
                "poster_url": tmdb.get("poster_url"),
            })
    return cards


def parse_tmdb_search_to_cards(data, keyword: str, limit: int = 24):
    """
    Normalize TMDB search response into suggestions + cards.
    Handles both raw TMDB shape {results:[...]} and pre-processed list.
    """
    keyword_l = keyword.strip().lower()

    if isinstance(data, dict) and "results" in data:
        raw_items = []
        for m in (data.get("results") or []):
            title   = (m.get("title") or "").strip()
            tmdb_id = m.get("id")
            poster  = m.get("poster_path")
            if not title or not tmdb_id:
                continue
            raw_items.append({
                "tmdb_id":      int(tmdb_id),
                "title":        title,
                "poster_url":   f"{TMDB_IMG}{poster}" if poster else None,
                "release_date": m.get("release_date", ""),
                "vote_average": m.get("vote_average"),
            })
    elif isinstance(data, list):
        raw_items = []
        for m in data:
            tmdb_id = m.get("tmdb_id") or m.get("id")
            title   = (m.get("title") or "").strip()
            if not title or not tmdb_id:
                continue
            raw_items.append({
                "tmdb_id":      int(tmdb_id),
                "title":        title,
                "poster_url":   m.get("poster_url"),
                "release_date": m.get("release_date", ""),
                "vote_average": m.get("vote_average"),
            })
    else:
        return [], []

    matched    = [x for x in raw_items if keyword_l in x["title"].lower()]
    final_list = matched if matched else raw_items

    suggestions = []
    for x in final_list[:10]:
        year  = (x.get("release_date") or "")[:4]
        label = f"{x['title']} ({year})" if year else x["title"]
        suggestions.append((label, x["tmdb_id"]))

    cards = [{
        "tmdb_id":      x["tmdb_id"],
        "title":        x["title"],
        "poster_url":   x["poster_url"],
        "vote_average": x.get("vote_average"),
        "release_date": x.get("release_date", ""),
    } for x in final_list[:limit]]

    return suggestions, cards


# =============================
# UI COMPONENTS
# =============================
def render_section_header(title: str, subtitle: str = ""):
    sub = f'<span class="section-sub">{subtitle}</span>' if subtitle else ""
    st.markdown(f"""
    <div class="section-head">
        <div><div class="gold-line"></div>
        <h2 class="section-title">{title}</h2></div>
        {sub}
    </div>""", unsafe_allow_html=True)


def render_hero(title, backdrop_url, overview,
                vote_average=None, release_date=None, genres=None, badge="Featured"):
    """Full-width cinematic hero banner with parallax effect."""
    year        = (release_date or "")[:4]
    rating_html = f'<span>⭐ {vote_average:.1f}/10</span>' if vote_average else ""
    year_html   = f'<span>📅 {year}</span>'               if year         else ""
    genre_tags  = "".join([
        f'<span class="genre-tag">{g["name"]}</span>'
        for g in (genres or [])[:4]
    ])
    st.markdown(f"""
    <div class="hero">
        <div class="hero-backdrop" style="background-image:url('{backdrop_url or ""}')"></div>
        <div class="hero-overlay"></div>
        <div class="hero-content">
            <div class="hero-badge">{badge}</div>
            <h1 class="hero-title">{title}</h1>
            <div class="hero-meta">{rating_html}{year_html}</div>
            <div style="margin-bottom:10px">{genre_tags}</div>
            <p class="hero-overview">{overview or ""}</p>
        </div>
    </div>""", unsafe_allow_html=True)


def poster_grid(cards, cols=6, key_prefix="grid"):
    """
    Responsive poster grid.
    Uses st.image(width=...) instead of use_column_width=True
    to avoid the Streamlit deprecation warning.
    """
    if not cards:
        st.markdown("""
        <div style="text-align:center;padding:48px 0;color:var(--muted)">
            <div style="font-size:2.5rem;margin-bottom:12px">🎬</div>
            <div style="font-family:'Cormorant Garamond',serif;font-size:1.4rem;color:var(--text)">
                No movies to show
            </div>
        </div>""", unsafe_allow_html=True)
        return

    rows = (len(cards) + cols - 1) // cols
    idx  = 0
    for r in range(rows):
        colset = st.columns(cols, gap="small")
        for c in range(cols):
            if idx >= len(cards):
                break
            m       = cards[idx]; idx += 1
            tmdb_id = m.get("tmdb_id")
            title   = m.get("title", "Untitled")
            poster  = m.get("poster_url")
            rating  = m.get("vote_average")
            year    = (m.get("release_date") or "")[:4]

            with colset[c]:
                st.markdown('<div class="movie-card fade-up">', unsafe_allow_html=True)

                # Poster image — width= replaces deprecated use_column_width
                if poster:
                    st.image(poster, width=300)
                else:
                    st.markdown(f"""
                    <div class="poster-placeholder">
                        <span style="font-size:1.8rem">🎬</span>
                        <span>{title}</span>
                    </div>""", unsafe_allow_html=True)

                # Rating caption
                if rating:
                    st.caption(f"⭐ {rating:.1f}")

                # Title + year
                st.markdown(f"""
                <div class="card-body">
                    <div class="card-title" title="{title}">{title}</div>
                    <div class="card-year">{year or "—"}</div>
                </div>
                </div>""", unsafe_allow_html=True)

                # Open button
                if tmdb_id:
                    if st.button("▶ Open", key=f"{key_prefix}_{r}_{c}_{idx}_{tmdb_id}"):
                        goto_details(tmdb_id)


# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.markdown('<div class="logo">Cine<span>Verse</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="logo-sub">Movie Discovery</div>',    unsafe_allow_html=True)
    st.markdown("---")

    if st.button("🏠  Home", use_container_width=True):
        goto_home()

    st.markdown("---")
    st.markdown(
        '<div style="font-size:11px;letter-spacing:1.5px;text-transform:uppercase;'
        'color:#7a7f8e;margin-bottom:10px">Home Feed</div>',
        unsafe_allow_html=True,
    )
    home_category = st.selectbox(
        "Category",
        ["trending", "popular", "top_rated", "now_playing", "upcoming"],
        index=0,
        label_visibility="collapsed",
    )
    grid_cols = st.slider("Grid columns", 3, 8, 6)

    st.markdown("---")
    st.markdown(
        '<div style="font-size:11px;color:#7a7f8e;line-height:1.6">'
        'Powered by TMDB API &<br>TF-IDF Content Similarity</div>',
        unsafe_allow_html=True,
    )


# =============================
# PAGE HEADER
# =============================
st.markdown(
    '<div style="font-family:\'Cormorant Garamond\',serif;font-size:2.6rem;'
    'font-weight:300;color:#fff;letter-spacing:0.04em;margin-bottom:4px">'
    '🎬 Cine<span style="color:#c9a84c;font-style:italic">Verse</span></div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="small-muted" style="margin-bottom:16px">'
    'Search any film · Discover by genre · AI-powered content recommendations</div>',
    unsafe_allow_html=True,
)
st.divider()


# ==========================================================
# VIEW: HOME
# ==========================================================
if st.session_state.view == "home":

    typed = st.text_input(
        "",
        placeholder="🔍  Search a movie…  e.g. Inception, The Dark Knight, Interstellar",
        label_visibility="collapsed",
    )
    st.divider()

    # ── SEARCH MODE ──
    if typed.strip():
        if len(typed.strip()) < 2:
            st.caption("Type at least 2 characters.")
        else:
            with st.spinner(f'Searching for "{typed.strip()}"…'):
                data, err = api_get_json("/tmdb/search", params={"query": typed.strip()})

            if err or data is None:
                st.error(f"Search failed: {err}")
            else:
                suggestions, cards = parse_tmdb_search_to_cards(data, typed.strip(), limit=24)

                if suggestions:
                    labels   = ["— Select a movie to see full details —"] + [s[0] for s in suggestions]
                    selected = st.selectbox("", labels, index=0, label_visibility="collapsed")
                    if selected != "— Select a movie to see full details —":
                        label_to_id = {s[0]: s[1] for s in suggestions}
                        goto_details(label_to_id[selected])
                else:
                    st.info("No suggestions found. Try another keyword.")

                render_section_header("Search Results", f"{len(cards)} movies found")
                poster_grid(cards, cols=grid_cols, key_prefix="search_results")

        st.stop()

    # ── HOME FEED MODE ──
    render_section_header(
        home_category.replace("_", " ").title(),
        "Home Feed",
    )

    with st.spinner("Loading movies…"):
        home_cards, err = api_get_json("/home", params={"category": home_category, "limit": 24})

    if err or not home_cards:
        st.error(f"Home feed failed: {err or 'Unknown error'}")
        st.stop()

    # Cinematic hero: first card with a poster
    hero = next((m for m in home_cards if m.get("poster_url")), home_cards[0])
    render_hero(
        title        = hero.get("title", ""),
        backdrop_url = hero.get("poster_url"),
        overview     = "Click any movie below to explore full details and AI-powered recommendations.",
        vote_average = hero.get("vote_average"),
        release_date = hero.get("release_date"),
        badge        = home_category.replace("_", " ").title(),
    )

    poster_grid(home_cards, cols=grid_cols, key_prefix="home_feed")


# ==========================================================
# VIEW: DETAILS
# ==========================================================
elif st.session_state.view == "details":
    tmdb_id = st.session_state.selected_tmdb_id

    if not tmdb_id:
        st.warning("No movie selected.")
        if st.button("← Back to Home"):
            goto_home()
        st.stop()

    if st.button("← Back to Home"):
        goto_home()

    # Fetch full movie details
    with st.spinner("Loading movie details…"):
        data, err = api_get_json(f"/movie/id/{tmdb_id}")

    if err or not data:
        st.error(f"Could not load details: {err or 'Unknown error'}")
        st.stop()

    # ── Hero banner ──
    render_hero(
        title        = data.get("title", ""),
        backdrop_url = data.get("backdrop_url") or data.get("poster_url"),
        overview     = data.get("overview", ""),
        vote_average = data.get("vote_average"),
        release_date = data.get("release_date"),
        genres       = data.get("genres", []),
        badge        = "Now Viewing",
    )

    # ── Poster + Info ──
    left, right = st.columns([1, 2.4], gap="large")

    with left:
        if data.get("poster_url"):
            # width= replaces the deprecated use_column_width parameter
            st.image(data["poster_url"], width=340)
        else:
            st.markdown(
                '<div class="poster-placeholder" style="height:400px">🎬<br>No Poster</div>',
                unsafe_allow_html=True,
            )

    with right:
        st.markdown('<div class="detail-card">', unsafe_allow_html=True)

        st.markdown(
            f'<div class="detail-title">{data.get("title","")}</div>',
            unsafe_allow_html=True,
        )

        release = data.get("release_date") or "—"
        rating  = data.get("vote_average")
        genres  = data.get("genres", [])
        year    = release[:4] if release != "—" else "—"

        # Stat boxes
        st.markdown(f"""
        <div class="stat-row">
            <div class="stat-box">
                <div class="stat-label">Rating</div>
                <div class="stat-value">{"⭐ " + str(round(rating, 1)) if rating else "—"}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Year</div>
                <div class="stat-value">{year}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Release</div>
                <div class="stat-value" style="font-size:13px">{release}</div>
            </div>
        </div>""", unsafe_allow_html=True)

        # Genre tags
        if genres:
            genre_html = "".join([f'<span class="genre-tag">{g["name"]}</span>' for g in genres])
            st.markdown(f'<div style="margin-bottom:14px">{genre_html}</div>', unsafe_allow_html=True)

        # Overview
        st.markdown(
            '<div style="font-size:11px;letter-spacing:1.2px;text-transform:uppercase;'
            'color:var(--muted);margin-bottom:8px">Overview</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="detail-overview">{data.get("overview") or "No overview available."}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # Backdrop
    if data.get("backdrop_url"):
        st.markdown('<div style="margin-top:22px">', unsafe_allow_html=True)
        st.image(data["backdrop_url"], width=1200)
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # ── Recommendations ──
    render_section_header("Recommendations", "AI content similarity + genre matching")

    title = (data.get("title") or "").strip()
    if title:
        with st.spinner("Finding recommendations…"):
            bundle, err2 = api_get_json(
                "/movie/search",
                params={"query": title, "tfidf_top_n": 12, "genre_limit": 12},
            )

        if not err2 and bundle:
            tab1, tab2 = st.tabs(["🧠  Content Similarity (AI)", "🎭  Same Genre"])

            with tab1:
                tfidf_cards = to_cards_from_tfidf_items(bundle.get("tfidf_recommendations"))
                if tfidf_cards:
                    st.markdown('<div class="rec-label">Because you watched this</div>', unsafe_allow_html=True)
                    poster_grid(tfidf_cards, cols=grid_cols, key_prefix="details_tfidf")
                else:
                    st.info("No content-based recommendations found for this title.")

            with tab2:
                genre_cards = bundle.get("genre_recommendations", [])
                if genre_cards:
                    st.markdown('<div class="rec-label">More in this genre</div>', unsafe_allow_html=True)
                    poster_grid(genre_cards, cols=grid_cols, key_prefix="details_genre")
                else:
                    st.info("No genre recommendations found.")
        else:
            # Fallback to genre-only endpoint
            st.info("Showing genre recommendations (fallback).")
            with st.spinner("Loading genre recommendations…"):
                genre_only, err3 = api_get_json(
                    "/recommend/genre", params={"tmdb_id": tmdb_id, "limit": 18}
                )
            if not err3 and genre_only:
                poster_grid(genre_only, cols=grid_cols, key_prefix="details_genre_fallback")
            else:
                st.warning("No recommendations available right now.")
    else:
        st.warning("No title available to compute recommendations.")