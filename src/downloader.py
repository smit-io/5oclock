import os
import requests
import zipfile
import shutil
from datetime import datetime
from src.constants import GEONAMES_URLS, FILES, DATA_DIR, FORCE_REBUILD

def get_remote_mtime(url):
    try:
        response = requests.head(url, timeout=5)
        last_modified = response.headers.get('Last-Modified')
        if last_modified:
            return datetime.strptime(last_modified, '%a, %d %b %Y %H:%M:%S %Z').timestamp()
    except:
        pass
    return 0

def download_file(url, dest):
    print(f"Downloading {url}...")
    response = requests.get(url, stream=True)
    with open(dest, 'wb') as f:
        shutil.copyfileobj(response.raw, f)

def sync_data():
    if FORCE_REBUILD and os.path.exists(DATA_DIR):
        print("FORCE_REBUILD is True. Cleaning data directory...")
        shutil.rmtree(DATA_DIR)
    
    os.makedirs(DATA_DIR, exist_ok=True)

    for key, url in GEONAMES_URLS.items():
        local_path = FILES["cities_txt"] if key == "cities" else FILES[key]
        zip_path = FILES["cities_zip"] if key == "cities" else None
        
        if not os.path.exists(local_path) or get_remote_mtime(url) > os.path.getmtime(local_path):
            target = zip_path if zip_path else local_path
            download_file(url, target)
            if zip_path:
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(DATA_DIR)
                os.remove(zip_path)