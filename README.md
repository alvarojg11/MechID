# MechID

Mechanism-based interpretation of antibiograms built with Streamlit.

## Project files

- `app_gnr.py`: main MechID app.
- `app.py`: legacy/simple app variant.
- `requirements.txt`: Python dependencies.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app_gnr.py
```

Default local URL: `http://localhost:8501`

## Data file note

`microbiology_cultures_cohort.csv` is excluded from git in `.gitignore` because it is very large and exceeds standard GitHub file size limits.

If you need to version this file, use Git LFS:

```bash
git lfs install
git lfs track "microbiology_cultures_cohort.csv"
git add .gitattributes microbiology_cultures_cohort.csv
```

## First GitHub push

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```
