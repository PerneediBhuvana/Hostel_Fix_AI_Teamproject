# HOSTELFIX AI - Run & Logins

## Run (Windows) - easiest
Double-click `start_all.bat`  ->  opens http://localhost:5173

## Run (manual, 2 terminals)
Terminal 1 (backend):
    cd backend
    python -m venv .venv
    .\.venv\Scripts\activate.bat        (PowerShell: .\.venv\Scripts\Activate.ps1)
    pip install -r requirements.txt
    python seed.py
    python run.py                        -> http://localhost:5000

Terminal 2 (frontend):
    cd frontend
    npm install
    npm run dev                          -> http://localhost:5173

## Logins  (select the MATCHING ROLE TAB on the login page!)
| Role tab            | Email                 | Password       |
|---------------------|-----------------------|----------------|
| Student             | student@college.edu   | Student@12345  |
| Faculty Coordinator | faculty1@college.edu  | Smith@2026     |
| Faculty Coordinator | faculty2@college.edu  | Johnson@2026   |
| Faculty Coordinator | faculty3@college.edu  | Williams@2026  |
| Warden              | warden1@college.edu   | WardenA@2026   |
| Warden              | warden2@college.edu   | WardenB@2026   |
| Maintenance Staff   | staff1@college.edu    | Staff1@2026    |
| Maintenance Staff   | staff2@college.edu    | Staff2@2026    |
| Maintenance Staff   | staff3@college.edu    | Staff3@2026    |
| Admin               | admin@college.edu     | Admin@12345    |

`python seed.py` resets all these passwords every time it runs.
Passwords are case-sensitive. Use .college.edu emails (NOT havendesk.local).

## First run after updating
Run `python seed.py` again (in backend). It keeps your accounts and adds ~100 demo complaints
(5 demo residents: resident1..5@college.edu / Resident@2026) so AI Insights has data to analyse.

## AI / ML  (all trained locally with scikit-learn, no API key needed)
- Complaint classifier: TF-IDF + Logistic Regression predicts category and priority while the student types
  (backend/app/ml/complaint_classifier.py, training data in complaint_data.py). Safety words (fire, shock,
  flooding, food poisoning...) always force Urgent. If the model is unsure it falls back to keyword rules.
- Live AI suggestion on "Raise Complaint": category, priority, estimated fix time, similar open complaints.
- AI Insights (Admin and Warden sidebar): hotspot detection (sudden spikes per block and category),
  weekly volume forecast (Linear Regression), resolution-time estimates (Ridge Regression),
  satisfaction by category, recommendations (backend/app/ml/insights.py).
- Food Waste Predictor: scikit-learn LinearRegression (backend/app/ml/food_predictor.py).
- Check the classifier numbers any time:  cd backend  then  python -m app.ml.complaint_classifier

Try it: login as Admin -> AI Insights (you should see Internet in Block B and Water in Block A flagged).
Login as Student -> Raise Complaint -> type "Fire sparking near switch board" and watch category/priority fill in.
