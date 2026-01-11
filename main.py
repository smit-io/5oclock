from fastapi import BackgroundTasks, FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from src import tz_locator, constants

app = FastAPI(title="5o Clock API - Grouped Mode")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def serve_website(
    request: Request, 
    hour: int = Query(constants.TARGET_24H), 
    pop: int = Query(constants.POP_LIMIT)
):
    city, final_pop = tz_locator.pick_random_city(hour, pop)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "city": city,
        "target_hour": hour,      # Pass this to the template
        "target_pop": pop,        # Pass this to the template
        "found_at_pop": final_pop
    })

@app.get("/api/all", tags=["API"])
async def api_all(hour: int = constants.TARGET_24H, pop: int = constants.POP_LIMIT):
    """Find all cities matching exactly."""
    cities = tz_locator.get_cities(hour, pop)
    return {"count": len(cities), "cities": cities}

@app.get("/api/all-recursive", tags=["API"])
async def api_recursive(hour: int = constants.TARGET_24H, pop: int = constants.POP_LIMIT):
    """Find all cities, reducing population threshold until found."""
    cities, final_pop = tz_locator.get_cities_until_found(hour, pop)
    return {"count": len(cities), "original_pop": pop, "found_at_pop": final_pop, "cities": cities}

@app.get("/api/random", tags=["API"])
async def api_random(hour: int = constants.TARGET_24H, pop: int = constants.POP_LIMIT):
    """Pick a random city, reducing population threshold if none found."""
    city, final_pop = tz_locator.pick_random_city(hour, pop)
    if not city:
        return {"message": f"No cities found even after reducing population from {pop}."}
    return {"city": city, "found_at_pop": final_pop}

@app.post("/api/rebuild")
async def rebuild_database(
    background_tasks: BackgroundTasks,
    force: bool = Query(False)
):
    """
    Triggers a rebuild of the GeoNames database.
    Using BackgroundTasks so the HTTP request doesn't timeout 
    during the large file download.
    """
    background_tasks.add_task(tz_locator.build_database, force=force)
    return {"message": "Database rebuild started in the background.", "force_used": force}