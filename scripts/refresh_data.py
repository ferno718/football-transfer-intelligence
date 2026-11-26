from pathlib import Path
import pandas as pd, requests, hashlib
from datetime import datetime
from utils.db import init_db, replace_players, connect

DEFAULT_URL='https://raw.githubusercontent.com/lkjmo123/EDA-NEW/main/players_data_light-2025_2026.csv'
DATA_DIR=Path(__file__).resolve().parents[1]/'data'
RAW=DATA_DIR/'players_source_2025_26.csv'

def fetch(url=DEFAULT_URL):
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    r=requests.get(url,timeout=60,headers={'User-Agent':'FootballTransferIntelligence/1.0'})
    r.raise_for_status(); RAW.write_bytes(r.content); return RAW

def normalize(path):
    df=pd.read_csv(path)
    def col(name,default=None): return df[name] if name in df.columns else default
    out=pd.DataFrame()
    out['player']=col('Player','Unknown').astype(str)
    out['nation']=col('Nation','').fillna('').astype(str)
    out['position']=col('Pos','').fillna('').astype(str)
    out['club']=col('Squad','').fillna('').astype(str)
    out['league']=col('Comp','').fillna('').astype(str).str.replace(r'^[a-z]{2,4}\s','',regex=True)
    out['season']='2025/26'
    out['age']=pd.to_numeric(col('Age',0),errors='coerce')
    out['minutes']=pd.to_numeric(col('Min',0),errors='coerce').fillna(0)
    out['goals']=pd.to_numeric(col('Gls',0),errors='coerce').fillna(0)
    out['assists']=pd.to_numeric(col('Ast',0),errors='coerce').fillna(0)
    out['shots']=pd.to_numeric(col('Sh',0),errors='coerce').fillna(0)
    out['shots_on_target']=pd.to_numeric(col('SoT',0),errors='coerce').fillna(0)
    out['tackles_won']=pd.to_numeric(col('TklW',0),errors='coerce').fillna(0)
    out['interceptions']=pd.to_numeric(col('Int',0),errors='coerce').fillna(0)
    out['player_id']=(out['player'].str.lower().str.replace(r'[^a-z0-9]+','-',regex=True).str.strip('-')+'-'+out['club'].str.lower().str.replace(r'[^a-z0-9]+','-',regex=True).str.strip('-')).map(lambda x: hashlib.sha1(x.encode()).hexdigest()[:16])
    rows=[]
    for r in out.itertuples(index=False): rows.append((r.player_id,r.player,r.nation,r.position,r.club,r.league,r.season,r.age,r.minutes,r.goals,r.assists,r.shots,r.shots_on_target,r.tackles_won,r.interceptions,'FBref-derived Kaggle dataset mirror',DEFAULT_URL))
    return rows,out

def main(url=DEFAULT_URL):
    init_db(); path=fetch(url); rows,out=normalize(path); replace_players(rows)
    con=connect()
    con.execute(
        '''INSERT OR REPLACE INTO source_registry
           (source_id,name,url,coverage,licence_note,last_refresh)
           VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)''',
        ('fbref_2526','FBref-derived Football Players Stats 2025/26',url,
         'Big Five European leagues',
         'Educational/non-commercial use; verify upstream terms before redistribution')
    )
    con.commit(); con.close()
    print(f'SUCCESS: Loaded {len(out):,} player rows into SQLite: {path}')

if __name__=='__main__': main()
