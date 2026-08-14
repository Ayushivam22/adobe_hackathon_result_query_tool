#!/usr/bin/env python3
"""
Adobe University Hackathon 2026 - Query and Search Tool
Fast search and query utility for the scraped hackathon leaderboard database.
"""

import os
import sys
import sqlite3
import argparse
import json
import csv

# Ensure safe UTF-8 output on Windows consoles with fallback
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adobe_hackathon_results.db")


def print_table(headers, rows):
    """Prints tabular data neatly with aligned column widths."""
    if not rows:
        print("No matching records found.")
        return

    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            str_val = str(val if val is not None else "")
            if len(str_val) > col_widths[i]:
                col_widths[i] = min(len(str_val), 50)  # cap wide columns

    # Format header
    header_str = " | ".join(f"{str(h):<{col_widths[i]}}" for i, h in enumerate(headers))
    separator = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    
    print("\n" + header_str)
    print(separator)
    
    for row in rows:
        row_str = " | ".join(
            f"{str(val if val is not None else '')[:col_widths[i]]:<{col_widths[i]}}" 
            for i, val in enumerate(row)
        )
        print(row_str)
    print(f"\nTotal matches: {len(rows)}\n")


def search_players(conn, name=None, team=None, college=None, profile=None, rank=None, limit=100):
    """Queries players table with given filters."""
    cur = conn.cursor()
    query = """
        SELECT 
            p.page,
            p.name,
            p.organisation,
            p.player_type_str as role,
            p.team_name,
            p.rank,
            p.score,
            p.profile_url
        FROM players p
        WHERE 1=1
    """
    params = []

    if name:
        query += " AND p.name LIKE ?"
        params.append(f"%{name}%")
    if team:
        query += " AND p.team_name LIKE ?"
        params.append(f"%{team}%")
    if college:
        query += " AND p.organisation LIKE ?"
        params.append(f"%{college}%")
    if profile:
        query += " AND p.profile_url LIKE ?"
        params.append(f"%{profile}%")
    if rank is not None:
        query += " AND p.rank = ?"
        params.append(rank)

    query += " ORDER BY p.page ASC, p.id ASC LIMIT ?"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    headers = ["Page", "Name", "College / Organisation", "Role", "Team Name", "Rank", "Score", "Profile URL"]
    return headers, rows


def search_teams(conn, team_name=None, college=None, limit=100):
    """Queries teams table with given filters."""
    cur = conn.cursor()
    query = """
        SELECT 
            t.page,
            t.team_name,
            t.player_count,
            GROUP_CONCAT(p.name || ' (' || p.player_type_str || ')', ', ') as members,
            t.rank,
            t.score,
            t.evaluated
        FROM teams t
        LEFT JOIN players p ON t.id = p.team_id
        WHERE 1=1
    """
    params = []

    if team_name:
        query += " AND t.team_name LIKE ?"
        params.append(f"%{team_name}%")
    if college:
        query += " AND p.organisation LIKE ?"
        params.append(f"%{college}%")

    query += " GROUP BY t.id ORDER BY t.page ASC LIMIT ?"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    headers = ["Page", "Team Name", "Members Count", "Members", "Rank", "Score", "Evaluated"]
    return headers, rows


def execute_custom_sql(conn, sql_query):
    """Executes a custom SQL query and displays results."""
    cur = conn.cursor()
    cur.execute(sql_query)
    rows = cur.fetchall()
    headers = [desc[0] for desc in cur.description] if cur.description else ["Result"]
    return headers, rows


def export_results(headers, rows, output_path):
    """Exports query results to CSV or JSON."""
    if output_path.endswith(".json"):
        dict_rows = [dict(zip(headers, row)) for row in rows]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dict_rows, f, indent=2, ensure_ascii=False)
    else:
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
    print(f"Exported {len(rows)} records to {output_path}")


