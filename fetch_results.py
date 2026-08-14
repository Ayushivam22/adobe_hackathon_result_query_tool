#!/usr/bin/env python3
"""
Adobe University Hackathon 2026 - Leaderboard Results Scraper
Fetches all paginated results from Unstop API, parses teams and players,
and exports into SQLite DB, JSON, and CSV documents for querying.
"""

import os
import sys
import json
import time
import csv
import sqlite3
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import argparse

# Ensure safe UTF-8 output on Windows consoles with fallback
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

API_BASE_URL = "https://unstop.com/api/public/live-leaderboard/460737/assessmentnewround"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adobe_hackathon_results.db")
JSON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adobe_hackathon_results.json")
PLAYERS_CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "players.csv")
TEAMS_CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "teams.csv")


def fetch_page_data(page_num, retries=5, backoff=1.0, use_cache=True):
    """
    Fetches JSON data for a specific page number.
    Caches response to disk to support seamless resumption.
    """
    cache_path = os.path.join(CACHE_DIR, f"page_{page_num}.json")
    
    if use_cache and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f), True
        except Exception:
            pass  # Fall back to re-fetching if cached file is corrupted

    url = f"{API_BASE_URL}?page={page_num}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Referer": "https://unstop.com/",
        }
    )

    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                if response.status == 200:
                    raw_content = response.read().decode("utf-8")
                    data = json.loads(raw_content)
                    
                    # Cache to disk
                    if use_cache:
                        os.makedirs(CACHE_DIR, exist_ok=True)
                        with open(cache_path, "w", encoding="utf-8") as f:
                            f.write(raw_content)
                            
                    return data, False
                else:
                    time.sleep(backoff * attempt)
        except Exception as e:
            if attempt == retries:
                raise RuntimeError(f"Failed to fetch page {page_num} after {retries} attempts: {e}")
            time.sleep(backoff * attempt)
            
    return None, False


def init_database(db_path):
    """Initializes SQLite database schema and indices."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page INTEGER,
            team_name TEXT,
            rank INTEGER,
            score REAL,
            time TEXT,
            finish_time TEXT,
            evaluated TEXT,
            report_file TEXT,
            player_count INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER,
            team_name TEXT,
            name TEXT,
            organisation TEXT,
            player_type INTEGER,
            player_type_str TEXT,
            profile_url TEXT,
            avatar TEXT,
            rank INTEGER,
            score REAL,
            page INTEGER,
            FOREIGN KEY (team_id) REFERENCES teams (id)
        )
    """)

    # Create search indices for fast queries
    cur.execute("CREATE INDEX IF NOT EXISTS idx_players_name ON players(name COLLATE NOCASE)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_players_org ON players(organisation COLLATE NOCASE)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_players_team ON players(team_name COLLATE NOCASE)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_players_profile ON players(profile_url)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_teams_name ON teams(team_name COLLATE NOCASE)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_teams_rank ON teams(rank)")

    conn.commit()
    conn.close()


