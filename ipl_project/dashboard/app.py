import streamlit as st
import pandas as pd
import psycopg2
import requests
from streamlit_autorefresh import st_autorefresh
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Ultimate IPL Analytics", page_icon="🏏", layout="wide")
st.title("🏏 Ultimate IPL Cricket Analytics Dashboard")
st.markdown("Analyzing **1,000+ matches** and **260,000+ deliveries** to drive franchise and coaching decisions.")
st.divider()

# --- DATABASE CONNECTION ---
@st.cache_data
def load_data(query, params=None):
    try:
        conn = psycopg2.connect(host="db", dbname="ipl_db", user="postgres", password="password")
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database Error: {e}")
        return pd.DataFrame()

# --- API SECURITY HEADERS ---
API_HEADERS = {
    "X-API-Key": "my_super_secret_ipl_key_2024"
}

# ==========================================
# GLOBAL SIDEBAR FILTERS
# ==========================================
# ==========================================
# GLOBAL SIDEBAR FILTERS
# ==========================================
st.sidebar.header("⚙️ Dashboard Filters")

# 1. Fetch all unique teams for the dropdown (With Rebrand Merging)
q_sidebar_teams = """
WITH RawTeams AS (
    SELECT DISTINCT team1 AS team FROM matches 
    UNION 
    SELECT DISTINCT team2 FROM matches
)
SELECT DISTINCT 
    CASE 
        WHEN team = 'Delhi Daredevils' THEN 'Delhi Capitals'
        WHEN team = 'Kings XI Punjab' THEN 'Punjab Kings'
        WHEN team = 'Rising Pune Supergiants' THEN 'Rising Pune Supergiant'
        WHEN team = 'Royal Challengers Bangalore' THEN 'Royal Challengers Bengaluru'
        ELSE team 
    END AS team
FROM RawTeams
WHERE team IS NOT NULL AND team != 'NA'
ORDER BY team;
"""
teams_df = load_data(q_sidebar_teams)
team_list = ["All Teams"] + teams_df['team'].dropna().tolist()

# 2. Fetch all unique players for the dropdown
players_df = load_data("SELECT DISTINCT batter AS player FROM deliveries UNION SELECT DISTINCT bowler FROM deliveries ORDER BY player;")
player_list = ["All Players"] + players_df['player'].dropna().tolist()

# 3. Create the interactive widgets
global_team = st.sidebar.selectbox("🏏 Filter by Team:", team_list)
global_player = st.sidebar.selectbox("🏃‍♂️ Filter by Player (For Scout/Analyst Views):", player_list)

st.sidebar.divider()
st.sidebar.info("💡 **Tip:** Select a Team to filter the bar charts across all tabs. Select a Player to unlock their deep-dive stats!")

# ==========================================
# AUTO-REFRESH LOGIC
# ==========================================
# Run the autorefresh about every 30 seconds (30000 milliseconds)
# limit=100 means it will stop refreshing after 100 times to save browser memory
refresh_count = st_autorefresh(interval=30000, limit=100, key="ipl_dashboard_refresh")

st.sidebar.caption(f"🔄 Last auto-refresh tick: {refresh_count}")

# --- CREATE TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏆 Team Performance", 
    "🏏 Batter Analysis", 
    "🎯 Bowler Analysis", 
    "🏟️ Venue Insights", 
    "🧠 Advanced Strategy"
])

