import zipfile
import requests
import os
from datetime import datetime
from pathlib import Path
from src.constants import BASE_URL, INPUT_DIR

def get_remote_last_modified(url: str) -> datetime:
    """Fetches the Last-Modified header from the server."""
    response = requests.head(url, allow_redirects=True)
    response.raise_for_status()
    last_modified_str = response.headers.get('Last-Modified')
    if last_modified_str:
        return datetime.strptime(last_modified_str, '%a, %d %b %Y %H:%M:%S %Z')
    return None

def extract_zip(file_path: Path):
    """Extracts a zip file to the same directory and removes the zip file."""
    print(f"Extracting {file_path.name}...")
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(file_path.parent)
    
    # Optional: Remove the zip after extraction to keep storage clean
    # file_path.unlink() 
    print(f"Extraction complete for {file_path.name}")

def download_geonames_file(filename: str, force: bool = False):
    url = f"{BASE_URL}{filename}"
    local_path = INPUT_DIR / filename
    
    exists = local_path.exists()
    should_download = force or not exists
    
    if exists and not force:
        remote_date = get_remote_last_modified(url)
        local_date = datetime.fromtimestamp(local_path.stat().st_mtime)
        
        if remote_date and remote_date > local_date:
            print(f"Update available for {filename}...")
            should_download = True
        else:
            print(f"{filename} is already up to date.")

    if should_download:
        print(f"Downloading {filename}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # New: Automatically extract if it's a ZIP file
        if local_path.suffix == '.zip':
            extract_zip(local_path)
            
        print(f"Successfully processed {filename}")

def sync_all_datasets(files_dict: dict, force: bool = False):
    """Loops through the required files and syncs them."""
    for key, filename in files_dict.items():
        try:
            download_geonames_file(filename, force=force)
        except Exception as e:
            print(f"Failed to download {filename}: {e}")