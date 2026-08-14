# Adobe University Hackathon 2026 Leaderboard Results & Query Tool

An automated, resilient Python pipeline to fetch, structure, query, and search all 78,043 participants across 892 pages from the Adobe University Hackathon 2026 leaderboard on Unstop — with both a **CLI Search Utility** and a **Web Search Application**.

---

## 🚀 Web Application (FastAPI + Modern UI)

### Running Locally:
```bash
python app.py
```
Open **`http://127.0.0.1:8000`** in your browser.

Features:
- **Instant Search**: Type any name, teammate's name, team name, or university.
- **Filter Pills**: Filter by Participant Name, Team Name, College, or Profile Handle.
- **Quick Tags**: Instant 1-click filters for popular colleges (IITs, NITs, IIITs, BITS, VIT, SRM, DTU).
- **Team Cards**: Displays full member list, roles (Leader/Member), college names, avatars, and direct links to Unstop profiles and leaderboard pages.
- **Live Stats Bar**: Real-time participant, team, and university counters.

---

## 🌐 1-Click Deployment Guide

### Deploying on Vercel (Recommended):
1. Push this repository to GitHub:
   ```bash
   git add .
   git commit -m "Add web search application and deployment config"
   git push
   ```
2. Go to [vercel.com](https://vercel.com) and click **"Add New" > "Project"**.
3. Import your GitHub repository.
4. Click **"Deploy"** — Vercel will automatically read `vercel.json` and deploy both the serverless API and the frontend instantly.

### Deploying on Render:
1. Push your repository to GitHub.
2. Go to [render.com](https://render.com) and create a **"New Web Service"**.
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `uvicorn api.index:app --host 0.0.0.0 --port $PORT`
5. Click **"Deploy"**.

---

## Output Files Generated

| File | Format | Description |
|---|---|---|
| `adobe_hackathon_results.db` | **SQLite Database** | Full relational database with `teams` and `players` tables, indexed on names, colleges, team names, profile URLs, and ranks for sub-millisecond querying. |
| `adobe_hackathon_results.json` | **JSON Document** | Complete structured document with metadata, teams, and nested player information. |
| `players.csv` | **CSV Table** | Flattened table containing every participant with their team, college/organisation, role (Leader/Member), rank, score, and profile link. Ideal for Excel & Google Sheets. |
| `teams.csv` | **CSV Table** | Aggregated table containing every team with participant lists, ranks, scores, and evaluation status. |
| `.cache/` | **Cache Directory** | Stores raw JSON page responses locally so repeated runs or interrupted fetches resume instantly. |

---

## 1. Fetching All Results

To run the scraper and generate all structured documents:

```bash
python fetch_results.py
```

### Options & Flags:
- `--workers <int>`: Concurrency level (default: `20` worker threads).
- `--start-page <int>`: Specify starting page (default: `1`).
- `--end-page <int>`: Specify ending page (default: all `892` pages).
- `--no-cache`: Force re-downloading pages bypassing the local `.cache/` folder.

Example:
```bash
python fetch_results.py --workers 25
```

---

## 2. Searching & Querying Results

You can search and query your results easily using `query.py`.

### Interactive Mode:
Simply run:
```bash
python query.py
```
This opens an interactive search menu where you can type your name, teammate's name, college name, or team name.

### Command-Line Search:

#### Search by Player Name:
```bash
python query.py --name "Aarav"
```

#### Search by Team Name:
```bash
python query.py --team "Cyber"
```

#### Search by College / University:
```bash
python query.py --college "IIT Bombay"
```

#### Search by Profile Username:
```bash
python query.py --profile "rishayad23586"
```

#### Custom SQL Query:
```bash
python query.py --sql "SELECT name, organisation, team_name, page FROM players WHERE name LIKE '%Sharma%' LIMIT 10"
```

#### Exporting Search Results:
Add `--export results.csv` or `--export results.json` to any query command:
```bash
python query.py --college "Bits Pilani" --export bits_pilani_results.csv
```

---

## 3. Database Schema

### `teams` Table
- `id`: Primary Key
- `page`: Page number in Unstop pagination
- `team_name`: Name of the team
- `rank`: Rank (if published)
- `score`: Score (if published)
- `time`: Submission time
- `finish_time`: Completion timestamp
- `evaluated`: Evaluation mode (e.g. `manual`)
- `report_file`: Report attachment URL
- `player_count`: Number of players in the team

### `players` Table
- `id`: Primary Key
- `team_id`: Foreign Key linking to `teams(id)`
- `team_name`: Name of the team
- `name`: Participant's full name (Indexed)
- `organisation`: Participant's college / university (Indexed)
- `player_type`: `1` (Leader) or `2` (Member)
- `player_type_str`: `"Leader"` or `"Member"`
- `profile_url`: Unstop profile URL path (Indexed)
- `avatar`: Profile avatar image URL
- `rank`: Team rank
- `score`: Team score
- `page`: Page number on leaderboard