# ==========================================
# TAB 1: TEAM PERFORMANCE & SCOUT VIEW
# ==========================================
with tab1:
    st.header("🏆 Team Performance")
    col1, col2 = st.columns(2)
    
    # Dynamic SQL Setup
    where_match = "WHERE winner IS NOT NULL AND winner != 'NA'"
    params_match = ()
    if global_team != "All Teams":
        where_match += " AND (team1 = %s OR team2 = %s)"
        params_match = (global_team, global_team)
    
    with col1:
        st.subheader("Most Successful Franchises")
        
        # NEW ARCHITECTURE: Call the FastAPI endpoint using 'requests'
        # We pass the 'global_team' sidebar variable securely into the URL
        # NOTE: "api" is the name of your FastAPI container in docker-compose. 
        # If running locally without docker, change "api" to "localhost".
        api_url = f"http://api:8000/api/team-wins?team={global_team}"
        
        try:
            # Fetch data from our custom API
            response = requests.get(api_url,headers=API_HEADERS)
            response_data = response.json()
            
            # Convert the JSON back into a Pandas DataFrame for the chart
            if response_data.get("data"):
                df_wins = pd.DataFrame(response_data["data"])
                st.bar_chart(df_wins, x="team", y="total_wins", color="#00008b")
                st.caption("🧠 **Decision:** Helps sponsors decide which franchise offers the most consistent brand visibility.")
            else:
                st.info("No data found for this selection.")
                
        except Exception as e:
            st.error(f"API Connection Error: {e}. Is your FastAPI server running?")

    with col2:
        st.subheader("Win Type: Chasing vs Defending")
        
        # Call the new API endpoint
        api_url_win = f"http://api:8000/api/win-type?team={global_team}"
        
        try:
            response = requests.get(api_url_win,headers=API_HEADERS)
            response_data = response.json()
            
            if response_data.get("data"):
                df_win_type = pd.DataFrame(response_data["data"])
                st.bar_chart(df_win_type, x="win_type", y="frequency", color="#ffaa00")
                st.caption("🧠 **Decision:** Tells pitch curators if the tournament is historically biased toward chasing or defending.")
            else:
                st.info("No data found for this selection.")
        except Exception as e:
            st.error(f"API Connection Error: {e}")

    # --- SCOUT VIEW ---
    st.divider()
    st.header("🕵️‍♂️ Scout View: Player Valuation & Impact")
    
    if global_player == "All Players":
        st.info("👈 Please select a specific player from the Sidebar to view their Scout Profile.")
    else:
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        
        q_sr = "SELECT ROUND((SUM(batsman_runs)::numeric / COUNT(*)) * 100, 2) FROM deliveries WHERE batter = %s;"
        sr_val = load_data(q_sr, (global_player,)).iloc[0,0]
        sr_display = f"{sr_val}" if pd.notna(sr_val) else "N/A"

        q_wkts = "SELECT COUNT(*) FROM deliveries WHERE bowler = %s AND is_wicket = 1 AND dismissal_kind NOT IN ('run out', 'retired hurt');"
        wkts_val = load_data(q_wkts, (global_player,)).iloc[0,0]
        
        q_price = "SELECT price FROM auction_data WHERE player_name = %s LIMIT 1;"
        price_df = load_data(q_price, (global_player,))
        price_display = f"₹ {price_df.iloc[0,0]:,}" if not price_df.empty else "Unsold/No Data"

        with kpi_col1:
            st.metric(label="💰 Auction Price", value=price_display)
        with kpi_col2:
            st.metric(label="🏏 Career Strike Rate", value=sr_display)
        with kpi_col3:
            st.metric(label="🎯 Total Wickets", value=wkts_val)
            
        st.divider()
        st.subheader("Scatter Plot: Auction Price vs. Performance Impact")
        q_scatter = """
        WITH PlayerStats AS (
            SELECT COALESCE(d1.batter, d2.bowler) AS player, COALESCE(SUM(d1.batsman_runs), 0) AS total_runs, COALESCE(SUM(CASE WHEN d2.is_wicket = 1 THEN 1 ELSE 0 END), 0) AS total_wickets
            FROM deliveries d1 FULL OUTER JOIN deliveries d2 ON d1.batter = d2.bowler AND d1.delivery_id = d2.delivery_id
            GROUP BY COALESCE(d1.batter, d2.bowler)
        )
        SELECT ps.player, a.price AS auction_price, (ps.total_runs + (ps.total_wickets * 20)) AS total_impact
        FROM PlayerStats ps JOIN auction_data a ON ps.player = a.player_name WHERE a.price > 0;
        """
        df_scatter = load_data(q_scatter)
        if not df_scatter.empty:
            st.scatter_chart(df_scatter, x="auction_price", y="total_impact", size=100, color="#ff4b4b")
            st.caption("🧠 **Scout Insight:** Look for dots in the **top-left corner** (High Impact, Low Price). These are your undervalued targets!")

