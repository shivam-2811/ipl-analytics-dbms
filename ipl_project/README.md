# IPL Analytics DBMS

A full-stack **Database Management System** built on **thousands of Indian Premier League (IPL) matches and ball-by-ball records**, featuring a relational SQLite database, a FastAPI REST backend, and an interactive Streamlit dashboard with search, CRUD operations, player/team comparison, and squad-building tools.

---

## Table of Contents

- [Project Overview](#-project-overview)
- [Tech Stack](#-tech-stack)
- [File Structure](#-file-structure)
- [Database Schema](#-database-schema)
- [Setup & Installation](#-setup--installation)
- [Running the Project](#-running-the-project)

---

## Project Overview

This project demonstrates a complete DBMS pipeline using real-world sports and financial data:

- **Massive IPL Dataset:** Thousands of matches, hundreds of thousands of deliveries, and detailed player auction records loaded into a relational SQLite database.
- **3 normalized tables** linked by primary/foreign keys (`match_id` and `player_name`).
- **FastAPI backend** exposing 18+ REST endpoints for full CRUD, search, and advanced cricket analytics.
- **Streamlit dashboard** with interactive pages including a search engine, ROI calculator, and head-to-head comparison tool.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Database | SQLite 3 |
| Backend API | FastAPI + Pydantic |
| Frontend | Streamlit |
| Data Processing | pandas |
| Language | Python 3.10+ |

---

## File Structure

text
ipl-analytics-dbms/
├── main.py                ← FastAPI routes & Streamlit Dashboard logic
├── init.sql               ← SQL schema definition (DDL)
├── Dockerfile             ← Container environment configuration
├── requirements.txt       ← Python dependencies
├── README.md              ← Project documentation
├── data/
│   ├── matches.csv        ← Match metadata
│   ├── deliveries.csv     ← Ball-by-ball records
│   └── auction.csv        ← Player financial data
└── db/
    └── ipl_analytics.db   ← SQLite database (auto-generated)


---

## Setup & Installation

### 1. Clone the repository
bash
git clone https://github.com/YOUR_USERNAME/ipl-analytics-dbms.git
cd ipl-analytics-dbms


### 2. Install dependencies
powershell
pip install -r requirements.txt


### 3. Generate the database
Ensure your 3 CSV files are inside a `data/` folder, then run this quick script to populate your SQLite database:

powershell
python -c "
import pandas as pd, sqlite3, os
os.makedirs('db', exist_ok=True)
conn = sqlite3.connect('db/ipl_analytics.db')

for file, table in [('data/matches.csv','matches'), ('data/deliveries.csv','deliveries'), ('data/auction.csv','auction')]:
    try:
        df = pd.read_csv(file)
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        if table == 'matches' and 'is_deleted' not in df.columns:
            df['is_deleted'] = 0
        df.to_sql(table, conn, if_exists='replace', index=False)
        print(f'Loaded {table} successfully')
    except Exception as e:
        print(f'Error loading {file}: {e}')

conn.close()
print('Database generation complete!')
"

---

## Running the Project

Open **two separate terminals** inside your project folder.

### Terminal 1 — Start the FastAPI backend
powershell
set API_KEY=ipl-dev-key
python -m uvicorn main:app --reload --port 8000


### Terminal 2 — Start the Streamlit dashboard
powershell
set API_KEY=ipl-dev-key
set API_BASE_URL=http://localhost:8000
python -m streamlit run main.py


### Access the app
| What | URL |
|------|-----|
| Dashboard | http://localhost:8501 |
| API Docs (Swagger) | http://localhost:8000/docs |
