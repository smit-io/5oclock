import requests

import requests
from email.utils import parsedate_to_datetime
from pathlib import Path


def remote_is_newer(url: str, local_path: Path, timeout: int = 10) -> bool:
    """
    Returns True if the remote file is newer than the local file,
    or if the local file does not exist.
    """

    if not local_path.exists():
        return True

    try:
        r = requests.head(url, allow_redirects=True, timeout=timeout)
        r.raise_for_status()
    except requests.RequestException:
        # If we can't reliably check, do NOT re-download
        return False

    last_modified = r.headers.get("Last-Modified")
    if not last_modified:
        # Server does not expose modification time → assume newer
        return True

    try:
        remote_dt = parsedate_to_datetime(last_modified)
        remote_ts = remote_dt.timestamp()
    except Exception:
        # Broken header → assume newer
        return True

    local_ts = local_path.stat().st_mtime

    return remote_ts > local_ts