# ==========================================
# TAB 2: BATTER ANALYSIS
# ==========================================
with tab2:
    st.header("🏏 Batter Analysis")
    col1, col2 = st.columns(2)
    
    # Dynamic thresholds for Tab 2
    where_bat = ""
    params_bat = ()
    min_balls = 500
    if global_team != "All Teams":
        where_bat = "WHERE batting_team = %s"
        params_bat = (global_team,)
        min_balls = 100 # Drop threshold so team players still show up!

    with col1:
        # Determine the dynamic threshold just for the title display
        min_balls_display = 500 if global_team == "All Teams" else 100
        st.subheader(f"Highest Strike Rates (Min {min_balls_display} balls)")
        
        # Call the new API endpoint
        api_url_batters = f"http://api:8000/api/top-batters?team={global_team}"
        
        try:
            response = requests.get(api_url_batters,headers=API_HEADERS)
            response_data = response.json()
            
            if response_data.get("data"):
                df_sr = pd.DataFrame(response_data["data"])
                st.bar_chart(df_sr, x="batter", y="strike_rate", color="#ff4b4b")
            else:
                st.info("No data found for this selection.")
        except Exception as e:
            st.error(f"API Connection Error: {e}")

    with col2:
        st.subheader("The Boundary Hitters (Most 6s)")
        q_sixes = f"""
        SELECT batter, SUM(CASE WHEN batsman_runs = 6 THEN 1 ELSE 0 END) as total_sixes
        FROM deliveries {where_bat}
        GROUP BY batter ORDER BY total_sixes DESC;
        """
        df_sixes = load_data(q_sixes, params_bat)
        if not df_sixes.empty: st.bar_chart(df_sixes, x="batter", y="total_sixes")

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Most Balls Faced (Volume Players)")
        q_balls = f"SELECT batter, COUNT(*) AS balls_faced FROM deliveries {where_bat} GROUP BY batter ORDER BY balls_faced DESC;"
        df_balls = load_data(q_balls, params_bat)
        if not df_balls.empty: st.bar_chart(df_balls, x="batter", y="balls_faced", color="#ffaa00")

    with col4:
        st.subheader("Precision Hitters (Most 4s)")
        q_fours = f"SELECT batter, SUM(CASE WHEN batsman_runs = 4 THEN 1 ELSE 0 END) AS total_fours FROM deliveries {where_bat} GROUP BY batter ORDER BY total_fours DESC;"
        df_fours = load_data(q_fours, params_bat)
        if not df_fours.empty: st.bar_chart(df_fours, x="batter", y="total_fours", color="#2ca02c")

    # --- ANALYST VIEW ---
    st.divider()
    st.header("📈 Performance Trends (The Analyst View)")

    if global_player == "All Players":
        st.info("👈 Please select a specific player from the Sidebar to view their Advanced Analyst Profile.")
    else:
        st.subheader(f"Advanced Scout Profile: {global_player}")
        
        # Create columns for our two new advanced charts
        adv_col1, adv_col2 = st.columns(2)
        
        with adv_col1:
            st.markdown("**Player DNA (Radar Chart)**")
            try:
                radar_res = requests.get(f"http://api:8000/api/batter-profile?player={global_player}", headers=API_HEADERS).json()
                if radar_res.get("data") and radar_res["data"][0]["strike_rate"] is not None:
                    stats = radar_res["data"][0]
                    
                    # Plotly Spider/Radar Chart
                    categories = ['Strike Rate', 'Boundary %', 'Strike Rotation %', 'Dot Ball %']
                    # We scale strike rate down slightly just so it fits the visual shape better alongside percentages
                    values = [float(stats['strike_rate'])/2, float(stats['boundary_pct']), float(stats['rotation_pct']), float(stats['dot_pct'])]
                    
                    fig_radar = go.Figure(data=go.Scatterpolar(
                      r=values,
                      theta=categories,
                      fill='toself',
                      line_color='#ff4b4b'
                    ))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=False)), showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
                    st.plotly_chart(fig_radar, use_container_width=True)
                    st.caption("🧠 **Insight:** The shape reveals the player's 'DNA'. A wider top means high aggression, a wider bottom means anchor/accumulator.")
            except Exception as e:
                st.error(f"Error loading Radar Chart: {e}")

        with adv_col2:
            st.markdown("**Run Distribution**")
            try:
                donut_res = requests.get(f"http://api:8000/api/run-distribution?player={global_player}", headers=API_HEADERS).json()
                if donut_res.get("data"):
                    df_donut = pd.DataFrame(donut_res["data"])
                    
                    # Plotly Donut Chart
                    fig_donut = px.pie(df_donut, values='total_runs', names='run_type', hole=0.5, 
                                       color='run_type', color_discrete_map={'Fours':'#2ca02c', 'Sixes':'#ffaa00', 'Singles & Twos':'#1f77b4'})
                    fig_donut.update_traces(textposition='inside', textinfo='percent+label')
                    fig_donut.update_layout(margin=dict(t=20, b=20, l=20, r=20), showlegend=False)
                    st.plotly_chart(fig_donut, use_container_width=True)
                    st.caption("🧠 **Insight:** Shows dependency on boundaries vs. running between the wickets.")
            except Exception as e:
                st.error(f"Error loading Donut Chart: {e}")
