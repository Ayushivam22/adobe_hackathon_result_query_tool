import os
import sqlite3
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Locate database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "adobe_hackathon_results.db")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

app = FastAPI(
    title="Adobe University Hackathon 2026 Results API",
    description="Search and query 78,000+ hackathon participants and teams",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/stats")
def get_stats():
    """Returns overall summary statistics."""
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
        
        # Top 5 participating universities
        cur.execute("""
            SELECT organisation, COUNT(*) as count 
            FROM players 
            WHERE organisation != '' 
            GROUP BY organisation 
            ORDER BY count DESC 
            LIMIT 6
        """)
        top_colleges = [{"name": row["organisation"], "count": row["count"]} for row in cur.fetchall()]
        
        conn.close()
        return {
            "total_teams": total_teams,
            "total_players": total_players,
            "total_pages": total_pages,
            "total_colleges": total_colleges,
            "top_colleges": top_colleges
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/search")
def search_results(
    q: Optional[str] = Query(None, description="Search query string"),
    filter_by: str = Query("all", description="Field to search: all, name, team, college, profile"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    limit: int = Query(24, ge=1, le=100, description="Items per page")
):
    """Searches teams and participants with pagination and detailed member lists."""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        offset = (page - 1) * limit
        query_str = (q or "").strip()
        
        # If no query, return top teams by page
        if not query_str:
            cur.execute("""
                SELECT t.id, t.page, t.team_name, t.rank, t.score, t.time, t.finish_time, t.evaluated, t.player_count
                FROM teams t
                ORDER BY t.page ASC, t.id ASC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            teams_rows = cur.fetchall()
            
            cur.execute("SELECT COUNT(*) FROM teams")
            total_count = cur.fetchone()[0]
        else:
            search_param = f"%{query_str}%"
            
            if filter_by == "name":
                where_clause = "p.name LIKE ?"
                params = [search_param]
            elif filter_by == "team":
                where_clause = "t.team_name LIKE ?"
                params = [search_param]
            elif filter_by == "college":
                where_clause = "p.organisation LIKE ?"
                params = [search_param]
            elif filter_by == "profile":
                where_clause = "p.profile_url LIKE ?"
                params = [search_param]
            else: # "all"
                where_clause = "(p.name LIKE ? OR t.team_name LIKE ? OR p.organisation LIKE ? OR p.profile_url LIKE ?)"
                params = [search_param, search_param, search_param, search_param]
            
            # Count matching teams
            count_sql = f"""
                SELECT COUNT(DISTINCT t.id)
                FROM teams t
                JOIN players p ON t.id = p.team_id
                WHERE {where_clause}
            """
            cur.execute(count_sql, params)
            total_count = cur.fetchone()[0]
            
            # Fetch matching teams
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
        
        # Fetch all players for the retrieved teams
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
            "query": query_str,
            "filter_by": filter_by,
            "page": page,
            "limit": limit,
            "total_matches": total_count,
            "total_pages": (total_count + limit - 1) // limit if limit > 0 else 1,
            "results": results
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# Mount static assets if public directory exists
if os.path.exists(PUBLIC_DIR):
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(PUBLIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Adobe Hackathon Results API is running. Visit /docs for API schema."}
