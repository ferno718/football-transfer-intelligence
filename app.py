import sys
import json
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import requests
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from utils.db import (
    DB_PATH, init_db, load_players, add_analysis, get_analysis_history,
    add_shortlist, update_shortlist, get_shortlist, remove_shortlist,
    add_user_input, get_user_inputs, delete_user_input,
    add_comparison_history, get_comparison_history, delete_comparison_history,
    database_summary,
)
from utils.engine import profile_scores, similarity, train_value_model
from scripts.refresh_data import fetch, normalize, replace_players, DEFAULT_URL

st.set_page_config(
    page_title='Football Transfer Intelligence',
    page_icon=None,
    layout='wide',
    initial_sidebar_state='expanded'
)
init_db()

st.markdown('''
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
html,body,[class*='css']{font-family:Manrope,sans-serif}
.stApp{background:#071018;color:#e8eef3}
.block-container{max-width:1500px;padding-top:1.8rem;padding-bottom:4rem}
.panel{background:#0d1822;border:1px solid #1d2b37;border-radius:16px;padding:18px}
.muted{color:#8ea1af}.metric{font-size:30px;font-weight:800}.accent{color:#b9e36a}
.tag{display:inline-block;border:1px solid #314452;border-radius:999px;padding:4px 10px;margin-right:6px;color:#b9e36a;font-size:12px}
.small-note{font-size:12px;color:#8ea1af}.section-title{font-size:18px;font-weight:800;margin:12px 0}
div[data-testid='stMetric']{background:#0d1822;border:1px solid #1d2b37;border-radius:14px;padding:10px 14px}
</style>
''', unsafe_allow_html=True)


def load():
    data = load_players()
    if data.empty:
        return data
    return profile_scores(data)


def player_image_url(name):
    try:
        r = requests.get(
            'https://en.wikipedia.org/api/rest_v1/page/summary/' + requests.utils.quote(name.replace(' ', '_')),
            timeout=4,
            headers={'User-Agent': 'FootballTransferIntelligence/1.0'}
        )
        if r.ok:
            return r.json().get('thumbnail', {}).get('source')
    except Exception:
        pass
    return None


def figure_layout(fig, height=500):
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=height,
        margin=dict(l=30, r=30, t=55, b=30)
    )
    return fig


df = load()

with st.sidebar:
    st.markdown('## FTI')
    st.caption('Football Transfer Intelligence')
    page = st.radio('Workspace', [
        'Market overview',
        'Player intelligence',
        'Compare & radar',
        'Scouting plot',
        'Recruitment shortlist',
        'User data entry',
        'Database history',
        'Data laboratory',
        'Sources & methodology'
    ])
    st.divider()
    st.markdown('### Data source manager')
    url = st.text_input('CSV URL', value=DEFAULT_URL)
    if st.button('Refresh player database', use_container_width=True):
        try:
            p = fetch(url)
            rows, _ = normalize(p)
            replace_players(rows)
            st.success(f'Loaded {len(rows):,} player records.')
            st.rerun()
        except Exception as e:
            st.error(f'Data refresh failed: {e}')
    if not df.empty:
        st.caption(f'{len(df):,} player-season rows currently indexed')
    summary = database_summary()
    st.divider()
    st.markdown('### SQLite status')
    st.caption(f"Players: {summary['players']:,} · Analyses: {summary['analyses']:,} · Comparisons: {summary['comparison_history']:,} · User inputs: {summary['user_inputs']:,}")

if df.empty:
    st.title('Football Transfer Intelligence')
    st.warning('The SQLite player table is empty. Use the Data Source Manager in the sidebar to load the dataset.')
    st.info('The database file is created automatically at data/transfer_intelligence.db. No manual database creation is required.')
    st.stop()


