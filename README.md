# Scraper

A set of Python scripts to interact with the Schoology API, scrape course materials, and query user/course data.

## Setup

Before running any of the scripts, you must provide your active Schoology access credentials.

To find your credentials:
1. Log in to Schoology in your web browser.
2. Open Developer Tools (Right click > Inspect).
3. Navigate to the Network tab and refresh the page.
4. Click on any request made to `schoology.harker.org`.
5. Look at the Request Headers for:
   - `Cookie`: Find the value starting with `SESS...` and copy the hash value.
   - `X-Csrf-Key`: Copy this value.
   - `X-Csrf-Token`: Copy this value.

Open the script you want to use and replace the variables at the top of the file:
```python
SESS_COOKIE = "your_session_cookie_value"
CSRF_KEY    = "your_csrf_key"
CSRF_TOKEN  = "your_csrf_token"
```

## Script Usage

### 1. `getCourseContentByCourseID.py`
Downloads all files, folders, and resources from specific Schoology course sections. The downloaded files maintain the original folder hierarchy and are saved into a `schoology_backup/` directory.

**Usage:**
```bash
python getCourseContentByCourseID.py <section_id> [section_id_2 ...]
```
*Example:* `python getCourseContentByCourseID.py 1234567890`

---

### 2. `getCoursesByGroupID.py`
Fetches a list of all members within a Schoology Group and queries the API for the courses each member is taking. By default, it ignores users with very few courses (depending on the season) and outputs the results to a JSON file.

**Usage:**
```bash
python getCoursesByGroupID.py <group_id> [output_file.json]
```
*Example:* `python getCoursesByGroupID.py 9876543210 my_group_courses.json`
*(If no output file is provided, it defaults to `group_<group_id>_courses.json`)*

---

### 3. `getCoursesByUID.py`
Fetches and prints out the courses (including the detected period/advisory) that a specific Schoology user is enrolled in.

**Usage:**
```bash
python getCoursesByUID.py <user_id> [user_id_2 ...]
```
*Example:* `python getCoursesByUID.py 1122334455`
