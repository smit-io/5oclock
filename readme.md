# TimeFinder 🌍⏰

**Build a local, timezone-aware city dataset and find cities around the world by local hour.**

TimeFinder ingests **GeoNames** data, normalizes it into optimized SQLite databases, exports static timezone-based JSON files, and supports powerful queries like:

> *“Which cities in the world are currently at 5 PM?”*

This project is **data-first**, **DST-safe**, and designed for **fast local querying** and **frontend-friendly exports**.

---

## What This Project Does

* Downloads and parses **GeoNames** datasets
* Builds two SQLite databases:

  * `geonames.db` (raw source-of-truth)
  * `cities.db` (query-optimized)
* Builds a canonical **IANA timezone table**
* Finds cities at a given local hour (DST-safe)
* Optionally applies **round-robin fairness**
* Exports **static JSON files per timezone**
* Generates a `_timezone.index` for fast frontend loading

---

## Project Structure

```
.
├── main.py                     # Entry point (build + query orchestration)
├── config.py                   # Global configuration & flags
│
├── downloader/
│   └── geonames.py             # GeoNames file downloader
│
├── geonames_db/
│   ├── importer.py             # Parse GeoNames into geonames.db
│   └── models.py               # GeoNames ORM models
│
├── cities_db/
│   ├── importer.py             # Build cities.db from geonames.db
│   ├── models.py               # City & IANA timezone models
│   └── queries.py              # High-level query helpers
│
├── services/
│   └── timezone_service.py     # DST-safe timezone calculations
│
├── export/
│   └── timezone_json_exporter.py  # Per-timezone JSON generation
│
├── utils/
│   ├── round_robin.py          # Optional fairness shuffling
│   ├── files.py                # File helpers
│   └── hashing.py              # Change detection utilities
│
├── db/
│   ├── base.py                 # SQLAlchemy base
│   └── session.py              # DB session management
│
├── schemas/
│   ├── cities.py               # Output schemas
│   └── geonames.py
│
├── src/
│   ├── constants.py
│   ├── data_aggregator.py
│   └── tz_locator.py
│
├── json/
│   └── timezones/              # Generated timezone JSON files
│
├── data/                       # Raw downloaded files
├── databases/                  # SQLite databases
├── cities/                     # Frontend-ready assets
├── dist/                       # Static assets (fonts, etc.)
└── templates/
```

---

## Databases

### `geonames.db` (Raw)

Contains unmodified GeoNames data:

* Cities
* Countries
* Admin divisions
* Population data

This database is **never queried directly by the app logic**.

---

### `cities.db` (Optimized)

Purpose-built for fast queries:

* `iana_timezones`
* `cities`

Each city:

* Is linked to **one IANA timezone**
* Stores population, lat/lng, country, admin info
* Does **not** store UTC offsets (computed dynamically)

---

## Why Offsets Are Not Stored

UTC offsets change due to **DST**.

Instead:

* Offsets are calculated at query time using `zoneinfo`
* This guarantees correctness year-round

---

## Core Queries

### Cities at a given hour

```python
cities_at_hour(session, hour=17)
```

With limit:

```python
cities_at_hour(session, hour=17, limit=50)
```

With optional round-robin fairness:

```python
cities_at_hour(
    session,
    hour=17,
    round_robin_by="country_code"
)
```

---

### Cities in a timezone

```python
cities_in_timezone(session, "America/New_York")
```

---

## Round-Robin Fairness (Optional)

Without fairness:

```
USA, USA, USA, USA, Canada, Mexico
```

With round-robin by country:

```
USA, Canada, Mexico, USA, USA, USA
```

* Applied **at query time**
* Never baked into storage or exports
* Can be turned on/off per call

---

## Static JSON Export

For frontend usage, cities are exported as:

```
json/timezones/
├── America_New_York.json
├── Europe_London.json
├── Asia_Kolkata.json
└── _timezone.index
```

Each file:

* Represents **one timezone**
* Groups cities by country
* Sorted by population (descending)
* Generated only if missing or `FORCE_REBUILD=true`

---

## `_timezone.index`

Automatically generated list of all available timezone JSON files.

Used by frontends to:

* Discover supported timezones
* Avoid filesystem scanning

---

## Build Flow (main.py)

1. Download GeoNames files (if newer)
2. Build `geonames.db`
3. Build `cities.db`
4. Extract unique IANA timezones
5. Run sanity checks
6. Export timezone JSON
7. Generate `_timezone.index`
8. Run queries (optional)

---

## Configuration

All global flags live in `config.py`, including:

* `FORCE_REBUILD`
* Data paths
* Export locations

---

## Performance

* Indexed SQLite tables
* Population-sorted inserts
* Optional limits on queries
* Round-robin runs in **O(n)**

---

## Requirements

* Python **3.10+**
* SQLite
* Key dependencies:

  * `sqlalchemy`
  * `requests`
  * `pytz` / `zoneinfo`

---

## Design Principles

* **Correctness > cleverness**
* **DST-safe by design**
* **No hidden magic**
* **Separation of concerns**
* **Frontend-ready outputs**

---