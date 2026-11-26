import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / 'data' / 'transfer_intelligence.db'


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = connect()
    con.executescript('''
    CREATE TABLE IF NOT EXISTS players (
        player_id TEXT PRIMARY KEY,
        player TEXT NOT NULL,
        nation TEXT,
        position TEXT,
        club TEXT,
        league TEXT,
        season TEXT,
        age REAL,
        minutes REAL,
        goals REAL,
        assists REAL,
        shots REAL,
        shots_on_target REAL,
        tackles_won REAL,
        interceptions REAL,
        source TEXT,
        source_url TEXT,
        loaded_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS analyses (
        analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id TEXT,
        analysis_type TEXT NOT NULL DEFAULT 'Player profile',
        fit_score REAL,
        impact_score REAL,
        value_proxy REAL,
        drivers TEXT,
        result_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(player_id) REFERENCES players(player_id)
    );

    CREATE TABLE IF NOT EXISTS shortlist (
        player_id TEXT PRIMARY KEY,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP,
        notes TEXT DEFAULT '',
        status TEXT DEFAULT 'Active',
        priority TEXT DEFAULT 'Medium',
        target_role TEXT DEFAULT '',
        FOREIGN KEY(player_id) REFERENCES players(player_id)
    );

    CREATE TABLE IF NOT EXISTS source_registry (
        source_id TEXT PRIMARY KEY,
        name TEXT,
        url TEXT,
        coverage TEXT,
        licence_note TEXT,
        last_refresh TEXT
    );

    CREATE TABLE IF NOT EXISTS user_inputs (
        input_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_name TEXT NOT NULL,
        position TEXT,
        current_club TEXT,
        target_club TEXT,
        age REAL,
        minutes REAL,
        goals REAL,
        assists REAL,
        transfer_fee REAL,
        wages REAL,
        contract_years REAL,
        target_role TEXT,
        scouting_notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS comparison_history (
        comparison_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_ids TEXT NOT NULL,
        player_names TEXT NOT NULL,
        metrics_used TEXT,
        comparison_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_players_player ON players(player);
    CREATE INDEX IF NOT EXISTS idx_players_position ON players(position);
    CREATE INDEX IF NOT EXISTS idx_players_league ON players(league);
    CREATE INDEX IF NOT EXISTS idx_analysis_player ON analyses(player_id);
    CREATE INDEX IF NOT EXISTS idx_user_inputs_created ON user_inputs(created_at);
    CREATE INDEX IF NOT EXISTS idx_comparison_created ON comparison_history(created_at);
    ''')

    # Lightweight migration for databases created by the previous project version.
    existing = {row['name'] for row in con.execute('PRAGMA table_info(analyses)').fetchall()}
    for name, definition in {
        'analysis_type': "TEXT NOT NULL DEFAULT 'Player profile'",
        'result_json': 'TEXT',
    }.items():
        if name not in existing:
            con.execute(f'ALTER TABLE analyses ADD COLUMN {name} {definition}')

    existing = {row['name'] for row in con.execute('PRAGMA table_info(shortlist)').fetchall()}
    for name, definition in {
        'status': "TEXT DEFAULT 'Active'",
        'priority': "TEXT DEFAULT 'Medium'",
        'target_role': "TEXT DEFAULT ''",
    }.items():
        if name not in existing:
            con.execute(f'ALTER TABLE shortlist ADD COLUMN {name} {definition}')

    con.commit()
    con.close()


