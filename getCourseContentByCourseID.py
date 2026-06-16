import sys
import os
import re
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

OUTPUT_DIR  = Path("schoology_backup")
SESS_COOKIE = "SESS_COOKIE"
CSRF_KEY    = "CSRF_KEY"
CSRF_TOKEN  = "CSRF_TOKEN"
BASE_URL    = "https://schoology.harker.org"
DELAY       = 0.4

HEADERS = {
    "Cookie": f"SESSe46255d9e858c8a948fcf4c02c56d2a2={SESS_COOKIE}",
    "Accept": "application/json",
    "X-Csrf-Key": CSRF_KEY,
    "X-Csrf-Token": CSRF_TOKEN,
}


def api_get(path: str) -> dict:
    """Fetch a Schoology API path and return parsed JSON."""
    url = f"{BASE_URL}{path}" if path.startswith("/") else path
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  [api-err] HTTP {e.code} — {url}")
        return {}
    except Exception as e:
        print(f"  [api-err] {e} — {url}")
        return {}


def api_get_all(path: str, list_key: str) -> list:
    """Fetch all pages of a paginated API endpoint, merging the list under list_key."""
    # Add a high limit to reduce number of round-trips
    sep = "&" if "?" in path else "?"
    url = f"{BASE_URL}{path}{sep}limit=200" if path.startswith("/") else f"{path}{sep}limit=200"
    results = []
    while url:
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            print(f"  [api-err] HTTP {e.code} — {url}")
            break
        except Exception as e:
            print(f"  [api-err] {e} — {url}")
            break
        results.extend(data.get(list_key, []))
        url = data.get("links", {}).get("next")
        if url:
            time.sleep(DELAY)
    return results


def fix_url(url: str) -> str:
    """Rewrite api.schoology.harker.org URLs to the working hostname."""
    return url.replace("https://api.schoology.harker.org/v1/", f"{BASE_URL}/")


def clean_name(name: str) -> str:
    name = re.sub(r"^#+\s*", "", name).strip()
    name = re.sub(r'[\\/*?:"<>|]', "-", name)
    return name[:100]


def download_file(url: str, dest: Path):
    if dest.exists():
        print(f"    [skip] {dest.name}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        print(f"    [dl]   {dest.name}")
        req = urllib.request.Request(fix_url(url), headers={
            "Cookie": f"SESSe46255d9e858c8a948fcf4c02c56d2a2={SESS_COOKIE}"
        })
        with urllib.request.urlopen(req) as r:
            dest.write_bytes(r.read())
        time.sleep(DELAY)
    except urllib.error.HTTPError as e:
        print(f"    [err]  HTTP {e.code} — {dest.name}")
    except Exception as e:
        print(f"    [err]  {e} — {dest.name}")


def extract_downloads(doc_data: dict) -> list[tuple[str, str]]:
    """Pull (filename, download_url) pairs out of a document's attachment data."""
    results = []

    def recurse(obj):
        if isinstance(obj, dict):
            if "download_path" in obj and "filename" in obj:
                url = obj["download_path"]
                filename = obj.get("filename") or obj.get("title", "file")
                if url and url.startswith("http"):
                    results.append((filename, url))
            for v in obj.values():
                recurse(v)
        elif isinstance(obj, list):
            for item in obj:
                recurse(item)

    recurse(doc_data)
    return results


def process_folder_item(section_id: str, item: dict, out_dir: Path, visited_folders: set):
    """Handle one item from a folder listing — recurse into sub-folders or download docs."""
    itype = item.get("type")
    title = clean_name(item.get("title", "untitled"))
    iid   = item.get("id")

    if itype == "folder":
        if iid in visited_folders:
            return  # already processed this folder via another path
        visited_folders.add(iid)
        print(f"  {'  ' * out_dir.parts.count(out_dir.parts[0])}[folder] {title}")
        sub_items = api_get_all(f"/v1/courses/{section_id}/folder/{iid}", "folder-item")
        time.sleep(DELAY)
        for sub_item in sub_items:
            process_folder_item(section_id, sub_item, out_dir / title, visited_folders)

    elif itype == "document":
        # The folder listing doesn't include attachments — fetch the full document
        doc_data = api_get(f"/v1/sections/{section_id}/documents/{iid}")
        time.sleep(DELAY)
        for filename, url in extract_downloads(doc_data):
            download_file(url, out_dir / filename)


def scrape_section(section_id: str):
    print(f"\n{'='*60}")

    # Get section metadata for the course name
    meta = api_get(f"/v1/sections/{section_id}")
    if not meta:
        print(f"ERROR: Could not fetch section {section_id}. Check the ID and cookie.")
        return
    time.sleep(DELAY)

    course_name = clean_name(f"{meta.get('course_title','')} {meta.get('section_title','')}".strip())
    print(f"Course: {course_name}  (active={meta.get('active')})")
    out_root = OUTPUT_DIR / course_name

    # Get top-level folders (paginated)
    top_folders = api_get_all(f"/v1/sections/{section_id}/folders", "folders")
    time.sleep(DELAY)

    # Get top-level documents (not inside any folder, paginated)
    all_docs = api_get_all(f"/v1/sections/{section_id}/documents", "document")
    time.sleep(DELAY)

    # Top-level documents
    for doc in all_docs:
        # Only process docs that are at root (course_fid == 0 or null)
        if not doc.get("course_fid"):
            full_doc = api_get(f"/v1/sections/{section_id}/documents/{doc['id']}")
            time.sleep(DELAY)
            for filename, url in extract_downloads(full_doc):
                download_file(url, out_root / filename)

    # Walk folders recursively
    visited_folders: set = set()
    for folder in top_folders:
        process_folder_item(section_id, {**folder, "type": "folder"}, out_root, visited_folders)

    print(f"\n  Done with {course_name}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    section_ids = sys.argv[1:]
    for sid in section_ids:
        scrape_section(sid.strip())

    print(f"\n✓ All done → {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
