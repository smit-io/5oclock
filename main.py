import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from src import download, database, city_finder
import random

# Lifespan event to handle startup tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Checking for data and database updates...")
    
    # 1. Ensure data is downloaded
    download.run_downloads()
    
    # 2. Build or update database if needed
    # (The database.process_data script handles 'replace' or updates)
    if not os.path.exists("cities.db"):
        database.process_data("cities.db")
    
    logging.info("Startup complete. App is ready.")
    yield
    # Shutdown logic would go here if needed

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def index(request: Request, hour: int = 17, pop: int = 50000):
    cities = city_finder.find_cities(hour=hour, min_pop=pop)
    selected_city = random.choice(cities) if cities else None
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "city": selected_city, 
        "hour": hour
    })