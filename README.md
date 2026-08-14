# Adobe University Hackathon 2026 Leaderboard Results & Query Tool

This project provides an automated, resilient Python pipeline to fetch, parse, structure, and query all 26,760+ participants across 892 pages from the Adobe University Hackathon 2026 leaderboard API on Unstop.

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