if page == 'Market overview':
    st.title('Transfer Market Intelligence')
    st.caption('Recruitment analytics for discovery, profiling, comparison, similarity search and shortlist construction.')

    a, b, c, d, e = st.columns(5)
    a.metric('Player rows', f'{len(df):,}')
    b.metric('Unique players', f'{df.player.nunique():,}')
    c.metric('Clubs', f'{df.club.nunique():,}')
    d.metric('Leagues', f'{df.league.nunique():,}')
    e.metric('Nations', f'{df.nation.nunique():,}')

    left, right = st.columns([1.15, .85])
    with left:
        pos = (df.assign(primary_position=df.position.fillna('Unknown').str.split(',').str[0])
               .groupby('primary_position').size().reset_index(name='players')
               .sort_values('players', ascending=False))
        st.plotly_chart(figure_layout(px.bar(pos, x='primary_position', y='players', title='Player population by primary position'), 430), use_container_width=True)
    with right:
        league = df.groupby('league').size().reset_index(name='players').sort_values('players', ascending=False).head(10)
        st.plotly_chart(figure_layout(px.bar(league, y='league', x='players', orientation='h', title='Largest league samples'), 430), use_container_width=True)

    st.markdown('### Recruitment board')
    board = df[df.minutes >= 900].sort_values('impact_adjusted', ascending=False).head(20)
    board = board[['market_rank','player','position','club','league','age','minutes','goals_p90','assists_p90','impact_adjusted']]
    st.dataframe(board, use_container_width=True, hide_index=True)

    st.markdown('### Analytical interpretation')
    st.write('The impact index is a transparent, role-weighted performance indicator. It is not a transfer-fee valuation and should be interpreted alongside minutes, role, league context and scouting evidence.')


