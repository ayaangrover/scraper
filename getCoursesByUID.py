import sys
import json
import urllib.request
import urllib.error

SESS_COOKIE = "SESS_COOKIE"
CSRF_KEY    = "CSRF_KEY"
CSRF_TOKEN  = "CSRF_TOKEN"
BASE_URL    = "https://schoology.harker.org"

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
        print(f"  [api-err] HTTP {e.code} — {url}")
        return {}
    except Exception as e:
        print(f"  [api-err] {e} — {url}")
        return {}


def list_courses(user_id: str):
    print(f"\n{'='*60}")
    print(f"User {user_id}")

    data = api_get(f"/v1/users/{user_id}/sections")
    sections = data.get("section", [])

    if not sections:
        print("  (no sections found — check user ID and cookie)")
        return

    for s in sections:
        period = get_period(s.get("section_title", ""))
        period_str = period if period else "period ?"
        print(f"  {s.get('id')}: {s.get('course_title')} — {s.get('section_title')} "
              f"({period_str}, active={s.get('active')})")


def get_period(section_title: str) -> str | None:
    """Extract the period from a section title.

    Summer courses (e.g. "SC221S 1 AP® Chemistry (Summer)") only have periods 1-2,
    given directly as the second token.

    Regular-year courses (e.g. "MT212 30 Honors Algebra 2") encode the period as
    the second token times 10 (10 = period 1, ... 70 = period 7), except 1, which
    means advisory.
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


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    for user_id in sys.argv[1:]:
        list_courses(user_id.strip())


if __name__ == "__main__":
    main()
