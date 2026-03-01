import os
import pickle
from typing import Optional, List, Dict, Any, Tuple

import numpy as np
import pandas as pd
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv


# =========================
# ENV
# =========================

# Load environment variables from .env file (e.g. TMDB_API_KEY=xxxx)
load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Base URL for all TMDB API requests
TMDB_BASE = "https://api.themoviedb.org/3"

# Base URL for movie poster images at 500px width
TMDB_IMG_500 = "https://image.tmdb.org/t/p/w500"

# Fail loudly at startup if the API key is missing — better than a cryptic error later
if not TMDB_API_KEY:
    raise RuntimeError("TMDB_API_KEY missing. Put it in .env as TMDB_API_KEY=xxxx")


# =========================
# FASTAPI APP
# =========================

# Initialize the FastAPI application with a title and version
app = FastAPI(title="Movie Recommender API", version="3.0")

# Allow cross-origin requests from any domain.
# This is needed so the Streamlit frontend (running on a different port) can call this API.
# NOTE: allow_credentials=True + allow_origins=["*"] is technically invalid for browsers;
#       consider restricting to "http://localhost:8501" in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for local streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# PICKLE GLOBALS
# =========================

# Resolve absolute paths to pickle files relative to this script's directory.
# This ensures the app works regardless of the working directory it's launched from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DF_PATH           = os.path.join(BASE_DIR, "df.pkl")           # DataFrame of movies with metadata
INDICES_PATH      = os.path.join(BASE_DIR, "indices.pkl")      # Mapping: movie title -> DataFrame row index
TFIDF_MATRIX_PATH = os.path.join(BASE_DIR, "tfidf_matrix.pkl") # Sparse TF-IDF matrix (movies x terms)
TFIDF_PATH        = os.path.join(BASE_DIR, "tfidf.pkl")        # Fitted TF-IDF vectorizer (for transforms)

# Global variables that will be populated at startup from the pickle files above.
# Typed as Optional so type checkers know they may be None before startup completes.
df: Optional[pd.DataFrame] = None
indices_obj: Any = None
tfidf_matrix: Any = None
tfidf_obj: Any = None

# Normalized title → row-index map, built from indices_obj at startup.
# Keys are lowercased/stripped titles for case-insensitive lookup.
TITLE_TO_IDX: Optional[Dict[str, int]] = None


# =========================
# MODELS
# =========================

class TMDBMovieCard(BaseModel):
    """
    Lightweight movie card returned in lists (home feed, search results, recommendations).
    Contains just enough info to render a poster tile in the UI.
    """
    tmdb_id: int
    title: str
    poster_url: Optional[str] = None      # Full URL to the 500px-wide poster image
    release_date: Optional[str] = None    # Format: "YYYY-MM-DD"
    vote_average: Optional[float] = None  # TMDB community rating (0–10)


class TMDBMovieDetails(BaseModel):
    """
    Full movie details fetched from the TMDB /movie/{id} endpoint.
    Used when a user clicks into a specific movie.
    """
    tmdb_id: int
    title: str
    overview: Optional[str] = None        # Plot summary
    release_date: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None    # Wide banner image for hero sections
    genres: List[dict] = []              # e.g. [{"id": 28, "name": "Action"}, ...]


class TFIDFRecItem(BaseModel):
    """
    A single TF-IDF recommendation result.
    Pairs a locally-computed similarity score with optional TMDB metadata for display.
    """
    title: str
    score: float                         # Cosine similarity score (0–1)
    tmdb: Optional[TMDBMovieCard] = None # TMDB poster/metadata, None if TMDB lookup failed


class SearchBundleResponse(BaseModel):
    """
    The main response shape for the /movie/search endpoint.
    Bundles everything the frontend needs for a movie detail page in one request:
      - Full TMDB movie details
      - Content-based TF-IDF recommendations (from local dataset)
      - Genre-based recommendations (from TMDB Discover API)
    """
    query: str
    movie_details: TMDBMovieDetails
    tfidf_recommendations: List[TFIDFRecItem]
    genre_recommendations: List[TMDBMovieCard]