# ==========================================
# TAB 3: BOWLER ANALYSIS & ADMIN VIEW
# ==========================================
with tab3:
    st.header("🎯 Bowler Analysis")
    col1, col2 = st.columns(2)
    
    where_bowl = "WHERE 1=1"
    where_bowl_wicket = "WHERE is_wicket = 1 AND dismissal_kind NOT IN ('NA', 'retired hurt')"
    params_bowl = ()
    min_bowl_balls = 500
    min_wickets = 20
    
    if global_team != "All Teams":
        where_bowl += " AND bowling_team = %s"
        where_bowl_wicket += " AND bowling_team = %s"
        params_bowl = (global_team,)
        min_bowl_balls = 100
        min_wickets = 5

    with col1:
        st.subheader(f"Economy Rates (Min {min_bowl_balls} balls)")
        q_eco = f"""
        SELECT bowler, ROUND((SUM(total_runs)::numeric / (COUNT(*)::numeric / 6)), 2) AS economy_rate
        FROM deliveries {where_bowl}
        GROUP BY bowler HAVING COUNT(*) >= {min_bowl_balls}
        ORDER BY economy_rate ASC;
        """
        df_eco = load_data(q_eco, params_bowl)
        if not df_eco.empty:
            st.dataframe(df_eco, use_container_width=True)
            st.caption("🧠 **Decision:** Identifies restrictive bowlers for the crucial Powerplay phase.")

    with col2:
        st.subheader("Types of Dismissals")
        q_dismissals = f"""
        SELECT dismissal_kind, COUNT(*) AS total_dismissals
        FROM deliveries {where_bowl_wicket}
        GROUP BY dismissal_kind ORDER BY total_dismissals DESC;
        """
        df_dismissals = load_data(q_dismissals, params_bowl)
        if not df_dismissals.empty:
            st.bar_chart(df_dismissals, x="dismissal_kind", y="total_dismissals", color="#ff4b4b")

    col3, col4 = st.columns(2)

    with col3:
        st.subheader(f"Bowling Strike Rates (Min {min_wickets} wkts)")
        q_bowl_sr = f"""
        SELECT bowler, ROUND(COUNT(*)::numeric / NULLIF(SUM(CASE WHEN is_wicket = 1 AND dismissal_kind NOT IN ('run out', 'retired hurt', 'NA') THEN 1 ELSE 0 END), 0), 2) AS strike_rate
        FROM deliveries {where_bowl}
        GROUP BY bowler HAVING SUM(CASE WHEN is_wicket = 1 AND dismissal_kind NOT IN ('run out', 'retired hurt', 'NA') THEN 1 ELSE 0 END) >= {min_wickets}
        ORDER BY strike_rate ASC;
        """
        df_bowl_sr = load_data(q_bowl_sr, params_bowl)
        if not df_bowl_sr.empty:
            st.dataframe(df_bowl_sr, use_container_width=True)

    with col4:
        st.subheader("Balls Bowled (Workhorses)")
        q_balls_bowled = f"SELECT bowler, COUNT(*) AS total_balls FROM deliveries {where_bowl} GROUP BY bowler ORDER BY total_balls DESC;"
        df_balls_bowled = load_data(q_balls_bowled, params_bowl)
        if not df_balls_bowled.empty: st.bar_chart(df_balls_bowled, x="bowler", y="total_balls", color="#00807E")

    col5, col6 = st.columns(2)

    with col5:
        st.subheader("Wickets by Match Phase")
        try:
            # We pass the global_team variable directly into the API URL!
            api_url = f"http://api:8000/api/wickets-phase?team={global_team}"
            phase_res = requests.get(api_url, headers=API_HEADERS).json()
            
            if phase_res.get("data"):
                df_wickets_phase = pd.DataFrame(phase_res["data"])
                st.bar_chart(df_wickets_phase, x="match_phase", y="total_wickets", color="#00cc66")
            else:
                st.info("No data available for this phase.")
        except Exception as e:
            st.error(f"Error loading Wickets by Phase API: {e}")
            
    with col6:
        st.subheader("Pace vs. Spin Effectiveness")
        mock_data = pd.DataFrame({"Bowling Style": ["Fast/Pace", "Spin", "Medium Pace"], "Wickets": [4230, 3150, 1820]})
        st.bar_chart(mock_data, x="Bowling Style", y="Wickets", color="#ff8c00")
        st.caption("🧠 *Note: Simulated data.*")

    # --- ADMIN VIEW ---
    st.divider()
    st.header("🔒 Management & Inventory (Admin View)")
    
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.warning("You must log in to access the Admin portal.")
        admin_password = st.text_input("Enter Admin Password (hint: try 'admin123')", type="password")
        if st.button("Login"):
            if admin_password == "admin123":
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("Incorrect password.")
    else:
        st.success("Authenticated as Administrator.")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()

        # THE FIX: Bypass load_data completely and fetch live from Postgres!
        try:
            conn = psycopg2.connect(host="db", dbname="ipl_db", user="postgres", password="password")
            cur = conn.cursor()
            cur.execute("SELECT * FROM auction_data ORDER BY price DESC;")
            columns = [desc[0] for desc in cur.description]
            df_auction = pd.DataFrame(cur.fetchall(), columns=columns)
            conn.close()
        except Exception as e:
            st.error("Database connection failed.")
            df_auction = pd.DataFrame(columns=["player_name", "price", "team", "type"])

        # Display the live table
        st.dataframe(df_auction, use_container_width=True, height=200)

        crud_col1, crud_col2, crud_col3 = st.columns(3)
        with crud_col1:
            st.markdown("### ➕ Add Player")
            with st.form("create_player_form"):
                new_player = st.text_input("Player Name")
                new_price = st.number_input("Base/Auction Price", min_value=0, step=100000)
                if st.form_submit_button("Create Record") and new_player:
                    try:
                        conn = psycopg2.connect(host="db", dbname="ipl_db", user="postgres", password="password")
                        cur = conn.cursor()
                        cur.execute("INSERT INTO auction_data (player_name, price) VALUES (%s, %s)", (new_player, new_price))
                        conn.commit()
                        conn.close()
                        st.success(f"Added {new_player}!")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

        with crud_col2:
            st.markdown("### ✏️ Update Price")
            with st.form("update_player_form"):
                player_list_db = df_auction['player_name'].tolist() if not df_auction.empty else []
                update_player = st.selectbox("Select Player", player_list_db)
                update_price = st.number_input("New Price", min_value=0, step=100000)
                if st.form_submit_button("Update Status") and update_player:
                    try:
                        conn = psycopg2.connect(host="db", dbname="ipl_db", user="postgres", password="password")
                        cur = conn.cursor()
                        cur.execute("UPDATE auction_data SET price = %s WHERE player_name = %s", (update_price, update_player))
                        conn.commit()
                        conn.close()
                        st.success(f"Updated {update_player}!")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

        with crud_col3:
            st.markdown("### ❌ Remove Player")
            with st.form("delete_player_form"):
                del_player = st.selectbox("Select Player to Delete", player_list_db, key="del_select")
                if st.form_submit_button("Delete Record", type="primary") and del_player:
                    try:
                        conn = psycopg2.connect(host="db", dbname="ipl_db", user="postgres", password="password")
                        cur = conn.cursor()
                        cur.execute("DELETE FROM auction_data WHERE player_name = %s", (del_player,))
                        conn.commit()
                        conn.close()
                        st.warning(f"Deleted {del_player} permanently.")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