def parse_and_store_results(all_page_data, db_path, json_path, players_csv_path, teams_csv_path):
    """
    Parses collected page data into normalized structures and saves to
    SQLite DB, structured JSON, and CSV files.
    """
    print("\nProcessing and structuring data...")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Clear existing records to avoid duplicates if re-running
    cur.execute("DELETE FROM players")
    cur.execute("DELETE FROM teams")
    conn.commit()

    teams_records = []
    players_records = []
    full_structured_data = []

    total_teams = 0
    total_players = 0

    for page_num in sorted(all_page_data.keys()):
        page_obj = all_page_data[page_num]
        items = page_obj.get("data", {}).get("data", [])
        
        for item in items:
            team_info = item.get("team") or {}
            team_name = team_info.get("team_name", "").strip()
            players = team_info.get("players", [])
            rank = item.get("rank")
            score = item.get("score")
            time_val = item.get("time")
            finish_time = item.get("finish_time")
            evaluated = item.get("evaluated")
            report_file = item.get("report_file")
            
            cur.execute("""
                INSERT INTO teams (page, team_name, rank, score, time, finish_time, evaluated, report_file, player_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (page_num, team_name, rank, score, str(time_val) if time_val else None, 
                  str(finish_time) if finish_time else None, evaluated, report_file, len(players)))
            
            team_id = cur.lastrowid
            total_teams += 1

            team_players_structured = []

            for p in players:
                p_name = (p.get("name") or "").strip()
                p_org = (p.get("organisation") or "").strip()
                p_type = p.get("player_type")
                p_type_str = "Leader" if p_type == 1 else "Member"
                p_profile = p.get("profile_url") or ""
                p_avatar = p.get("avatar") or ""

                cur.execute("""
                    INSERT INTO players (team_id, team_name, name, organisation, player_type, player_type_str, profile_url, avatar, rank, score, page)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (team_id, team_name, p_name, p_org, p_type, p_type_str, p_profile, p_avatar, rank, score, page_num))
                
                total_players += 1

                player_dict = {
                    "name": p_name,
                    "organisation": p_org,
                    "role": p_type_str,
                    "player_type": p_type,
                    "profile_url": p_profile,
                    "avatar": p_avatar
                }
                team_players_structured.append(player_dict)

                players_records.append({
                    "page": page_num,
                    "team_name": team_name,
                    "name": p_name,
                    "organisation": p_org,
                    "role": p_type_str,
                    "rank": rank if rank is not None else "",
                    "score": score if score is not None else "",
                    "profile_url": f"https://unstop.com{p_profile}" if p_profile.startswith('/') else p_profile,
                    "evaluated": evaluated or "",
                })

            teams_records.append({
                "page": page_num,
                "team_name": team_name,
                "player_count": len(players),
                "members": " | ".join([f"{p['name']} ({p['organisation']})" for p in team_players_structured]),
                "rank": rank if rank is not None else "",
                "score": score if score is not None else "",
                "time": time_val or "",
                "finish_time": finish_time or "",
                "evaluated": evaluated or "",
            })

            full_structured_data.append({
                "team_id": team_id,
                "page": page_num,
                "team_name": team_name,
                "rank": rank,
                "score": score,
                "time": time_val,
                "finish_time": finish_time,
                "evaluated": evaluated,
                "report_file": report_file,
                "players": team_players_structured
            })

    conn.commit()
    conn.close()

    print(f"Saved to SQLite database: {db_path}")
    print(f"  - Total Teams:   {total_teams:,}")
    print(f"  - Total Players: {total_players:,}")

    # Write to JSON file
    print(f"Writing structured JSON: {json_path}...")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "source": API_BASE_URL,
                "total_teams": total_teams,
                "total_players": total_players,
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "teams": full_structured_data
        }, f, indent=2, ensure_ascii=False)

    # Write players CSV
    print(f"Writing players CSV: {players_csv_path}...")
    if players_records:
        keys = ["page", "name", "organisation", "role", "team_name", "rank", "score", "profile_url", "evaluated"]
        with open(players_csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(players_records)

    # Write teams CSV
    print(f"Writing teams CSV: {teams_csv_path}...")
    if teams_records:
        keys = ["page", "team_name", "player_count", "members", "rank", "score", "time", "finish_time", "evaluated"]
        with open(teams_csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(teams_records)

    print("\nAll files successfully generated!")


def scrape_all(start_page=1, end_page=None, max_workers=20, use_cache=True):
    """Scrapes all leaderboard pages concurrently with progress reporting."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    init_database(DB_FILE)

    print("=" * 60)
    print("  Adobe University Hackathon 2026 Leaderboard Scraper")
    print("=" * 60)
    print(f"Target API Base: {API_BASE_URL}")
    print(f"Fetching initial metadata from Page 1...")

    # Fetch page 1 to detect total pages
    first_page_data, _ = fetch_page_data(1, use_cache=use_cache)
    if not first_page_data or "data" not in first_page_data:
        print("Error: Could not fetch initial page data.")
        sys.exit(1)

    api_total = first_page_data.get("data", {}).get("total", 0)
    api_last_page = first_page_data.get("data", {}).get("last_page", 1)
    
    total_pages = end_page if end_page is not None else api_last_page
    start_page = max(1, start_page)
    
    print(f"Found {api_total:,} total entries across {api_last_page} pages.")
    print(f"Scraping pages {start_page} through {total_pages} using {max_workers} worker threads...")

    pages_to_fetch = list(range(start_page, total_pages + 1))
    all_page_data = {}
    
    lock = Lock()
    completed_count = 0
    cached_hits = 0
    network_fetches = 0
    start_time = time.time()
    
    def worker(p):
        data, is_cached = fetch_page_data(p, use_cache=use_cache)
        return p, data, is_cached

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_page = {executor.submit(worker, p): p for p in pages_to_fetch}
        
        for future in as_completed(future_to_page):
            page_num = future_to_page[future]
            try:
                p, data, is_cached = future.result()
                if data:
                    all_page_data[p] = data
                with lock:
                    completed_count += 1
                    if is_cached:
                        cached_hits += 1
                    else:
                        network_fetches += 1

                    elapsed = time.time() - start_time
                    percent = (completed_count / len(pages_to_fetch)) * 100
                    speed = completed_count / elapsed if elapsed > 0 else 0
                    remaining = len(pages_to_fetch) - completed_count
                    eta = (remaining / speed) if speed > 0 else 0
                    
                    sys.stdout.write(
                        f"\rProgress: [{completed_count}/{len(pages_to_fetch)}] "
                        f"{percent:5.1f}% | "
                        f"Speed: {speed:4.1f} p/s | "
                        f"ETA: {int(eta)}s | "
                        f"Cached: {cached_hits} | Network: {network_fetches}"
                    )
                    sys.stdout.flush()
            except Exception as e:
                print(f"\n[Warning] Error on page {page_num}: {e}")

    print("\n\nAll pages successfully fetched!")
    
    parse_and_store_results(
        all_page_data, 
        DB_FILE, 
        JSON_FILE, 
        PLAYERS_CSV_FILE, 
        TEAMS_CSV_FILE
    )


def main():
    parser = argparse.ArgumentParser(description="Scrape and structure Adobe Hackathon leaderboard results.")
    parser.add_argument("--start-page", type=int, default=1, help="Start page number (default: 1)")
    parser.add_argument("--end-page", type=int, default=None, help="End page number (default: all pages)")
    parser.add_argument("--workers", type=int, default=20, help="Number of concurrent worker threads (default: 20)")
    parser.add_argument("--no-cache", action="store_true", help="Bypass local cache and refetch all pages from network")
    
    args = parser.parse_args()
    scrape_all(
        start_page=args.start_page, 
        end_page=args.end_page, 
        max_workers=args.workers, 
        use_cache=not args.no_cache
    )


if __name__ == "__main__":
    main()
