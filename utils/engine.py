import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity

STAT_COLS = ['goals_p90', 'assists_p90', 'shots_p90', 'sot_p90', 'tackles_p90', 'interceptions_p90', 'minutes']


def add_features(df):
    df = df.copy()
    numeric = ['age','minutes','goals','assists','shots','shots_on_target','tackles_won','interceptions']
    for c in numeric:
        df[c] = pd.to_numeric(df.get(c, 0), errors='coerce').fillna(0)
    n90 = (df['minutes'] / 90).replace(0, np.nan)
    for raw, out in [('goals','goals_p90'), ('assists','assists_p90'), ('shots','shots_p90'),
                     ('shots_on_target','sot_p90'), ('tackles_won','tackles_p90'),
                     ('interceptions','interceptions_p90')]:
        df[out] = (df[raw] / n90).replace([np.inf, -np.inf], np.nan).fillna(0)
    df['age'] = df['age'].fillna(df['age'].median() if len(df) else 25)
    return df


def percentile_series(s):
    return s.rank(pct=True).fillna(0) * 100


def add_percentiles(df):
    df = df.copy()
    metrics = ['goals_p90','assists_p90','shots_p90','sot_p90','tackles_p90','interceptions_p90']
    for c in metrics:
        df[c + '_pct'] = percentile_series(df[c])
    return df


def impact_score(row):
    vals = [row.get('goals_p90_pct', 0), row.get('assists_p90_pct', 0),
            row.get('shots_p90_pct', 0), row.get('tackles_p90_pct', 0),
            row.get('interceptions_p90_pct', 0)]
    pos = str(row.get('position', '')).upper()
    if 'GK' in pos:
        weights = [0.0, 0.0, 0.05, 0.45, 0.50]
    elif 'DF' in pos:
        weights = [0.10, 0.10, 0.05, 0.40, 0.35]
    elif 'FW' in pos:
        weights = [0.45, 0.25, 0.20, 0.05, 0.05]
    else:
        weights = [0.20, 0.30, 0.15, 0.20, 0.15]
    return float(np.dot(vals, weights))


def profile_scores(df):
    df = add_percentiles(add_features(df))
    df['impact_score'] = df.apply(impact_score, axis=1)
    df['reliability'] = np.clip(np.sqrt(df['minutes'].clip(lower=0) / 1800), 0, 1)
    df['impact_adjusted'] = df['impact_score'] * df['reliability']
    df['market_rank'] = df['impact_adjusted'].rank(method='min', ascending=False).astype(int)
    df['availability_index'] = (100 - ((df['age'] - 18).clip(lower=0, upper=17) / 17 * 35)).clip(0, 100)
    return df



def similarity(df, player_id, feature_cols):
    if df.empty:
        return pd.DataFrame()
    x = df[feature_cols].apply(
        pd.to_numeric, errors="coerce"
    ).fillna(0)
    scaler = StandardScaler()
    z = scaler.fit_transform(x)
    matches = np.flatnonzero(
        df["player_id"].to_numpy() == player_id
    )
    if matches.size == 0:
        return pd.DataFrame()
    selected_position = matches[0]
    sims = cosine_similarity(
        z[selected_position].reshape(1, -1), z
    ).ravel()
    out = df[
        ["player_id", "player", "position",
         "club", "league", "age", "minutes"]
    ].copy()
    out["similarity"] = sims * 100

    return (
        out[out.player_id != player_id]
        .sort_values("similarity", ascending=False)
        .reset_index(drop=True)
    )


def train_value_model(df):
    d = df.copy()
    d = profile_scores(d)
    target = 'impact_adjusted'
    feats = ['age','minutes','goals_p90','assists_p90','shots_p90','tackles_p90','interceptions_p90']
    X = d[feats].replace([np.inf, -np.inf], np.nan).fillna(0)
    y = d[target].fillna(0)
    model = ExtraTreesRegressor(n_estimators=250, random_state=42, min_samples_leaf=4, n_jobs=-1)
    model.fit(X, y)
    d['model_index'] = model.predict(X)
    return model, d
