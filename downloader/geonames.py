import zipfile
import requests
from pathlib import Path
from utils.hashing import remote_is_newer

def download_if_needed(url: str, dest: Path, force: bool):
    if dest.exists() and not force and not remote_is_newer(url, dest):
        print(f"⏭️  Skipping download of {url}, local file is up to date.")
        return

    r = requests.get(url)
    dest.write_bytes(r.content)

    if dest.suffix == ".zip":
        with zipfile.ZipFile(dest) as z:
            z.extractall(dest.parent)