# ==========================================
# TAB 4: VENUE INSIGHTS
# ==========================================
with tab4:
    st.header("🏟️ Venue Insights")
    col1, col2 = st.columns(2)
    
    where_venue = ""
    where_venue_bat = "WHERE result IN ('runs', 'wickets')"
    params_venue = ()
    min_matches = 20
    if global_team != "All Teams":
        where_venue = "WHERE team1 = %s OR team2 = %s"
        where_venue_bat += " AND (team1 = %s OR team2 = %s)"
        params_venue = (global_team, global_team)
        min_matches = 5
        
    with col1:
        st.subheader("Toss Advantage (Win % after winning toss)")
        q_venue_toss = f"""
        SELECT venue, ROUND((SUM(CASE WHEN toss_winner = winner THEN 1 ELSE 0 END)::numeric / COUNT(*)) * 100, 2) AS toss_win_advantage_pct
        FROM matches {where_venue} GROUP BY venue HAVING COUNT(*) >= {min_matches} ORDER BY toss_win_advantage_pct DESC;
        """
        df_venue_toss = load_data(q_venue_toss, params_venue)
        if not df_venue_toss.empty: st.bar_chart(df_venue_toss, x="venue", y="toss_win_advantage_pct", color="#00ffff")

    with col2:
        st.subheader("Total Matches Played")
        q_matches = f"SELECT venue, COUNT(*) AS total_matches FROM matches {where_venue} GROUP BY venue ORDER BY total_matches DESC;"
        df_matches = load_data(q_matches, params_venue)
        if not df_matches.empty: st.dataframe(df_matches, use_container_width=True, height=350)

    st.divider()
    col3 = st.columns(1)[0]

    with col3:
        st.subheader("Win Strategy: Defending vs Chasing (%)")
        q_bat_chase = f"""
        SELECT venue,
               ROUND((SUM(CASE WHEN result = 'runs' THEN 1 ELSE 0 END)::numeric / COUNT(*)) * 100, 2) AS defend_win_pct,
               ROUND((SUM(CASE WHEN result = 'wickets' THEN 1 ELSE 0 END)::numeric / COUNT(*)) * 100, 2) AS chase_win_pct
        FROM matches {where_venue_bat} GROUP BY venue HAVING COUNT(*) >= {min_matches} ORDER BY venue ASC;
        """
        df_bat_chase = load_data(q_bat_chase, params_venue)
        if not df_bat_chase.empty: st.bar_chart(df_bat_chase.set_index("venue"))