elif page == 'Player intelligence':
    st.title('Player Intelligence')
    names = sorted(df.player.dropna().astype(str).unique())
    selected = st.selectbox('Search player', names, index=0)
    p = df[df.player == selected].sort_values('minutes', ascending=False).iloc[0]

    image = player_image_url(p.player)
    top = st.columns([.22, .78])
    with top[0]:
        if image:
            st.image(image, use_container_width=True)
        else:
            initials = ''.join(w[0] for w in str(p.player).split()[:2]).upper()
            st.markdown(f'<div class="panel" style="height:170px;display:flex;align-items:center;justify-content:center;font-size:44px;font-weight:800;color:#b9e36a">{initials}</div>', unsafe_allow_html=True)
    with top[1]:
        st.markdown(f'## {p.player}')
        st.markdown(f'<span class="tag">{p.position}</span><span class="tag">{p.club}</span><span class="tag">{p.league}</span>', unsafe_allow_html=True)
        st.write(f'Age {p.age:.0f} · {p.minutes:,.0f} minutes · {p.goals:.0f} goals · {p.assists:.0f} assists')
        st.caption(f"Database rank: {int(p.market_rank)} · Reliability: {p.reliability:.2f} · Source: {p.source}")

    cards = st.columns(6)
    labels = ['Impact index','Goals / 90','Assists / 90','Shots / 90','Tackles / 90','Interceptions / 90']
    vals = [p.impact_adjusted,p.goals_p90,p.assists_p90,p.shots_p90,p.tackles_p90,p.interceptions_p90]
    for col, label, val in zip(cards, labels, vals):
        col.metric(label, f'{val:.2f}')

    metrics = [('Goals / 90','goals_p90_pct'),('Assists / 90','assists_p90_pct'),('Shots / 90','shots_p90_pct'),('Tackles / 90','tackles_p90_pct'),('Interceptions / 90','interceptions_p90_pct')]
    radar = go.Figure(go.Scatterpolar(r=[p[c] for _, c in metrics], theta=[x for x, _ in metrics], fill='toself', name=p.player))
    radar.update_layout(template='plotly_dark', polar={'radialaxis': {'range': [0,100]}}, paper_bgcolor='rgba(0,0,0,0)', height=450)
    st.plotly_chart(radar, use_container_width=True)

    sim = similarity(df, p.player_id, ['goals_p90','assists_p90','shots_p90','tackles_p90','interceptions_p90','age'])
    st.markdown('### Similar profile discovery')
    st.dataframe(sim.head(10), use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button('Add to recruitment shortlist', use_container_width=True):
            add_shortlist(p.player_id)
            st.success('Player added to SQLite shortlist.')
    with c2:
        if st.button('Save analysis snapshot', use_container_width=True):
            drivers = f'Percentile profile; reliability={p.reliability:.2f}; rank={int(p.market_rank)}'
            result = {'player': p.player, 'impact_adjusted': float(p.impact_adjusted), 'percentiles': {c: float(p[c]) for _, c in metrics}}
            add_analysis(p.player_id, float(p.impact_adjusted), float(p.impact_adjusted), 0.0, drivers, 'Player profile', result)
            st.success('Analysis snapshot saved to SQLite.')
    with c3:
        st.download_button('Export player profile', p.to_json().encode(), 'player_profile.json', 'application/json', use_container_width=True)


elif page == 'Compare & radar':
    st.title('Player Comparison Studio')
    names = sorted(df.player.dropna().astype(str).unique())
    picks = st.multiselect('Select up to four players', names, default=names[:2])
    if len(picks) > 4:
        picks = picks[:4]
        st.info('The comparison workspace uses the first four selected players.')

    if len(picks) >= 2:
        sub = df[df.player.isin(picks)].sort_values('minutes', ascending=False).groupby('player').head(1)
        metrics = [('Goals / 90','goals_p90_pct'),('Assists / 90','assists_p90_pct'),('Shots / 90','shots_p90_pct'),('Tackles / 90','tackles_p90_pct'),('Interceptions / 90','interceptions_p90_pct')]
        fig = go.Figure()
        for _, r in sub.iterrows():
            fig.add_trace(go.Scatterpolar(r=[r[c] for _, c in metrics], theta=[x for x, _ in metrics], fill='toself', name=r.player))
        fig.update_layout(template='plotly_dark', polar={'radialaxis': {'range': [0,100]}}, paper_bgcolor='rgba(0,0,0,0)', height=550)
        st.plotly_chart(fig, use_container_width=True)
        table = sub[['player','position','club','league','age','minutes','goals','assists','impact_adjusted','market_rank']]
        st.dataframe(table, use_container_width=True, hide_index=True)

        selected_metrics = [x for x, _ in metrics]
        comparison_payload = table.to_dict(orient='records')
        if st.button('Save comparison to SQLite', use_container_width=True):
            add_comparison_history(
                sub.player_id.tolist(), sub.player.tolist(), selected_metrics, comparison_payload
            )
            st.success('Comparison history saved. It is now visible in Database history and DB Browser for SQLite.')
    else:
        st.info('Select at least two players to create a comparison.')


elif page == 'Scouting plot':
    st.title('Scouting Plot')
    st.caption('DataMB-inspired exploration: two-variable player discovery with filters, sample controls and role-aware impact context.')
    metric_map = {'Goals / 90':'goals_p90','Assists / 90':'assists_p90','Shots / 90':'shots_p90','Shots on target / 90':'sot_p90','Tackles / 90':'tackles_p90','Interceptions / 90':'interceptions_p90','Impact index':'impact_adjusted','Age':'age','Minutes':'minutes'}
    c1, c2, c3 = st.columns(3)
    xlab = c1.selectbox('X metric', list(metric_map), index=0)
    ylab = c2.selectbox('Y metric', list(metric_map), index=1)
    minmin = c3.slider('Minimum minutes', 0, 3000, 900, 100)
    posopts = ['All'] + sorted(df.position.fillna('Unknown').str.split(',').str[0].unique())
    pos = st.selectbox('Primary position', posopts)
    s = df[df.minutes >= minmin].copy()
    if pos != 'All':
        s = s[s.position.fillna('Unknown').str.split(',').str[0] == pos]
    s['label'] = s.player + ' · ' + s.club
    if not s.empty:
        fig = px.scatter(s, x=metric_map[xlab], y=metric_map[ylab], hover_name='label', size='minutes', color='league', title=f'{xlab} vs {ylab}', trendline=None)
        st.plotly_chart(figure_layout(fig, 650), use_container_width=True)
        st.dataframe(s.sort_values('impact_adjusted', ascending=False)[['player','position','club','league','age','minutes',metric_map[xlab],metric_map[ylab],'impact_adjusted']].head(100), use_container_width=True, hide_index=True)
    else:
        st.warning('No records match the current filters.')


elif page == 'Recruitment shortlist':
    st.title('Recruitment Shortlist')
    sl = get_shortlist()
    if sl.empty:
        st.info('No players are currently shortlisted.')
    else:
        st.dataframe(sl, use_container_width=True, hide_index=True)
        selected = st.selectbox('Manage player', sl.player.tolist())
        row = sl[sl.player == selected].iloc[0]
        with st.form('shortlist_management'):
            notes = st.text_area('Recruitment notes', value=str(row.notes or ''))
            priority = st.selectbox('Priority', ['High','Medium','Low'], index=['High','Medium','Low'].index(row.priority) if row.priority in ['High','Medium','Low'] else 1)
            status = st.selectbox('Status', ['Active','Monitoring','Contacted','Rejected','Signed'], index=['Active','Monitoring','Contacted','Rejected','Signed'].index(row.status) if row.status in ['Active','Monitoring','Contacted','Rejected','Signed'] else 0)
            role = st.text_input('Target role', value=str(row.target_role or ''))
            submitted = st.form_submit_button('Update shortlist record')
            if submitted:
                update_shortlist(row.player_id, notes, status, priority, role)
                st.success('Shortlist record updated in SQLite.')
                st.rerun()
        if st.button('Remove selected player'):
            remove_shortlist(row.player_id)
            st.rerun()
        st.download_button('Export shortlist CSV', sl.to_csv(index=False).encode(), 'football_recruitment_shortlist.csv', 'text/csv')


elif page == 'User data entry':
    st.title('Recruitment Data Entry')
    st.caption('Manual scouting and transfer-planning inputs are stored separately from source performance data so provenance remains clear.')

    with st.form('user_input_form', clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        player_name = c1.text_input('Player name *')
        position = c2.text_input('Position')
        current_club = c3.text_input('Current club')
        c4, c5, c6 = st.columns(3)
        target_club = c4.text_input('Target club')
        age = c5.number_input('Age', min_value=0.0, max_value=50.0, value=24.0, step=0.5)
        minutes = c6.number_input('Minutes', min_value=0.0, value=0.0, step=100.0)
        c7, c8, c9 = st.columns(3)
        goals = c7.number_input('Goals', min_value=0.0, value=0.0, step=1.0)
        assists = c8.number_input('Assists', min_value=0.0, value=0.0, step=1.0)
        transfer_fee = c9.number_input('Planned transfer fee', min_value=0.0, value=0.0, step=100000.0)
        c10, c11, c12 = st.columns(3)
        wages = c10.number_input('Planned wage / salary reference', min_value=0.0, value=0.0, step=1000.0)
        contract_years = c11.number_input('Contract years', min_value=0.0, max_value=10.0, value=3.0, step=0.5)
        target_role = c12.text_input('Target role')
        scouting_notes = st.text_area('Scouting notes', placeholder='Role fit, strengths, risks, tactical observations, recruitment rationale...')
        submit = st.form_submit_button('Save user input to SQLite', use_container_width=True)
        if submit:
            if not player_name.strip():
                st.error('Player name is required.')
            else:
                input_id = add_user_input({
                    'player_name': player_name.strip(), 'position': position.strip(),
                    'current_club': current_club.strip(), 'target_club': target_club.strip(),
                    'age': age, 'minutes': minutes, 'goals': goals, 'assists': assists,
                    'transfer_fee': transfer_fee, 'wages': wages,
                    'contract_years': contract_years, 'target_role': target_role.strip(),
                    'scouting_notes': scouting_notes.strip()
                })
                st.success(f'User input saved with database ID {input_id}.')

    st.markdown('### Stored manual inputs')
    inputs = get_user_inputs()
    st.dataframe(inputs, use_container_width=True, hide_index=True)
    if not inputs.empty:
        selected_id = st.number_input('Input ID to delete', min_value=int(inputs.input_id.min()), max_value=int(inputs.input_id.max()), value=int(inputs.input_id.iloc[0]), step=1)
        if st.button('Delete selected manual input'):
            delete_user_input(int(selected_id))
            st.rerun()
        st.download_button('Export user inputs CSV', inputs.to_csv(index=False).encode(), 'fti_user_inputs.csv', 'text/csv')


elif page == 'Database history':
    st.title('Database History & Audit')
    st.caption('This workspace makes the SQLite persistence layer visible to the project user and to an examiner reviewing the application.')

    summary = database_summary()
    cols = st.columns(6)
    for col, label in zip(cols, ['Players','Analyses','Shortlist','Sources','User inputs','Comparisons']):
        key = {'Players':'players','Analyses':'analyses','Shortlist':'shortlist','Sources':'source_registry','User inputs':'user_inputs','Comparisons':'comparison_history'}[label]
        col.metric(label, f'{summary[key]:,}')

    tab1, tab2, tab3 = st.tabs(['Analysis history','Comparison history','SQLite file'])
    with tab1:
        hist = get_analysis_history()
        if hist.empty:
            st.info('No analysis snapshots saved yet.')
        else:
            view = hist.drop(columns=['result_json'], errors='ignore')
            st.dataframe(view, use_container_width=True, hide_index=True)
            st.download_button('Export analysis history', hist.to_csv(index=False).encode(), 'fti_analysis_history.csv', 'text/csv')
    with tab2:
        hist = get_comparison_history()
        if hist.empty:
            st.info('No comparison history saved yet.')
        else:
            display = hist.copy()
            display['players'] = display.player_names.apply(lambda x: ', '.join(json.loads(x)) if x else '')
            display = display[['comparison_id','created_at','players','metrics_used']]
            st.dataframe(display, use_container_width=True, hide_index=True)
            selected = st.number_input('Comparison ID to delete', min_value=int(hist.comparison_id.min()), max_value=int(hist.comparison_id.max()), value=int(hist.comparison_id.iloc[0]), step=1)
            if st.button('Delete selected comparison history'):
                delete_comparison_history(int(selected))
                st.rerun()
            st.download_button('Export comparison history', hist.to_csv(index=False).encode(), 'fti_comparison_history.csv', 'text/csv')
    with tab3:
        st.code(str(DB_PATH), language='text')
        st.write('Open this exact file in DB Browser for SQLite. The tables are: players, analyses, shortlist, source_registry, user_inputs and comparison_history.')
        try:
            db_bytes = DB_PATH.read_bytes()
            st.download_button('Download current SQLite database', db_bytes, 'transfer_intelligence.db', 'application/x-sqlite3')
        except Exception as e:
            st.error(f'Could not read database file: {e}')


elif page == 'Data laboratory':
    st.title('Data Laboratory')
    st.write('Source ingestion, normalized SQLite storage, quality checks and analytical feature engineering are separated so the dataset can be refreshed without redesigning the application.')
    st.dataframe(df.head(100), use_container_width=True, hide_index=True)
    st.download_button('Export normalized player data', df.to_csv(index=False).encode(), 'fti_player_data.csv', 'text/csv')

    st.markdown('### Coverage diagnostics')
    diag = pd.DataFrame({
        'metric': ['Rows','Players','Clubs','Leagues','Nations','Median minutes','Median age','Median impact index'],
        'value': [len(df),df.player.nunique(),df.club.nunique(),df.league.nunique(),df.nation.nunique(),round(df.minutes.median(),1),round(df.age.median(),1),round(df.impact_adjusted.median(),1)]
    })
    st.dataframe(diag, use_container_width=True, hide_index=True)

    st.markdown('### Exploratory model index')
    if st.button('Train exploratory ExtraTrees index'):
        model, scored = train_value_model(df)
        imp = pd.DataFrame({'feature':['age','minutes','goals_p90','assists_p90','shots_p90','tackles_p90','interceptions_p90'], 'importance':model.feature_importances_}).sort_values('importance', ascending=False)
        st.dataframe(imp, use_container_width=True, hide_index=True)
        st.caption('This model is an exploratory analytical feature, not a market-price predictor. No transfer-fee target is trained.')


else:
    st.title('Methodology & Sources')
    st.markdown('''
### Data architecture
**Primary performance source:** FBref-derived Football Players Stats 2025/26 dataset, loaded through a configurable GitHub mirror. The project normalizes source records into SQLite.

**Comparison methodology:** DataMB is used as a product/design reference for player radars, percentile profiles, rank-style thinking, per-90 metrics and two-variable scouting plots. Proprietary DataMB values are not copied into this application.

**Open football analytics source:** StatsBomb Open Data is documented as an optional event-level research source.

### SQLite architecture
- **players:** source-derived player-season performance records.
- **analyses:** saved player analysis snapshots and analytical drivers.
- **comparison_history:** every saved multi-player comparison, including selected metrics and comparison payload.
- **shortlist:** recruitment candidates, priority, status, role and notes.
- **user_inputs:** manually entered scouting / transfer-planning records.
- **source_registry:** source provenance, coverage and licensing notes.

### Important limitation
This is a recruitment analytics prototype, not a live transfer-fee oracle. Performance data and market valuations are separate concepts. Manual transfer-fee and wage fields are stored as user inputs and are not presented as verified market values.

### Reproducibility
Refreshing the source replaces the normalized `players` table while preserving user-generated analysis, comparison, shortlist and manual-input history. The source URL and source label are recorded in SQLite.
''')
    st.markdown('### References')
    st.markdown('- DataMB guide: https://datamb.football/guide/\n- DataMB radars: https://datamb.football/radars/\n- StatsBomb Open Data: https://github.com/hudl/open-data\n- FBref: https://fbref.com/en/')
