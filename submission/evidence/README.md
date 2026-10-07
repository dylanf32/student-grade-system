# Evidence — Capture These Before Submission

This folder is for screenshots and actual test/demo evidence.

## Required captures

1. **Terminal screenshot:** `python -m unittest discover -s tests -q` showing `Ran 147 tests … OK`
2. **Dashboard screenshot:** The web app loaded with the demo roster, showing:
   - Stats grid (total, average, passing rate, highest, GPA)
   - Grade Distribution chart with colored bars
   - Support Panel showing the 4 below-threshold students
   - Student table with all 18 demo students
3. **Demo workflow screenshot:** After updating a below-threshold student's grade to ≥ 60,
   showing that student disappears from the Support Panel
4. **API response screenshot (optional):** `GET /api/insights` JSON response in a browser

## How to load the demo roster

```bash
cp data/demo_students.json data/students.json
python run_web.py
# Open http://localhost:5000
```

## Naming convention

`01-test-results.png`, `02-dashboard-overview.png`, `03-grade-update-demo.png`, etc.
