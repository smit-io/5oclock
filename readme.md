# TimeFinder 🌍⏰🍻

**Because it’s always 5 o’clock somewhere.**

TimeFinder started as a way to answer something that isn’t really a question:

> **“It’s 5 o’clock somewhere.”**

What began as a curiosity quickly turned into a deeper exploration of **timezones, geography, population data**, and the surprisingly interesting towns and cities that rarely make it onto maps.

Over time, the idea expanded:

* Not just **5 PM**, but **any hour**
* Not just major cities, but **lesser-known towns**
* Not just trivia, but **accurate, DST-safe data**

This project became a way to **learn geography through time** 🌐🕰️.

---

## ✨ What This Project Does

* 📥 Downloads and parses **GeoNames** datasets
* 🗄️ Builds optimized **SQLite databases**
* 🕒 Answers questions like:

  * *Which cities are currently at 17:00?*
  * *What towns are waking up right now?*
* 🌎 Correctly handles **DST and timezone quirks**
* ⚖️ Supports **round-robin fairness** across countries
* 📦 Exports **static JSON per timezone**
* 🚀 Designed for **frontend-friendly consumption**

---

## 📁 Project Structure

```text
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

## 🚀 Quick Start (Docker)

The easiest way to get started is with Docker.

### 🐳 Docker Compose

```yaml
services:
  service:
    image: ghcr.io/smit-io/5oclock:static
    container_name: 5oclock_static
    restart: unless-stopped
    ports:
      - 8043:8043
```

Then run:

```bash
docker compose up -d
```

Visit:

```text
http://localhost:8043
```

🍻 You’re now exploring cities around the world by time.

---

## 🗄️ Databases

### `geonames.db` (Raw Source)

* Raw GeoNames imports
* Countries, admin divisions, cities
* Never queried directly by app logic

---

### `cities.db` (Optimized)

Purpose-built for queries:

* `cities`
* `iana_timezones`

Each city:

* 🌍 Belongs to exactly **one IANA timezone**
* 📍 Stores lat/lng
* 👥 Stores population
* ⏱️ Does **not** store UTC offsets

---

## 🕒 Why Offsets Are Not Stored

UTC offsets change because of **DST**.

Instead:

* Offsets are computed dynamically using `zoneinfo`
* Ensures correctness year-round
* Avoids stale data bugs ❌

---

## 🔍 Core Queries

### Cities at a given hour

```python
cities_at_hour(session, hour=17)
```

With limit:

```python
cities_at_hour(session, hour=17, limit=50)
```

With round-robin fairness:

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

## ⚖️ Round-Robin Fairness

Without fairness:

```text
USA, USA, USA, Canada, Mexico
```

With round-robin by country:

```text
USA, Canada, Mexico, USA, USA
```

* Applied **only at query time**
* Never baked into storage or exports
* Optional and configurable

---

## 📦 Static JSON Export

Generated files:

```text
json/timezones/
├── America_New_York.json
├── Europe_London.json
├── Asia_Kolkata.json
└── timezone.json
```

Each timezone file:

* 📄 One timezone per file
* 🌎 Cities grouped by country
* 📊 Sorted by population
* 🔁 Regenerated only if missing or forced

---

## 🗂️ `timezone.json`

* Lists all available timezone JSON files
* Enables fast frontend discovery
* Avoids directory scans

---

## 🧠 Design Philosophy

* ✅ Correctness over shortcuts
* 🕰️ DST-safe by design
* 📦 Static where possible
* 🔍 Explicit over magic
* 🌍 Geography-first mindset

---

## 🛣️ Roadmap

Planned improvements and ideas:

* 🚀 **FastAPI API layer**
  * Query cities by hour via HTTP
  * Optional filters (population, country)
* 🎄 **Structured logging**
  * Build-time logs
  * Query diagnostics
* 🧪 More tests & validation
* 📊 Additional metadata (regions, hemispheres)
* 🗺️ Visualizations & maps

---

## ❤️ Why This Exists

This project exists because:

* Timezones are fascinating
* Geography is underrated
* Small towns matter
* “It’s 5 o’clock somewhere” deserved a real answer
