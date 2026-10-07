# GradePulse — Deployment Instructions

## Local development (verified working)

### Requirements

```
Python >= 3.10
Flask  (see requirements.txt)
```

### Install and run

```bash
# 1. Clone the repository
git clone <your-github-repo-url>
cd student-grade-system

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the web server
python run_web.py
# Server starts on http://localhost:5000

# 4. Run all tests
python -m unittest discover -s tests -q
```

### Load the demo roster

Copy the included demo data file over the default data file to start with 18 representative students:

```bash
cp data/demo_students.json data/students.json   # macOS / Linux
copy data\demo_students.json data\students.json  # Windows
```

Then restart the server. The dashboard will show the demo roster with the grade-distribution chart
and the Support Panel pre-populated with 4 students below the passing threshold.

---

## Production hosting

> **Note:** A live URL has not been confirmed yet. The instructions below describe the
> recommended setup. Update this file with the verified live URL before submission.

### Recommended: Render (free tier)

Render supports persistent disk and a single Python process — matching the app's in-process JSON storage.

1. Create a new **Web Service** on [render.com](https://render.com).
2. Connect your GitHub repository.
3. Set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python run_web.py`
   - **Environment:** Python 3
4. Add a **Persistent Disk** (mount path `/opt/render/project/src/data`) so
   `data/students.json` survives redeploys.
5. Set environment variable `PORT` if needed (the app already reads `os.environ.get('PORT', 5000)`).

### Alternative: Railway

Similar process; add a volume at `/app/data`.

### Important: storage warning

The default storage backend writes `data/students.json` to the local filesystem.
On ephemeral or multi-worker hosts (e.g., Heroku free tier without a persistent volume, or
any host that rebuilds the container on redeploy), saved data will be lost on restart.
Use a host with a persistent volume, or replace `JsonStorage` with a SQLite or PostgreSQL
backend by implementing a new subclass of `app/storage/base_storage.py`.

---

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `5000` | HTTP port the Flask app listens on |

---

## Verified deployment checklist

- [ ] Repository is public and accessible to judges
- [ ] `python run_web.py` starts without errors on a clean install
- [ ] `python -m unittest discover -s tests -q` reports all tests passing
- [ ] Live URL is confirmed and tested (CRUD, persist through reload, support panel visible)
- [ ] Demo data (`data/demo_students.json`) is committed and readable
- [ ] README updated with live URL
