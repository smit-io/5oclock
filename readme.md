# 🍻 Five O'Clock Somewhere

A high-performance, containerized geographic locator that finds cities currently experiencing a specific hour of the day. Whether you're looking for a virtual happy hour or just curious about global time, this tool uses the **GeoNames** database to provide real-time results.

## 🚀 Quick Start with Docker

The easiest way to get the project running is using the provided Docker configuration.

1. **Clone the repository.**
2. **Launch with Docker Compose:**

```bash
docker-compose up --build
```

3. **Access the App:**

* **Jinja2 Website:** `http://localhost:8000/`
* **Static Website:** `http://localhost:8000/static/index.html` (if hosted via FastAPI)
* **API Docs:** `http://localhost:8000/docs`

---

## 🛠 Features

* **Dynamic Clock:** Real-time ticking clock synced to the target city's UTC offset.
* **Persistent Database:** Downloads and aggregates 15,000+ cities from GeoNames and stores them in a local JSON cache.
* **Smart Querying:** Ability to filter by specific hours (0–23) and population thresholds.
* **Sticky Sharing:** Social share links (X, WhatsApp, Telegram) preserve your custom hour and population filters.
* **Dev Container Support:** Pre-configured environment for VS Code.

---

## 📡 API Endpoints

The backend is built with **FastAPI**. All endpoints accept query parameters to filter results.

### `GET /`

Serves the dynamic Jinja2-rendered website.

* **Parameters:**
* `hour` (int): The target hour in 24h format (Default: `17`).
* `pop` (int): Minimum population (Default: `500`).

### `GET /api/random`

Returns a single random city matching the criteria in JSON format.

* **Parameters:** `hour`, `pop`.
* **Response:**

```json
{
  "city": {
    "city": "Sham Shui Po",
    "state": "Sham Shui Po District",
    "country": "Hong Kong",
    "population": 431090,
    "local_time_str": "05:54 PM",
    "timezone_id": "Asia/Hong_Kong",
    "timezone_abbr": "HKT",
    "utc_offset": "+0800"
  },
  "found_at_pop": 15000
}

```

### `GET /api/all`

Returns a list of **all** cities currently at the target hour that meet the population requirement.

```json
{
  "count": 4,
  "cities": [
    {
      "city": "Shenzhen",
      "state": "Guangdong",
      "country": "China",
      "population": 17494398,
      "local_time_str": "05:57 PM",
      "timezone_id": "Asia/Shanghai",
      "timezone_abbr": "CST",
      "utc_offset": "+0800"
    },
    {
      "city": "Shanghai",
      "state": "Shanghai",
      "country": "China",
      "population": 24874500,
      "local_time_str": "05:57 PM",
      "timezone_id": "Asia/Shanghai",
      "timezone_abbr": "CST",
      "utc_offset": "+0800"
    },
    {
      "city": "Guangzhou",
      "state": "Guangdong",
      "country": "China",
      "population": 16096724,
      "local_time_str": "05:57 PM",
      "timezone_id": "Asia/Shanghai",
      "timezone_abbr": "CST",
      "utc_offset": "+0800"
    },
    {
      "city": "Beijing",
      "state": "Beijing",
      "country": "China",
      "population": 18960744,
      "local_time_str": "05:57 PM",
      "timezone_id": "Asia/Shanghai",
      "timezone_abbr": "CST",
      "utc_offset": "+0800"
    }
  ]
}
```

### `GET /api/all-recursive`

This is a "fail-safe" endpoint. If no cities are found at your requested population (e.g., 1,000,000), the logic automatically reduces the population requirement by 10% and searches again. It repeats this until it finds at least one city or hits a minimum floor.

* **Query Parameters:**
* `hour` (int): Target hour in 24h format (0–23).
* `pop` (int): Your preferred minimum population.

* **Key Response Fields:**
* `requested_pop`: The population you originally asked for.
* `final_pop`: The population threshold where cities were actually found.
* `cities`: Array of city objects.

### `POST /api/rebuild`

Manually triggers the background utility to update the local database from GeoNames. This is useful if the data becomes stale or if the `world_cities.json` file is deleted.

* **Query Parameters:**
* `force` (bool): If `true`, the system ignores existing files and re-downloads everything from the source (GeoNames).

* **Behavior:**
* Returns a `200 OK` immediately.
* Processing happens in a **Background Task** to prevent request timeouts.
* Monitor progress via `docker logs`.

---

## 🌐 Website Modes

### 1. Jinja2 Dynamic Mode (Standard)

Accessed at the root `/`. This version uses server-side Python logic to pick the city. It is faster for SEO and social media "unfurling" (OpenGraph).

* **Query Params:** `?hour=20&pop=1000000`

### 2. Static HTML Mode

Found in `static/index.html`. This is a "Client-Side Only" version. It fetches the `world_cities.json` file once and does all calculations in the user's browser.

* **Setup:** Ensure the `DATA_URL` in the script matches your file structure.
* **Logic:** Loops through the timezone-grouped JSON to find matches.

---

## 📂 Project Structure

```text
├── .devcontainer/         # VS Code Dev Container config
├── src/
│   ├── constants.py       # Env var defaults and paths
│   ├── data_aggregator.py # GeoNames download & JSON processing
│   └── tz_locator.py      # Timezone math and city filtering
├── templates/             # Jinja2 HTML files
├── cities/                # Generated world_cities.json (Persistent Volume)
├── geonames/              # Raw GeoNames text files (Persistent Volume)
├── main.py                # FastAPI Application Entry
├── Dockerfile             # Image definition
└── docker-compose.yml     # Container orchestration

```

---

## ⚙️ Environment Variables

You can customize the app behavior by editing the `environment` section in `docker-compose.yml`:

| Variable | Default | Description |
| --- | --- | --- |
| `TARGET_24H` | `17` | The default hour to search for (5 PM). |
| `POP_LIMIT` | `500` | The default minimum population threshold. |
| `PYTHONUNBUFFERED` | `1` | Ensures logs appear in Docker terminal immediately. |

---

## 🔨 Build Docker Image

Build a docker image using the below command, after checking out/cloning the repo.

```bash
docker build -t 5oclock:latest .
```