# ==========================================
# TAB 5: ADVANCED STRATEGY
# ==========================================
with tab5:
    st.header("🧠 Advanced Strategy")
    col1, col2 = st.columns(2)
    
    where_death_bat = "WHERE over >= 15"
    where_death_bowl = "WHERE over >= 15 AND is_wicket = 1 AND dismissal_kind NOT IN ('run out', 'retired hurt', 'obstructing the field', 'NA')"
    where_nemesis = "WHERE is_wicket = 1 AND dismissal_kind NOT IN ('run out', 'retired hurt', 'obstructing the field')"
    params_team = ()
    min_death = 150
    min_nemesis = 5
    
    if global_team != "All Teams":
        where_death_bat += " AND batting_team = %s"
        where_death_bowl += " AND bowling_team = %s"
        where_nemesis += " AND (batting_team = %s OR bowling_team = %s)"
        params_team = (global_team,)
        min_death = 30
        min_nemesis = 2

    with col1:
        st.subheader(f"Death Over Specialists (Min {min_death} balls)")
        q_death = f"""
        SELECT batter, ROUND((SUM(batsman_runs)::numeric / COUNT(*)) * 100, 2) AS death_strike_rate
        FROM deliveries {where_death_bat} GROUP BY batter HAVING COUNT(*) >= {min_death} ORDER BY death_strike_rate DESC;
        """
        df_death = load_data(q_death, params_team)
        if not df_death.empty: st.bar_chart(df_death, x="batter", y="death_strike_rate", color="#ff4b4b")

    with col2:
        st.subheader(f"Nemesis Matchups (Min {min_nemesis} dismissals)")
        q_nemesis = f"""
        SELECT batter, bowler, COUNT(*) AS times_dismissed
        FROM deliveries {where_nemesis} GROUP BY batter, bowler HAVING COUNT(*) >= {min_nemesis} ORDER BY times_dismissed DESC;
        """
        # Note: nemesis needs the param twice because of the OR statement
        df_nemesis = load_data(q_nemesis, (global_team, global_team) if global_team != "All Teams" else ())
        if not df_nemesis.empty: st.dataframe(df_nemesis, use_container_width=True)

    st.divider()
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("Kings of the Death Overs (Most Wickets)")
        q_death_bowl = f"""
        SELECT bowler, COUNT(*) AS death_wickets
        FROM deliveries {where_death_bowl} GROUP BY bowler ORDER BY death_wickets DESC;
        """
        df_death_bowl = load_data(q_death_bowl, params_team)
        if not df_death_bowl.empty: st.bar_chart(df_death_bowl, x="bowler", y="death_wickets", color="#800080")