def replace_players(rows):
    con = connect()
    con.execute('DELETE FROM players')
    con.executemany('''INSERT OR REPLACE INTO players
      (player_id,player,nation,position,club,league,season,age,minutes,goals,assists,shots,shots_on_target,tackles_won,interceptions,source,source_url)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', rows)
    con.commit()
    con.close()


def load_players():
    import pandas as pd
    con = connect()
    df = pd.read_sql_query('SELECT * FROM players', con)
    con.close()
    return df


def add_analysis(player_id, fit, impact, value_proxy, drivers, analysis_type='Player profile', result=None):
    con = connect()
    con.execute('''INSERT INTO analyses
        (player_id, analysis_type, fit_score, impact_score, value_proxy, drivers, result_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (player_id, analysis_type, fit, impact, value_proxy, drivers,
         json.dumps(result, default=str) if result is not None else None))
    con.commit()
    con.close()


def get_analysis_history(limit=250):
    import pandas as pd
    con = connect()
    df = pd.read_sql_query('''
        SELECT a.analysis_id, a.created_at, a.analysis_type, a.player_id,
               p.player, p.position, p.club, a.fit_score, a.impact_score,
               a.value_proxy, a.drivers, a.result_json
        FROM analyses a
        LEFT JOIN players p ON p.player_id = a.player_id
        ORDER BY a.created_at DESC, a.analysis_id DESC
        LIMIT ?
    ''', con, params=(limit,))
    con.close()
    return df


def add_shortlist(player_id, notes='', status='Active', priority='Medium', target_role=''):
    con = connect()
    con.execute('''INSERT OR REPLACE INTO shortlist
        (player_id, notes, status, priority, target_role)
        VALUES (?, ?, ?, ?, ?)''',
        (player_id, notes, status, priority, target_role))
    con.commit()
    con.close()


def update_shortlist(player_id, notes='', status='Active', priority='Medium', target_role=''):
    add_shortlist(player_id, notes, status, priority, target_role)


def remove_shortlist(player_id):
    con = connect()
    con.execute('DELETE FROM shortlist WHERE player_id=?', (player_id,))
    con.commit()
    con.close()


def get_shortlist():
    import pandas as pd
    con = connect()
    df = pd.read_sql_query('''
        SELECT s.player_id, p.player, p.position, p.club, p.league, p.age,
               p.minutes, p.goals, p.assists, s.added_at, s.notes,
               s.status, s.priority, s.target_role
        FROM shortlist s
        LEFT JOIN players p ON p.player_id=s.player_id
        ORDER BY CASE s.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
                 s.added_at DESC
    ''', con)
    con.close()
    return df


def add_user_input(data):
    con = connect()
    cur = con.execute('''INSERT INTO user_inputs
        (player_name, position, current_club, target_club, age, minutes,
         goals, assists, transfer_fee, wages, contract_years, target_role, scouting_notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (data.get('player_name'), data.get('position'), data.get('current_club'),
         data.get('target_club'), data.get('age'), data.get('minutes'),
         data.get('goals'), data.get('assists'), data.get('transfer_fee'),
         data.get('wages'), data.get('contract_years'), data.get('target_role'),
         data.get('scouting_notes')))
    con.commit()
    new_id = cur.lastrowid
    con.close()
    return new_id


def get_user_inputs(limit=500):
    import pandas as pd
    con = connect()
    df = pd.read_sql_query('''SELECT * FROM user_inputs
                              ORDER BY created_at DESC, input_id DESC LIMIT ?''', con, params=(limit,))
    con.close()
    return df


def delete_user_input(input_id):
    con = connect()
    con.execute('DELETE FROM user_inputs WHERE input_id=?', (input_id,))
    con.commit()
    con.close()


def add_comparison_history(player_ids, player_names, metrics_used, comparison_data):
    con = connect()
    con.execute('''INSERT INTO comparison_history
        (player_ids, player_names, metrics_used, comparison_json)
        VALUES (?, ?, ?, ?)''',
        (json.dumps(player_ids), json.dumps(player_names), json.dumps(metrics_used),
         json.dumps(comparison_data, default=str)))
    con.commit()
    con.close()


def get_comparison_history(limit=250):
    import pandas as pd
    con = connect()
    df = pd.read_sql_query('''SELECT comparison_id, created_at, player_ids,
        player_names, metrics_used, comparison_json
        FROM comparison_history ORDER BY created_at DESC, comparison_id DESC LIMIT ?''',
        con, params=(limit,))
    con.close()
    return df


def delete_comparison_history(comparison_id):
    con = connect()
    con.execute('DELETE FROM comparison_history WHERE comparison_id=?', (comparison_id,))
    con.commit()
    con.close()


def database_summary():
    con = connect()
    tables = ['players', 'analyses', 'shortlist', 'source_registry', 'user_inputs', 'comparison_history']
    counts = {}
    for table in tables:
        counts[table] = con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    con.close()
    return counts
