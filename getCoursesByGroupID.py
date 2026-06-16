import sys
import json
import time
import datetime
import urllib.request
import urllib.error

SESS_COOKIE = "SESS_COOKIE"
CSRF_KEY    = "CSRF_KEY"
CSRF_TOKEN  = "CSRF_TOKEN"
BASE_URL    = "https://schoology.harker.org"
DELAY       = 0.3

HEADERS = {
    "Cookie": f"SESSe46255d9e858c8a948fcf4c02c56d2a2={SESS_COOKIE}",
    "Accept": "application/json",
    "X-Csrf-Key": CSRF_KEY,
    "X-Csrf-Token": CSRF_TOKEN,
}


def api_get(path: str) -> dict:
    url = f"{BASE_URL}{path}" if path.startswith("/") else path
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  [api-err] HTTP {e.code} — {url}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"  [api-err] {e} — {url}", file=sys.stderr)
        return {}


def api_get_all(path: str, list_key: str) -> list:
    sep = "&" if "?" in path else "?"
    url = f"{BASE_URL}{path}{sep}limit=200"
    results = []
    while url:
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            print(f"  [api-err] HTTP {e.code} — {url}", file=sys.stderr)
            break
        except Exception as e:
            print(f"  [api-err] {e} — {url}", file=sys.stderr)
            break
        results.extend(data.get(list_key, []))
        url = data.get("links", {}).get("next")
        if url:
            time.sleep(DELAY)
    return results


def get_period(section_title: str) -> str | None:
    """Extract the period from a section title.

    Summer (e.g. "SC221S 1 AP® Chemistry (Summer)"): second token is period directly.
    Regular (e.g. "MT212 30 Honors Algebra 2"): second token is period * 10 (10–70),
    except 1 which means advisory.
    """
    parts = section_title.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return None
    num = int(parts[1])
    if "(Summer)" in section_title:
        return f"period {num}"
    if num == 1:
        return "advisory"
    if num % 10 == 0:
        return f"period {num // 10}"
    return None


def get_user_courses(uid: str) -> list[dict]:
    data = api_get(f"/v1/users/{uid}/sections")
    sections = data.get("section", [])
    courses = []
    for s in sections:
        section_title = s.get("section_title", "")
        course_title  = s.get("course_title", "")
        period = get_period(section_title)
        courses.append({
            "section_id":    s.get("id"),
            "course_title":  course_title,
            "section_title": section_title,
            "period":        period,
            "active":        bool(int(s.get("active", 0))),
        })
    return courses


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    group_id  = sys.argv[1]
    out_file  = sys.argv[2] if len(sys.argv) >= 3 else f"group_{group_id}_courses.json"

    print(f"Fetching members of group {group_id} …")
    members = api_get_all(f"/v1/groups/{group_id}/enrollments", "enrollment")
    print(f"  {len(members)} members found")

    month = datetime.date.today().month
    is_summer = 6 <= month <= 8
    min_courses = 1 if is_summer else 4
    season = "summer" if is_summer else "school year"
    print(f"Season: {season} — skipping users with fewer than {min_courses} course(s)")

    result = []
    for i, member in enumerate(members):
        uid  = member["uid"]
        name = member.get("name_display", uid)
        print(f"  [{i+1}/{len(members)}] {name} (uid={uid}) …", end=" ", flush=True)
        time.sleep(DELAY)
        courses = get_user_courses(uid)
        if len(courses) < min_courses:
            print(f"only {len(courses)} course(s), skipping")
            continue
        print(f"{len(courses)} course(s)")
        result.append({
            "uid":   uid,
            "name":  name,
            "admin": bool(member.get("admin", 0)),
            "courses": courses,
        })

    with open(out_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n✓ {len(result)} users with courses written to {out_file}")


if __name__ == "__main__":
    main()
