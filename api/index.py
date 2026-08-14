import os
import time
import sqlite3
import csv
import io
import json
import re
from typing import Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response

# Locate database dynamically across local and serverless environments
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

def find_db_path():
    candidate_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "adobe_hackathon_results.db"),
        os.path.join(BASE_DIR, "adobe_hackathon_results.db"),
        os.path.join(os.getcwd(), "adobe_hackathon_results.db"),
        os.path.join(os.getcwd(), "api", "adobe_hackathon_results.db"),
        "/var/task/api/adobe_hackathon_results.db",
        "/var/task/adobe_hackathon_results.db"
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            return path
    return candidate_paths[0]

app = FastAPI(
    title="Adobe University Hackathon 2026 Results API",
    description="Search, query, and analyze 78,000+ hackathon participants and teams",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    """Returns a read-only SQLite database connection."""
    db_file = find_db_path()
    if not os.path.exists(db_file):
        raise HTTPException(status_code=500, detail=f"Database file not found. Checked: {db_file}")
    try:
        conn = sqlite3.connect(f"file:{os.path.abspath(db_file)}?mode=ro", uri=True)
    except Exception:
        conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/stats")
@app.get("/stats")
def get_stats():
    """Returns overall summary statistics and top universities."""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM teams")
        total_teams = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM players")
        total_players = cur.fetchone()[0]
        
        cur.execute("SELECT MAX(page) FROM teams")
        total_pages = cur.fetchone()[0] or 892
        
        cur.execute("SELECT COUNT(DISTINCT organisation) FROM players WHERE organisation != ''")
        total_colleges = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM players WHERE player_type = 1")
        total_leaders = cur.fetchone()[0]
        
        # Top 15 participating universities
        cur.execute("""
            SELECT organisation, COUNT(*) as count 
            FROM players 
            WHERE organisation != '' 
            GROUP BY organisation 
            ORDER BY count DESC 
            LIMIT 15
        """)
        top_colleges = [{"name": row["organisation"], "count": row["count"]} for row in cur.fetchall()]
        
        conn.close()
        return {
            "total_teams": total_teams,
            "total_players": total_players,
            "total_pages": total_pages,
            "total_colleges": total_colleges,
            "total_leaders": total_leaders,
            "top_colleges": top_colleges
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/search")
@app.get("/search")
def search_results(
    q: Optional[str] = None,
    filter_by: str = "all",
    name: Optional[str] = None,
    team: Optional[str] = None,
    college: Optional[str] = None,
    profile: Optional[str] = None,
    page: int = 1,
    limit: int = 24,
    view: str = "cards"
):
    """Searches teams and participants with multi-field filtering and pagination."""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        offset = (page - 1) * limit
        conditions = []
        params = []

        # Check multi-field filters first
        if name and isinstance(name, str) and name.strip():
            conditions.append("p.name LIKE ?")
            params.append(f"%{name.strip()}%")
        if team and isinstance(team, str) and team.strip():
            conditions.append("t.team_name LIKE ?")
            params.append(f"%{team.strip()}%")
        if college and isinstance(college, str) and college.strip():
            conditions.append("p.organisation LIKE ?")
            params.append(f"%{college.strip()}%")
        if profile and isinstance(profile, str) and profile.strip():
            conditions.append("p.profile_url LIKE ?")
            params.append(f"%{profile.strip()}%")

        # If general q query is provided
        if q and isinstance(q, str) and q.strip():
            query_str = q.strip()
            search_param = f"%{query_str}%"
            if filter_by == "name":
                conditions.append("p.name LIKE ?")
                params.append(search_param)
            elif filter_by == "team":
                conditions.append("t.team_name LIKE ?")
                params.append(search_param)
            elif filter_by == "college":
                conditions.append("p.organisation LIKE ?")
                params.append(search_param)
            elif filter_by == "profile":
                conditions.append("p.profile_url LIKE ?")
                params.append(search_param)
            else: # "all"
                conditions.append("(p.name LIKE ? OR t.team_name LIKE ? OR p.organisation LIKE ? OR p.profile_url LIKE ?)")
                params.extend([search_param, search_param, search_param, search_param])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        if view == "flat":
            # Flat player-level list for table view
            count_sql = f"""
                SELECT COUNT(*)
                FROM players p
                JOIN teams t ON p.team_id = t.id
                WHERE {where_clause}
            """
            cur.execute(count_sql, params)
            total_count = cur.fetchone()[0]

            data_sql = f"""
                SELECT 
                    p.page,
                    p.name,
                    p.organisation,
                    p.player_type_str as role,
                    t.team_name,
                    p.rank,
                    p.score,
                    p.profile_url,
                    t.evaluated
                FROM players p
                JOIN teams t ON p.team_id = t.id
                WHERE {where_clause}
                ORDER BY p.page ASC, p.id ASC
                LIMIT ? OFFSET ?
            """
            cur.execute(data_sql, params + [limit, offset])
            flat_rows = [dict(row) for row in cur.fetchall()]

            conn.close()
            return {
                "view": "flat",
                "page": page,
                "limit": limit,
                "total_matches": total_count,
                "total_pages": (total_count + limit - 1) // limit if limit > 0 else 1,
                "results": flat_rows
            }

        # Cards View (Grouped by team)
        count_sql = f"""
            SELECT COUNT(DISTINCT t.id)
            FROM teams t
            JOIN players p ON t.id = p.team_id
            WHERE {where_clause}
        """
        cur.execute(count_sql, params)
        total_count = cur.fetchone()[0]

        teams_sql = f"""
            SELECT DISTINCT t.id, t.page, t.team_name, t.rank, t.score, t.time, t.finish_time, t.evaluated, t.player_count
            FROM teams t
            JOIN players p ON t.id = p.team_id
            WHERE {where_clause}
            ORDER BY t.page ASC, t.id ASC
            LIMIT ? OFFSET ?
        """
        cur.execute(teams_sql, params + [limit, offset])
        teams_rows = cur.fetchall()

        team_ids = [row["id"] for row in teams_rows]
        results = []

        if team_ids:
            placeholders = ",".join("?" * len(team_ids))
            cur.execute(f"""
                SELECT team_id, name, organisation, player_type, player_type_str, profile_url, avatar, rank, score, page
                FROM players
                WHERE team_id IN ({placeholders})
                ORDER BY player_type ASC, id ASC
            """, team_ids)

            players_by_team = {}
            for p in cur.fetchall():
                t_id = p["team_id"]
                if t_id not in players_by_team:
                    players_by_team[t_id] = []
                players_by_team[t_id].append({
                    "name": p["name"],
                    "organisation": p["organisation"],
                    "player_type": p["player_type"],
                    "role": p["player_type_str"],
                    "profile_url": f"https://unstop.com{p['profile_url']}" if p["profile_url"].startswith("/") else p["profile_url"],
                    "avatar": p["avatar"],
                    "rank": p["rank"],
                    "score": p["score"]
                })

            for t in teams_rows:
                results.append({
                    "id": t["id"],
                    "page": t["page"],
                    "team_name": t["team_name"],
                    "rank": t["rank"],
                    "score": t["score"],
                    "time": t["time"],
                    "finish_time": t["finish_time"],
                    "evaluated": t["evaluated"],
                    "player_count": t["player_count"],
                    "unstop_url": f"https://unstop.com/api/public/live-leaderboard/460737/assessmentnewround?page={t['page']}",
                    "players": players_by_team.get(t["id"], [])
                })

        conn.close()
        return {
            "view": "cards",
            "page": page,
            "limit": limit,
            "total_matches": total_count,
            "total_pages": (total_count + limit - 1) // limit if limit > 0 else 1,
            "results": results
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/sql")
@app.post("/sql")
def execute_sql(body: dict = Body(...)):
    """Executes arbitrary read-only SQL queries and returns column headers, rows, and execution time."""
    query = (body.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Read-only security validation: Only allow SELECT or WITH statements
    clean_query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)  # remove comments
    clean_query = clean_query.strip().upper()

    if not (clean_query.startswith("SELECT") or clean_query.startswith("WITH") or clean_query.startswith("PRAGMA")):
        raise HTTPException(
            status_code=400, 
            detail="Only read-only SELECT or WITH statements are allowed."
        )

    # Disallow destructive keywords
    disallowed = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "ATTACH", "DETACH", "CREATE", "VACUUM"]
    for word in disallowed:
        if re.search(rf"\b{word}\b", clean_query):
            raise HTTPException(status_code=400, detail=f"Operation '{word}' is not permitted.")

    try:
        conn = get_db()
        cur = conn.cursor()
        
        start_time = time.time()
        cur.execute(query)
        rows_raw = cur.fetchmany(500)  # Limit to 500 rows for browser performance
        duration_ms = round((time.time() - start_time) * 1000, 2)

        headers = [desc[0] for desc in cur.description] if cur.description else []
        rows = [[val for val in row] for row in rows_raw]
        
        conn.close()
        return {
            "headers": headers,
            "rows": rows,
            "total_rows": len(rows),
            "execution_time_ms": duration_ms,
            "is_truncated": len(rows_raw) == 500
        }
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.get("/api/export")
@app.get("/export")
def export_data(
    format: str = "csv",
    q: Optional[str] = None,
    filter_by: str = "all",
    name: Optional[str] = None,
    team: Optional[str] = None,
    college: Optional[str] = None,
    sql_query: Optional[str] = None
):
    """Exports filtered search results or custom SQL query results as downloadable CSV or JSON."""
    try:
        conn = get_db()
        cur = conn.cursor()

        if sql_query and sql_query.strip():
            cur.execute(sql_query)
            headers = [desc[0] for desc in cur.description] if cur.description else []
            rows = [list(r) for r in cur.fetchall()]
        else:
            conditions = []
            params = []
            if name and name.strip():
                conditions.append("p.name LIKE ?")
                params.append(f"%{name.strip()}%")
            if team and team.strip():
                conditions.append("t.team_name LIKE ?")
                params.append(f"%{team.strip()}%")
            if college and college.strip():
                conditions.append("p.organisation LIKE ?")
                params.append(f"%{college.strip()}%")
            if q and q.strip():
                p_val = f"%{q.strip()}%"
                if filter_by == "name":
                    conditions.append("p.name LIKE ?")
                    params.append(p_val)
                elif filter_by == "team":
                    conditions.append("t.team_name LIKE ?")
                    params.append(p_val)
                elif filter_by == "college":
                    conditions.append("p.organisation LIKE ?")
                    params.append(p_val)
                else:
                    conditions.append("(p.name LIKE ? OR t.team_name LIKE ? OR p.organisation LIKE ? OR p.profile_url LIKE ?)")
                    params.extend([p_val, p_val, p_val, p_val])

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cur.execute(f"""
                SELECT 
                    p.page,
                    p.name,
                    p.organisation,
                    p.player_type_str as role,
                    t.team_name,
                    p.rank,
                    p.score,
                    p.profile_url,
                    t.evaluated
                FROM players p
                JOIN teams t ON p.team_id = t.id
                WHERE {where_clause}
                ORDER BY p.page ASC, p.id ASC
                LIMIT 5000
            """, params)

            headers = ["Page", "Name", "College / Organisation", "Role", "Team Name", "Rank", "Score", "Profile URL", "Evaluated"]
            rows = [list(r) for r in cur.fetchall()]

        conn.close()

        if format.lower() == "json":
            json_data = [dict(zip(headers, row)) for row in rows]
            content = json.dumps(json_data, indent=2, ensure_ascii=False)
            return Response(
                content=content,
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=adobe_results_export.json"}
            )
        else:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)
            writer.writerows(rows)
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=adobe_results_export.csv"}
            )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# Mount static assets
if os.path.exists(PUBLIC_DIR):
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(PUBLIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Adobe Hackathon Results API is running."}

@app.get("/style.css")
def serve_css_root():
    css_file = os.path.join(PUBLIC_DIR, "style.css")
    if os.path.exists(css_file):
        return FileResponse(css_file, media_type="text/css")
    raise HTTPException(status_code=404, detail="style.css not found")

@app.get("/app.js")
def serve_js_root():
    js_file = os.path.join(PUBLIC_DIR, "app.js")
    if os.path.exists(js_file):
        return FileResponse(js_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")
