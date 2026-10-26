"""Download the three public datasets into data/raw/ and record where they came from.

Olist files arrive as zip archives from Kaggle's public download endpoint (no login
needed); Hillstrom is a single CSV from the author's site. A SHA-256 of every file is
written to data/raw/DOWNLOAD_INFO.txt so results can be tied to an exact copy.
"""
import hashlib
import urllib.request
import zipfile
from datetime import datetime, timezone

from config import RAW, SOURCES


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url, dest):
    if dest.exists():
        print(f"  exists, skipping: {dest.name}")
        return
    req = urllib.request.Request(url, headers={"User-Agent": "sql-ab-analysis/1.0"})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        f.write(r.read())
    print(f"  downloaded {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    targets = {
        "olist": RAW / "olist.zip",
        "olist_funnel": RAW / "olist_funnel.zip",
        "hillstrom": RAW / "hillstrom.csv",
    }
    for key, dest in targets.items():
        print(f"[{key}]")
        fetch(SOURCES[key], dest)
        if dest.suffix == ".zip":
            with zipfile.ZipFile(dest) as z:
                z.extractall(RAW / key)
                print(f"  extracted {len(z.namelist())} files to {key}/")

    lines = [f"Downloaded (UTC): {datetime.now(timezone.utc):%Y-%m-%d %H:%M}", ""]
    for key, dest in targets.items():
        lines.append(f"{key}: {SOURCES[key]}")
        lines.append(f"  {dest.name}  sha256={sha256(dest)}")
    (RAW / "DOWNLOAD_INFO.txt").write_text("\n".join(lines) + "\n")
    print("wrote DOWNLOAD_INFO.txt")


if __name__ == "__main__":
    main()