# =========================
# UTILS
# =========================

def _norm_title(t: str) -> str:
    """
    Normalize a movie title for consistent dictionary lookups.
    Strips surrounding whitespace and lowercases so "The Matrix" == "the matrix".
    """
    return str(t).strip().lower()


def make_img_url(path: Optional[str]) -> Optional[str]:
    """
    Convert a TMDB image path (e.g. "/abc123.jpg") to a full URL.
    Returns None if no path is provided (some movies have no poster).
    """
    if not path:
        return None
    return f"{TMDB_IMG_500}{path}"


async def tmdb_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Central helper for all TMDB API GET requests.
    Automatically injects the API key and wraps errors into HTTP 502 responses
    so callers never have to handle raw network/HTTP exceptions.

    Args:
        path:   TMDB endpoint path, e.g. "/movie/popular"
        params: Query parameters (api_key is injected automatically)

    Returns:
        Parsed JSON response as a dict.

    Raises:
        HTTPException(502): On network errors or non-200 TMDB responses.
    """
    # Inject the API key into every request without mutating the caller's dict
    q = dict(params)
    q["api_key"] = TMDB_API_KEY

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(f"{TMDB_BASE}{path}", params=q)
    except httpx.RequestError as e:
        # Network-level failure (DNS, timeout, connection refused, etc.)
        raise HTTPException(
            status_code=502,
            detail=f"TMDB request error: {type(e).__name__} | {repr(e)}",
        )

    # Surface TMDB API-level errors (bad key, rate limit, not found, etc.)
    if r.status_code != 200:
        raise HTTPException(
            status_code=502, detail=f"TMDB error {r.status_code}: {r.text}"
        )

    return r.json()


async def tmdb_cards_from_results(
    results: List[dict], limit: int = 20
) -> List[TMDBMovieCard]:
    """
    Convert a raw TMDB 'results' list into typed TMDBMovieCard objects.
    Handles both movie and TV results (prefers 'title', falls back to 'name').

    Args:
        results: Raw list from a TMDB results array.
        limit:   Maximum number of cards to return.
    """
    out: List[TMDBMovieCard] = []
    for m in (results or [])[:limit]:
        out.append(
            TMDBMovieCard(
                tmdb_id=int(m["id"]),
                title=m.get("title") or m.get("name") or "",
                poster_url=make_img_url(m.get("poster_path")),
                release_date=m.get("release_date"),
                vote_average=m.get("vote_average"),
            )
        )
    return out


async def tmdb_movie_details(movie_id: int) -> TMDBMovieDetails:
    """
    Fetch full details for a single movie from TMDB by its numeric ID.
    Used both directly (via /movie/id/{id}) and internally for bundle responses.
    """
    data = await tmdb_get(f"/movie/{movie_id}", {"language": "en-US"})
    return TMDBMovieDetails(
        tmdb_id=int(data["id"]),
        title=data.get("title") or "",
        overview=data.get("overview"),
        release_date=data.get("release_date"),
        poster_url=make_img_url(data.get("poster_path")),
        backdrop_url=make_img_url(data.get("backdrop_path")),
        genres=data.get("genres", []) or [],
    )


async def tmdb_search_movies(query: str, page: int = 1) -> Dict[str, Any]:
    """
    Search TMDB for movies matching a keyword query.
    Returns the raw TMDB response (with 'results', 'total_pages', etc.)
    so the caller can decide how many results to use.

    Used by:
      - /tmdb/search  (returns the full raw shape for Streamlit grids/dropdowns)
      - tmdb_search_first (grabs just the top result)
    """
    return await tmdb_get(
        "/search/movie",
        {
            "query": query,
            "include_adult": "false",
            "language": "en-US",
            "page": page,
        },
    )


async def tmdb_search_first(query: str) -> Optional[dict]:
    """
    Convenience wrapper: search TMDB and return only the top result dict.
    Returns None if TMDB returns no matches (instead of raising).
    Used when we need the single best match for a given title string.
    """
    data = await tmdb_search_movies(query=query, page=1)
    results = data.get("results", [])
    return results[0] if results else None


# =========================
# TF-IDF Helpers
# =========================

def build_title_to_idx_map(indices: Any) -> Dict[str, int]:
    """
    Build a normalized title → DataFrame row index lookup dictionary
    from the loaded indices.pkl file.

    The pickle file can be either:
      - A plain Python dict  {title: index}
      - A pandas Series      (index=title, values=row_index)

    Both are normalized to lowercase stripped keys for case-insensitive lookup.

    Raises:
        RuntimeError: If the indices object cannot be iterated as key-value pairs.
    """
    title_to_idx: Dict[str, int] = {}

    if isinstance(indices, dict):
        # Straightforward dict — just normalize the keys
        for k, v in indices.items():
            title_to_idx[_norm_title(k)] = int(v)
        return title_to_idx

    # Try treating it as any iterable with .items() (covers pandas Series and similar)
    try:
        for k, v in indices.items():
            title_to_idx[_norm_title(k)] = int(v)
        return title_to_idx
    except Exception:
        raise RuntimeError(
            "indices.pkl must be dict or pandas Series-like (with .items())"
        )


def get_local_idx_by_title(title: str) -> int:
    """
    Look up the DataFrame row index for a movie title using the normalized map.
    Raises HTTP 404 if the title isn't in the local dataset (not in the pickle).

    Args:
        title: Movie title (case-insensitive, whitespace-stripped).

    Returns:
        Integer row index into the global df / tfidf_matrix.
    """
    global TITLE_TO_IDX
    if TITLE_TO_IDX is None:
        raise HTTPException(status_code=500, detail="TF-IDF index map not initialized")
    key = _norm_title(title)
    if key in TITLE_TO_IDX:
        return int(TITLE_TO_IDX[key])
    raise HTTPException(
        status_code=404, detail=f"Title not found in local dataset: '{title}'"
    )


def tfidf_recommend_titles(
    query_title: str, top_n: int = 10
) -> List[Tuple[str, float]]:
    """
    Core content-based recommendation function using cosine similarity.

    How it works:
      1. Find the row index for query_title in the TF-IDF matrix.
      2. Multiply the query row vector by the full matrix (dot product = cosine similarity
         since TF-IDF rows are L2-normalized by sklearn's default).
      3. Sort all movies by descending similarity score.
      4. Return the top_n titles (excluding the query movie itself).

    Args:
        query_title: The movie to find recommendations for.
        top_n:       How many recommendations to return.

    Returns:
        List of (title, similarity_score) tuples, highest score first.

    Raises:
        HTTPException(500): If TF-IDF resources aren't loaded.
        HTTPException(404): If query_title isn't in the local dataset.
    """
    global df, tfidf_matrix
    if df is None or tfidf_matrix is None:
        raise HTTPException(status_code=500, detail="TF-IDF resources not loaded")

    # Get the row index for this movie in the TF-IDF matrix
    idx = get_local_idx_by_title(query_title)

    # Extract the query movie's TF-IDF vector and compute cosine similarity
    # against every other movie in the matrix via matrix multiplication.
    # Result shape: (n_movies,) — one score per movie.
    qv = tfidf_matrix[idx]
    scores = (tfidf_matrix @ qv.T).toarray().ravel()

    # Sort indices by score descending (argsort gives ascending, so negate)
    order = np.argsort(-scores)

    out: List[Tuple[str, float]] = []
    for i in order:
        # Skip the query movie itself (score would be 1.0 — perfect self-match)
        if int(i) == int(idx):
            continue
        try:
            title_i = str(df.iloc[int(i)]["title"])
        except Exception:
            # Skip rows with missing/malformed title data
            continue
        out.append((title_i, float(scores[int(i)])))
        if len(out) >= top_n:
            break
    return out


async def attach_tmdb_card_by_title(title: str) -> Optional[TMDBMovieCard]:
    """
    Enrich a locally-computed recommendation title with TMDB poster/metadata.
    Performs a TMDB keyword search and returns the top match as a TMDBMovieCard.

    This is a best-effort function — if TMDB doesn't find the movie or any
    error occurs, it returns None rather than crashing the recommendation list.

    NOTE: This makes one TMDB API call per title. For bulk use, consider
    parallelizing with asyncio.gather() to avoid sequential latency.

    Args:
        title: Local movie title string.

    Returns:
        TMDBMovieCard if found, else None.
    """
    try:
        m = await tmdb_search_first(title)
        if not m:
            return None
        return TMDBMovieCard(
            tmdb_id=int(m["id"]),
            title=m.get("title") or title,  # Fall back to local title if TMDB has none
            poster_url=make_img_url(m.get("poster_path")),
            release_date=m.get("release_date"),
            vote_average=m.get("vote_average"),
        )
    except Exception:
        # Swallow all errors so a single bad TMDB response doesn't kill the whole rec list
        return None


# =========================
# STARTUP: LOAD PICKLES
# =========================

@app.on_event("startup")
def load_pickles():
    """
    Load all pre-computed ML artifacts from disk into memory at server startup.
    These globals are reused across all requests without reloading.

    Files loaded:
      - df.pkl           → pandas DataFrame (one row per movie, must have 'title' column)
      - indices.pkl      → title → row-index mapping (dict or pandas Series)
      - tfidf_matrix.pkl → scipy sparse matrix (movies × TF-IDF terms)
      - tfidf.pkl        → fitted TfidfVectorizer (available for future transforms)

    Note: This runs synchronously and blocks the event loop during startup.
    For large matrices, consider wrapping with asyncio.to_thread() in a
    lifespan handler (the modern FastAPI approach replacing on_event).
    """
    global df, indices_obj, tfidf_matrix, tfidf_obj, TITLE_TO_IDX

    # Load the main movie DataFrame
    with open(DF_PATH, "rb") as f:
        df = pickle.load(f)

    # Load the title-to-index mapping used for TF-IDF lookups
    with open(INDICES_PATH, "rb") as f:
        indices_obj = pickle.load(f)

    # Load the TF-IDF matrix (typically a scipy sparse CSR matrix)
    with open(TFIDF_MATRIX_PATH, "rb") as f:
        tfidf_matrix = pickle.load(f)

    # Load the fitted TF-IDF vectorizer (not used directly in routes, but
    # available for future features like transforming new query text)
    with open(TFIDF_PATH, "rb") as f:
        tfidf_obj = pickle.load(f)

    # Build the normalized lookup dictionary from the raw indices object
    TITLE_TO_IDX = build_title_to_idx_map(indices_obj)

    # Sanity check: ensure the DataFrame has the required 'title' column
    if df is None or "title" not in df.columns:
        raise RuntimeError("df.pkl must contain a DataFrame with a 'title' column")


# =========================
# ROUTES
# =========================

@app.get("/health")
def health():
    """
    Simple health check endpoint.
    Returns {"status": "ok"} if the server is running.
    Used by load balancers, monitoring tools, or the Streamlit frontend
    to verify the API is alive before making heavier requests.
    """
    return {"status": "ok"}


# ---------- HOME FEED (TMDB) ----------

@app.get("/home", response_model=List[TMDBMovieCard])
async def home(
    category: str = Query("popular"),
    limit: int = Query(24, ge=1, le=50),
):
    """
    Fetch a curated list of movies from TMDB for the home page feed.

    Supported categories:
      - "trending"     → /trending/movie/day  (what's popular right now)
      - "popular"      → /movie/popular       (all-time most popular)
      - "top_rated"    → /movie/top_rated     (highest TMDB user ratings)
      - "upcoming"     → /movie/upcoming      (not yet released)
      - "now_playing"  → /movie/now_playing   (currently in theaters)

    Args:
        category: One of the category strings above (default: "popular").
        limit:    Max number of movie cards to return (1–50, default: 24).
    """
    try:
        if category == "trending":
            # Trending has a different endpoint structure than other categories
            data = await tmdb_get("/trending/movie/day", {"language": "en-US"})
            return await tmdb_cards_from_results(data.get("results", []), limit=limit)

        # Validate the category before hitting TMDB to give a clear 400 error
        if category not in {"popular", "top_rated", "upcoming", "now_playing"}:
            raise HTTPException(status_code=400, detail="Invalid category")

        # All other categories share the same /movie/{category} endpoint pattern
        data = await tmdb_get(f"/movie/{category}", {"language": "en-US", "page": 1})
        return await tmdb_cards_from_results(data.get("results", []), limit=limit)

    except HTTPException:
        raise  # Re-raise known HTTP exceptions as-is (don't wrap in 500)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Home route failed: {e}")


# ---------- TMDB KEYWORD SEARCH (MULTIPLE RESULTS) ----------

@app.get("/tmdb/search")
async def tmdb_search(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1, le=10),
):
    """
    Keyword search for movies using the TMDB search API.
    Returns the RAW TMDB response (not transformed into our models)
    so the Streamlit frontend can work with the full result shape.

    Used by Streamlit for:
      - Autocomplete/suggestion dropdowns as the user types
      - Displaying a grid of search results

    Args:
        query: Search keyword(s), e.g. "inception" or "the dark knight".
        page:  Results page number (TMDB paginates at 20 results/page).

    Returns:
        Raw TMDB JSON with keys: results, page, total_results, total_pages.
    """
    return await tmdb_search_movies(query=query, page=page)


# ---------- MOVIE DETAILS (SAFE ROUTE) ----------

@app.get("/movie/id/{tmdb_id}", response_model=TMDBMovieDetails)
async def movie_details_route(tmdb_id: int):
    """
    Fetch full details for a movie by its TMDB numeric ID.
    Used when the frontend already knows the TMDB ID (e.g. user clicked a card).

    Args:
        tmdb_id: TMDB movie ID (integer in the URL path).

    Returns:
        TMDBMovieDetails with title, overview, genres, poster, backdrop, etc.
    """
    return await tmdb_movie_details(tmdb_id)


# ---------- GENRE RECOMMENDATIONS ----------

@app.get("/recommend/genre", response_model=List[TMDBMovieCard])
async def recommend_genre(
    tmdb_id: int = Query(...),
    limit: int = Query(18, ge=1, le=50),
):
    """
    Recommend movies by genre using the TMDB Discover API.

    Workflow:
      1. Fetch full details for tmdb_id to get its genres list.
      2. Pick the first (primary) genre.
      3. Query TMDB Discover for popular movies in that genre.
      4. Filter out the source movie from results.

    Args:
        tmdb_id: The source movie's TMDB ID.
        limit:   Max number of recommendations to return (default: 18).

    Returns:
        List of TMDBMovieCard sorted by popularity (TMDB default).
    """
    details = await tmdb_movie_details(tmdb_id)

    # If the movie has no genres listed, we can't make genre-based recs
    if not details.genres:
        return []

    # Use only the primary genre (first in list) for discovery
    genre_id = details.genres[0]["id"]
    discover = await tmdb_get(
        "/discover/movie",
        {
            "with_genres": genre_id,
            "language": "en-US",
            "sort_by": "popularity.desc",
            "page": 1,
        },
    )
    cards = await tmdb_cards_from_results(discover.get("results", []), limit=limit)

    # Exclude the source movie from its own recommendations
    return [c for c in cards if c.tmdb_id != tmdb_id]


# ---------- TF-IDF ONLY (debug/useful) ----------

@app.get("/recommend/tfidf")
async def recommend_tfidf(
    title: str = Query(..., min_length=1),
    top_n: int = Query(10, ge=1, le=50),
):
    """
    Return raw TF-IDF content-based recommendations for a movie title.
    This endpoint is useful for debugging the local ML model or building
    custom frontends that don't need TMDB poster enrichment.

    Args:
        title: Exact movie title as it appears in the local dataset (case-insensitive).
        top_n: Number of recommendations to return (default: 10).

    Returns:
        List of {"title": str, "score": float} dicts, sorted by score descending.
    """
    recs = tfidf_recommend_titles(title, top_n=top_n)
    return [{"title": t, "score": s} for t, s in recs]


# ---------- BUNDLE: Details + TF-IDF recs + Genre recs ----------

@app.get("/movie/search", response_model=SearchBundleResponse)
async def search_bundle(
    query: str = Query(..., min_length=1),
    tfidf_top_n: int = Query(12, ge=1, le=30),
    genre_limit: int = Query(12, ge=1, le=30),
):
    """
    Primary movie detail endpoint — returns everything the frontend needs
    for a movie detail/recommendation page in a single API call.

    Workflow:
      1. Search TMDB for the best match to 'query', get the TMDB movie ID.
      2. Fetch full TMDB movie details (poster, backdrop, genres, overview).
      3. Run TF-IDF content-based recommendations using the local dataset:
           a. Try matching by the TMDB title.
           b. Fallback to the raw query string if title isn't in local dataset.
           c. If both fail, return empty list (never crash the endpoint).
      4. For each TF-IDF rec title, look up TMDB poster via search (best-effort).
      5. Run genre-based recommendations via TMDB Discover on the primary genre.

    NOTE: For multiple search results (user searching, not selecting), use /tmdb/search.
          This endpoint always picks the single best TMDB match for the given query.

    Args:
        query:        Movie title to search for (user-typed string).
        tfidf_top_n:  Number of content-based recommendations (default: 12).
        genre_limit:  Number of genre-based recommendations (default: 12).

    Returns:
        SearchBundleResponse with movie_details, tfidf_recommendations, genre_recommendations.
    """
    # Step 1: Find the best TMDB match for the user's query
    best = await tmdb_search_first(query)
    if not best:
        raise HTTPException(
            status_code=404, detail=f"No TMDB movie found for query: {query}"
        )

    tmdb_id = int(best["id"])
    details = await tmdb_movie_details(tmdb_id)

    # Step 2: TF-IDF content-based recommendations (never crash the whole endpoint)
    tfidf_items: List[TFIDFRecItem] = []

    recs: List[Tuple[str, float]] = []
    try:
        # Primary: use the official TMDB title (most likely to match local dataset)
        recs = tfidf_recommend_titles(details.title, top_n=tfidf_top_n)
    except Exception:
        # Fallback: try the raw user query (handles typos or alternate titles)
        try:
            recs = tfidf_recommend_titles(query, top_n=tfidf_top_n)
        except Exception:
            recs = []  # Give up gracefully — return empty TF-IDF section

    # Step 3: Attach TMDB poster metadata to each TF-IDF recommendation title.
    # Each call makes a separate TMDB search request.
    # TODO: Parallelize with asyncio.gather() to reduce latency on large top_n.
    for title, score in recs:
        card = await attach_tmdb_card_by_title(title)
        tfidf_items.append(TFIDFRecItem(title=title, score=score, tmdb=card))

    # Step 4: Genre-based recommendations via TMDB Discover
    genre_recs: List[TMDBMovieCard] = []
    if details.genres:
        genre_id = details.genres[0]["id"]  # Use the primary genre
        discover = await tmdb_get(
            "/discover/movie",
            {
                "with_genres": genre_id,
                "language": "en-US",
                "sort_by": "popularity.desc",
                "page": 1,
            },
        )
        cards = await tmdb_cards_from_results(
            discover.get("results", []), limit=genre_limit
        )
        # Exclude the queried movie from its own genre recommendations
        genre_recs = [c for c in cards if c.tmdb_id != details.tmdb_id]

    return SearchBundleResponse(
        query=query,
        movie_details=details,
        tfidf_recommendations=tfidf_items,
        genre_recommendations=genre_recs,
    )