def interactive_mode(conn):
    """Interactive CLI search prompt."""
    print("=" * 60)
    print("  Adobe Hackathon 2026 Results - Interactive Search")
    print("=" * 60)
    print("Options:")
    print("  1. Search by Your Name (or teammate's name)")
    print("  2. Search by Team Name")
    print("  3. Search by College / University")
    print("  4. Custom SQL Query")
    print("  5. View Leaderboard Summary Statistics")
    print("  Type 'q' or 'exit' to quit.\n")

    while True:
        try:
            choice = input("Enter choice (1-5, or search query): ").strip()
            if not choice or choice.lower() in ("q", "exit", "quit"):
                print("Goodbye!")
                break

            if choice == "1" or not choice.isdigit():
                name_query = choice if not choice.isdigit() else input("Enter name to search: ").strip()
                if name_query:
                    headers, rows = search_players(conn, name=name_query, limit=100)
                    print_table(headers, rows)

            elif choice == "2":
                team_query = input("Enter team name to search: ").strip()
                if team_query:
                    headers, rows = search_teams(conn, team_name=team_query, limit=100)
                    print_table(headers, rows)

            elif choice == "3":
                college_query = input("Enter college/university name: ").strip()
                if college_query:
                    headers, rows = search_players(conn, college=college_query, limit=100)
                    print_table(headers, rows)

            elif choice == "4":
                sql = input("Enter SQL query: ").strip()
                if sql:
                    try:
                        headers, rows = execute_custom_sql(conn, sql)
                        print_table(headers, rows)
                    except Exception as e:
                        print(f"SQL Error: {e}")

            elif choice == "5":
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM teams")
                teams_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM players")
                players_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(DISTINCT organisation) FROM players WHERE organisation != ''")
                colleges_count = cur.fetchone()[0]
                
                print("\n--- Leaderboard Summary ---")
                print(f"Total Teams:              {teams_count:,}")
                print(f"Total Participants:       {players_count:,}")
                print(f"Unique Universities/Orgs: {colleges_count:,}")
                print("---------------------------\n")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break


def main():
    parser = argparse.ArgumentParser(description="Search and query Adobe Hackathon results.")
    parser.add_argument("-n", "--name", type=str, help="Search by player name")
    parser.add_argument("-t", "--team", type=str, help="Search by team name")
    parser.add_argument("-c", "--college", "--org", type=str, help="Search by college/organisation")
    parser.add_argument("-p", "--profile", type=str, help="Search by profile URL or handle")
    parser.add_argument("-r", "--rank", type=int, help="Filter by rank")
    parser.add_argument("-s", "--sql", type=str, help="Execute arbitrary SQL query")
    parser.add_argument("-l", "--limit", type=int, default=100, help="Maximum results to return (default: 100)")
    parser.add_argument("-e", "--export", type=str, help="Export results to CSV or JSON file path")
    parser.add_argument("-i", "--interactive", action="store_true", help="Launch interactive search mode")

    args = parser.parse_args()

    if not os.path.exists(DB_FILE):
        print(f"Error: Database file '{DB_FILE}' not found.")
        print("Please run `python fetch_results.py` first to download and build the database.")
        sys.exit(1)

    conn = sqlite3.connect(DB_FILE)

    # Check if any search filter is given
    has_filter = any([args.name, args.team, args.college, args.profile, args.rank is not None, args.sql])

    if args.interactive or not has_filter:
        interactive_mode(conn)
    elif args.sql:
        try:
            headers, rows = execute_custom_sql(conn, args.sql)
            print_table(headers, rows)
            if args.export:
                export_results(headers, rows, args.export)
        except Exception as e:
            print(f"SQL Error: {e}")
    else:
        headers, rows = search_players(
            conn,
            name=args.name,
            team=args.team,
            college=args.college,
            profile=args.profile,
            rank=args.rank,
            limit=args.limit
        )
        print_table(headers, rows)
        if args.export and rows:
            export_results(headers, rows, args.export)

    conn.close()


if __name__ == "__main__":
    main()
