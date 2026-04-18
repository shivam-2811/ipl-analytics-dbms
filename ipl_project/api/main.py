from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import psycopg2

app = FastAPI()

# --- PYDANTIC MODELS ---
# This ensures anyone sending data to your API uses this exact structure
class Match(BaseModel):
    id: int
    season: str
    city: Optional[str] = None
    team1: str
    team2: str
    winner: Optional[str] = None

# --- DATABASE CONNECTION ---
def get_db_connection():
    return psycopg2.connect(host="db", dbname="ipl_db", user="postgres", password="password")

# --- CRUD OPERATIONS ---

# READ (Existing endpoint)
@app.get("/")
def home():
    return {"message": "API is successfully connected!"}

# READ (Existing endpoint)
@app.get("/api/matches/count")
def get_match_count():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM matches;")
    count = cursor.fetchone()[0]
    conn.close()
    return {"total_matches_played": count}

# CREATE (New endpoint)
@app.post("/api/matches/")
def create_match(match: Match):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO matches (id, season, city, team1, team2, winner) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (match.id, match.season, match.city, match.team1, match.team2, match.winner)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()
    return {"message": "Match created successfully!", "match_id": match.id}

# UPDATE (New endpoint)
@app.put("/api/matches/{match_id}")
def update_match_winner(match_id: int, winner: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE matches SET winner = %s WHERE id = %s", (winner, match_id))
    conn.commit()
    conn.close()
    return {"message": f"Match {match_id} updated with new winner: {winner}"}

# DELETE (New endpoint)
@app.delete("/api/matches/{match_id}")
def delete_match(match_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM matches WHERE id = %s", (match_id,))
    conn.commit()
    conn.close()
    return {"message": f"Match {match_id} deleted permanently."}

from fastapi import FastAPI, Query
import psycopg2

app = FastAPI(title="IPL Analytics API")

# Database connection helper
def get_db_connection():
    # Make sure these match your docker-compose settings!
    return psycopg2.connect(host="db", dbname="ipl_db", user="postgres", password="password")

# ==========================================
# API Authentication 
# ==========================================
from fastapi import FastAPI, Query, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
import psycopg2

app = FastAPI(title="IPL Analytics API")

# ==========================================
# AUTHENTICATION SETUP
# ==========================================
# This is our secret password for the API
API_KEY = "my_super_secret_ipl_key_2024"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

# The "Security Guard" function
def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Access Denied: Invalid API Key")

# Database connection helper
def get_db_connection():
    return psycopg2.connect(host="db", dbname="ipl_db", user="postgres", password="password")

# ==========================================
# ENDPOINT 1: TEAM WINS (For Tab 1)
# ==========================================
@app.get("/api/team-wins")
@app.get("/api/team-wins")
def get_team_wins(
    team: str = Query("All Teams", description="Filter by team name"),
    api_key: str = Depends(get_api_key)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Handle the dynamic filter from the UI
    where_match = "WHERE winner IS NOT NULL AND winner != 'NA'"
    params = ()
    if team != "All Teams":
        where_match += " AND (team1 = %s OR team2 = %s)"
        params = (team, team)
        
    # 2. The exact same SQL from your Streamlit app
    q_wins = f"""
    SELECT 
        CASE 
            WHEN winner = 'Delhi Daredevils' THEN 'Delhi Capitals'
            WHEN winner = 'Kings XI Punjab' THEN 'Punjab Kings'
            WHEN winner = 'Rising Pune Supergiants' THEN 'Rising Pune Supergiant'
            WHEN winner = 'Royal Challengers Bangalore' THEN 'Royal Challengers Bengaluru'
            ELSE winner 
        END AS team, 
        COUNT(*) AS total_wins
    FROM matches
    {where_match}
    GROUP BY team
    ORDER BY total_wins DESC;
    """
    
    # 3. Execute and format as JSON
    cursor.execute(q_wins, params)
    
    # This magic line converts SQL rows into a list of dictionaries (JSON)
    columns = [desc[0] for desc in cursor.description]
    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    conn.close()
    return {"data": data}

# ==========================================
# ENDPOINT 2: WIN TYPES (Chasing vs Defending)
# ==========================================
@app.get("/api/win-type")
def get_win_type(
    team: str = Query("All Teams", description="Filter by team name"),
    api_key: str = Depends(get_api_key)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    where_win_type = "WHERE result IN ('runs', 'wickets')"
    params = ()
    if team != "All Teams":
        where_win_type += " AND (team1 = %s OR team2 = %s)"
        params = (team, team)

    q_win_type = f"""
    SELECT result AS win_type, COUNT(*) AS frequency
    FROM matches
    {where_win_type}
    GROUP BY result;
    """
    
    cursor.execute(q_win_type, params)
    columns = [desc[0] for desc in cursor.description]
    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    conn.close()
    return {"data": data}

# ==========================================
# ENDPOINT 3: TOP BATTERS (Highest Strike Rate)
# ==========================================
@app.get("/api/top-batters")
def get_top_batters(
    team: str = Query("All Teams", description="Filter by team name"),
    api_key: str = Depends(get_api_key)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    where_bat = ""
    params = ()
    min_balls = 500
    if team != "All Teams":
        where_bat = "WHERE batting_team = %s"
        params = (team,)
        min_balls = 100 

    q_sr = f"""
    SELECT batter, ROUND((SUM(batsman_runs)::numeric / COUNT(*)) * 100, 2) AS strike_rate
    FROM deliveries {where_bat}
    GROUP BY batter HAVING COUNT(*) >= {min_balls}
    ORDER BY strike_rate DESC;
    """
    
    cursor.execute(q_sr, params)
    columns = [desc[0] for desc in cursor.description]
    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    conn.close()
    return {"data": data}
# ==========================================
# ENDPOINT 4: BATTER RADAR PROFILE
# ==========================================
@app.get("/api/batter-profile")
def get_batter_profile(player: str = Query(..., description="Player name"), api_key: str = Depends(get_api_key)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calculates the 4 key dimensions of a T20 Batter
    q_radar = """
    SELECT 
        ROUND((SUM(batsman_runs)::numeric / COUNT(*)) * 100, 2) AS strike_rate,
        ROUND((SUM(CASE WHEN batsman_runs IN (4, 6) THEN 1 ELSE 0 END)::numeric / COUNT(*)) * 100, 2) AS boundary_pct,
        ROUND((SUM(CASE WHEN batsman_runs = 0 THEN 1 ELSE 0 END)::numeric / COUNT(*)) * 100, 2) AS dot_pct,
        ROUND((SUM(CASE WHEN batsman_runs IN (1, 2, 3) THEN 1 ELSE 0 END)::numeric / COUNT(*)) * 100, 2) AS rotation_pct
    FROM deliveries
    WHERE batter = %s;
    """
    cursor.execute(q_radar, (player,))
    columns = [desc[0] for desc in cursor.description]
    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return {"data": data}

# ==========================================
# ENDPOINT 5: RUN DISTRIBUTION (DONUT CHART)
# ==========================================
@app.get("/api/run-distribution")
def get_run_distribution(player: str = Query(..., description="Player name"), api_key: str = Depends(get_api_key)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    q_donut = """
    SELECT 
        CASE 
            WHEN batsman_runs IN (1, 2, 3) THEN 'Singles & Twos'
            WHEN batsman_runs = 4 THEN 'Fours'
            WHEN batsman_runs = 6 THEN 'Sixes'
        END as run_type,
        SUM(batsman_runs) as total_runs
    FROM deliveries
    WHERE batter = %s AND batsman_runs IN (1, 2, 3, 4, 6)
    GROUP BY run_type;
    """
    cursor.execute(q_donut, (player,))
    columns = [desc[0] for desc in cursor.description]
    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return {"data": data}
# ==========================================
# API 6: WICKETS BY MATCH PHASE (From Tab 3)
# ==========================================
@app.get("/api/wickets-phase")
def get_wickets_phase(team: str = Query("All Teams"), api_key: str = Depends(get_api_key)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Base query
    query = """
    SELECT CASE 
        WHEN over < 6 THEN '1. Powerplay (0-5)' 
        WHEN over < 15 THEN '2. Middle (6-14)' 
        ELSE '3. Death (15-19)' END AS match_phase,
    SUM(is_wicket) AS total_wickets 
    FROM deliveries 
    WHERE is_wicket = 1 AND dismissal_kind NOT IN ('run out', 'retired hurt', 'NA')
    """
    params = ()
    
    # If a specific team is selected, add the filter to the SQL!
    if team != "All Teams":
        query += " AND bowling_team = %s"
        params = (team,)
        
    query += " GROUP BY match_phase ORDER BY match_phase;"
    
    cursor.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    
    return {"data": data}