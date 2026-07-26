# Data

This project uses **public data only**. The two Inside Airbnb files (`listings.csv`, `reviews.csv`) are **not committed** (size); download them (archived December 2025, Barcelona city) into this `data/` folder from the source below. All other datasets and the precomputed files are already in the repo. Files are read directly from here.

| Dataset | Expected file | In repo? | Source |
| :---- | :---- | :---- | :---- |
| Listings | `listings.csv` | download | Inside Airbnb — Barcelona: [https://insideairbnb.com/es/get-the-data/](https://insideairbnb.com/es/get-the-data/) |
| Reviews | `reviews.csv` | download | Inside Airbnb — Barcelona (same page) |
| Public transport stops | `stops.txt` | yes | GTFS feed for Barcelona public transport (TMB / ATM): [link](https://t-mobilitat.atm.cat/web/t-mobilitat/datos-abiertos/catalogo-de-datos/informacion-estatica) |
| Points of interest | `opendatabcn_pics-csv.csv` | yes | Open Data BCN: [link](https://opendata-ajuntament.barcelona.cat/data/es/dataset/punts-informacio-turistica/resource/31431b23-d5b9-42b8-bcd0-a84da9d8c7fa) |
| Neighbourhood income | `2022_renda_disponible_llars_per_persona.csv` | yes | Idescat / Open Data BCN (disposable household income, 2022): [link](https://opendata-ajuntament.barcelona.cat/data/ca/dataset/renda-disponible-llars-bcn/resource/3df0c5b9-de69-4c94-b924-57540e52932f) |
| District security | `Taula estadistica.csv` | yes | District incident statistics (Mossos d'Esquadra / open data): [link](https://portaldades.ajuntament.barcelona.cat/ca/estad%C3%ADstiques/co6rdrzcdj?view=table) |

## Precomputed files (included in the repo)

So the Streamlit demonstrator runs without re-executing the full pipeline:

- `listings_scored.csv` — final per-listing base, authenticity and final scores.  
- `top100_reviews.json` — the reviews shown for the Top-100 in the app.

## Expected layout

```
data/
├── listings.csv                                      (download from Inside Airbnb)
├── reviews.csv                                       (download from Inside Airbnb)
├── stops.txt                                         (in repo)
├── opendatabcn_pics-csv.csv                          (in repo)
├── 2022_renda_disponible_llars_per_persona.csv       (in repo)
├── Taula estadistica.csv                             (in repo)
├── listings_scored.csv                               (in repo)
└── top100_reviews.json                               (in repo)
```

> Note: Inside Airbnb and the open-data portals distribute their data under their own terms.  
