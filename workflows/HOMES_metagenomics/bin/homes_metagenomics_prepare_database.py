#!/usr/bin/env python3

import argparse
import csv
import re
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen


def clean(value):
    return str(value or "").strip()


def truthy(value):
    return clean(value).lower() not in {"", "0", "false", "f", "no", "n", "none", "null"}


def safe_name(value):
    value = clean(value) or "database"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "database"


def normalize_download_url(url):
    parsed = urlparse(url)
    if parsed.scheme == "s3":
        key = parsed.path.lstrip("/")
        return f"https://{parsed.netloc}.s3.amazonaws.com/{key}"
    return url


def infer_name(database_set, database_url):
    if clean(database_set) and clean(database_set).lower() not in {"none", "null"}:
        return safe_name(database_set)
    if clean(database_url):
        name = Path(urlparse(database_url).path).name
        for suffix in [".tar.gz", ".tgz", ".tar", ".zip", ".gz"]:
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break
        return safe_name(name)
    return "database"


def is_relative_to(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def download(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    with urlopen(normalize_download_url(url)) as response, partial.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    partial.replace(destination)


def safe_extract_tar(archive, target_dir):
    target_root = target_dir.resolve()
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        for member in members:
            destination = (target_root / member.name).resolve()
            if not is_relative_to(destination, target_root):
                raise RuntimeError(f"Unsafe path in tar archive: {member.name}")
        tar.extractall(target_root, members=members)


def safe_extract_zip(archive, target_dir):
    target_root = target_dir.resolve()
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            destination = (target_root / member.filename).resolve()
            if not is_relative_to(destination, target_root):
                raise RuntimeError(f"Unsafe path in zip archive: {member.filename}")
        zf.extractall(target_root)


def extract_or_copy(archive, target_dir):
    target_dir.mkdir(parents=True, exist_ok=True)
    name = archive.name
    if name.endswith((".tar.gz", ".tgz", ".tar")):
        safe_extract_tar(archive, target_dir)
        return
    if name.endswith(".zip"):
        safe_extract_zip(archive, target_dir)
        return
    shutil.copy2(archive, target_dir / archive.name)


def marker_path(cache_dir):
    return cache_dir / ".homes_metagenomics_database.complete"


def archive_name_from_url(url, default_name):
    name = Path(urlparse(url).path).name
    return name or f"{default_name}.download"


def prepare_cached_asset(store_dir, database_name, asset_name, asset_url, allow_download):
    asset_url = clean(asset_url)
    if not asset_url:
        return "", "not_configured", ""

    cache_dir = store_dir / database_name / asset_name
    marker = marker_path(cache_dir)
    if marker.exists():
        return str(cache_dir), "reused", "Using cached asset; download skipped."

    if not allow_download:
        return str(cache_dir), "download_disabled", "Asset URL was provided, but downloads are disabled and no completed cache exists."

    downloads_dir = store_dir / "_downloads" / database_name
    archive = downloads_dir / archive_name_from_url(asset_url, asset_name)
    if not archive.exists():
        download(asset_url, archive)
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    extract_or_copy(archive, cache_dir)
    marker.write_text(f"asset={asset_name}\nurl={asset_url}\n")
    return str(cache_dir), "downloaded", "Downloaded asset into cache."


def check_existing_path(value, label):
    if not clean(value):
        return ""
    path = Path(value).expanduser().resolve()
    if not path.exists():
        print(f"ERROR: --{label} does not exist: {path}", file=sys.stderr)
        raise SystemExit(1)
    return str(path)


def write_info(path, row):
    fieldnames = [
        "database_set",
        "status",
        "database_path",
        "bracken_path",
        "taxonomy_path",
        "reference_url",
        "ref2taxid_url",
        "store_dir",
        "database_url",
        "taxonomy_url",
        "message",
    ]
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerow(row)


def combined_status(statuses):
    active = [status for status in statuses if status and status != "not_configured"]
    if not active:
        return "not_configured"
    if "downloaded" in active:
        return "downloaded"
    if "download_disabled" in active:
        return "download_disabled"
    if all(status == "provided" for status in active):
        return "provided"
    if "reused" in active:
        return "reused"
    return active[0]


def main():
    parser = argparse.ArgumentParser(description="Prepare and cache HOMES metagenomics databases.")
    parser.add_argument("--database_set", default="")
    parser.add_argument("--database_url", default="")
    parser.add_argument("--taxonomy_url", default="")
    parser.add_argument("--reference_url", default="")
    parser.add_argument("--ref2taxid_url", default="")
    parser.add_argument("--database_name", default="")
    parser.add_argument("--store_dir", required=True)
    parser.add_argument("--kraken2_db", default="")
    parser.add_argument("--bracken_db", default="")
    parser.add_argument("--taxonomy", default="")
    parser.add_argument("--download_databases", default="true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    database_set = clean(args.database_set)
    database_url = clean(args.database_url)
    taxonomy_url = clean(args.taxonomy_url)
    store_dir = Path(args.store_dir).expanduser().resolve()
    database_name = safe_name(args.database_name) if clean(args.database_name) else infer_name(database_set, database_url)
    allow_download = truthy(args.download_databases)

    messages = []
    statuses = []

    if clean(args.kraken2_db):
        database_path = check_existing_path(args.kraken2_db, "kraken2_db")
        bracken_path = check_existing_path(args.bracken_db, "bracken_db") if clean(args.bracken_db) else database_path
        db_status = "provided"
        messages.append("Using user-provided Kraken2 database path.")
    else:
        database_path, db_status, db_message = prepare_cached_asset(
            store_dir, database_name, "kraken2", database_url, allow_download
        )
        bracken_path = database_path
        if db_message:
            messages.append(f"kraken2: {db_message}")
    statuses.append(db_status)

    if clean(args.taxonomy):
        taxonomy_path = check_existing_path(args.taxonomy, "taxonomy")
        taxonomy_status = "provided"
        messages.append("Using user-provided taxonomy path.")
    else:
        taxonomy_path, taxonomy_status, taxonomy_message = prepare_cached_asset(
            store_dir, database_name, "taxonomy", taxonomy_url, allow_download
        )
        if taxonomy_message:
            messages.append(f"taxonomy: {taxonomy_message}")
    statuses.append(taxonomy_status)

    status = combined_status(statuses)
    if not messages:
        messages.append("No local database path or preset URL was provided; database download was skipped.")

    write_info(
        args.output,
        {
            "database_set": database_set,
            "status": status,
            "database_path": database_path,
            "bracken_path": bracken_path,
            "taxonomy_path": taxonomy_path,
            "reference_url": clean(args.reference_url),
            "ref2taxid_url": clean(args.ref2taxid_url),
            "store_dir": str(store_dir),
            "database_url": database_url,
            "taxonomy_url": taxonomy_url,
            "message": " ".join(messages),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
