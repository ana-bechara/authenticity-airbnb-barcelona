# Authenticity-Aware Ranking of Airbnb Listings in Barcelona

Master's thesis — Master's in Data Science, DKSchool. Author: **Ana Bechara**.

An optional **authenticity-ranking layer** that sits on top of a short-term-rental platform's standard search. It surfaces genuinely local, individually-hosted stays that the default ranking leaves less visible, using public data only. A single "authenticity" slider lets the guest decide how much to prioritise authenticity over a conventional quality ranking.

## How it works (in brief)

A three-stage pipeline:

1. **Stage 1 — pre-filter:** keep only listings that fit the trip (capacity, room type, availability).  
2. **Stage 2 — base quality score**: 0.30 · host \+ 0.40 · reviews \+ 0.30 · context, each feature normalised to 0–1 with fixed, documented weights.  
3. **Stage 3 — authenticity re-ranking:** authenticity \= 0.5 · text \+ 0.5 · host, where the text signal compares each review (SBERT sentence embeddings) to a "local" and a "commercial" prototype, and the host signal penalises large multi-listing operators and rewards a locally-based host. The final ranking blends the two: final \= (1 − w) · base \+ w · authenticity, with w \= 0.30 by default.

## Repository structure

```
├── README.md
├── requirements.txt
├── .gitignore
├── TFM.ipynb                 # full pipeline: data prep, scoring, evaluation
├── src/
│   └── app.py                # Streamlit demonstrator (add your app file here)
└── data/
    ├── README.md             # dataset sources + expected paths
    ├── listings_scored.csv   # precomputed per-listing scores (for the app)
    └── top100_reviews.json   # reviews for the Top-100 shown in the app
```

## Reproduce

1. Python 3.12. Install dependencies: `pip install -r requirements.txt`.  
2. Download the Inside Airbnb datasets (`listings.csv`, `reviews.csv`) into `data/` (see `data/README.md`). They are not committed here due to size.  
3. Run `TFM.ipynb` **from the repo root** to reproduce the pipeline and export the scored files (`listings_scored.csv`, `top100_reviews.json`). The notebook reads data from a `data/` folder relative to the repo root (`DATA_DIR = Path("data")`), so launch Jupyter from the repo root.  
4. Launch the demo: `streamlit run src/app.py`.

The precomputed score files are included so the demonstrator runs without re-executing the full pipeline.

## Data

Public data only (Inside Airbnb listings and reviews; GTFS public transport; Open Data BCN points of interest; neighbourhood income; district security). Sources, filenames and expected paths are documented in [`data/README.md`](http://data/README.md).  
