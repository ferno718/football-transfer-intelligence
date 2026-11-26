
# Football Transfer Intelligence (FTI)

A football recruitment analytics platform built using Python, Streamlit and SQLite. FTI helps explore player performance, evaluate positional profiles, discover similar players and manage recruitment shortlists through interactive data visualizations and a persistent database.

## Key Features

- **Market Overview:** Player population, league coverage and recruitment rankings.
- **Player Intelligence:** Individual player profiles, performance metrics and percentile analysis.
- **Player Comparison:** Interactive multi-player comparisons and radar charts.
- **Similarity Discovery:** Standardized player profiling using cosine similarity.
- **Scouting Plot:** Two-dimensional player exploration with performance filters.
- **Recruitment Shortlist:** Save candidates, recruitment priorities, notes and target roles.
- **Database History:** Persistent analysis and comparison records.
- **Data Laboratory:** Dataset exploration, quality checks and exploratory modelling.
- **Data Source Manager:** Refresh player records through a configurable CSV source.

## Technology Stack

| Category | Technologies |
|---|---|
| Programming | Python |
| Data Processing | Pandas, NumPy |
| Machine Learning | Scikit-learn, ExtraTrees |
| Similarity Analysis | StandardScaler, Cosine Similarity |
| Visualization | Plotly |
| Application | Streamlit |
| Database | SQLite |
| Data Retrieval | Requests |

## Analytical Methodology

### 1. Feature Engineering
Raw performance statistics are converted into per-90-minute indicators to support comparisons across players with different playing time.

### 2. Percentile Ranking
Performance metrics are converted into percentile scores within the loaded player sample.

### 3. Role-Weighted Impact Scoring
A custom impact index assigns different weights to attacking and defensive performance indicators based on player position.

### 4. Reliability Adjustment
A minutes-based reliability factor adjusts the impact score to reduce the influence of limited playing-time samples.

### 5. Similarity Discovery
Player performance features are standardized using StandardScaler and compared using cosine similarity to identify similar profiles.

### 6. Exploratory ExtraTrees Model
An ExtraTrees Regressor is used to explore patterns in the engineered impact index. It is not a validated transfer-fee prediction model.

## Database Architecture

FTI uses SQLite for persistent storage.

| Table | Purpose |
|---|---|
| players | Source-derived player performance records |
| analyses | Saved player analysis snapshots |
| comparison_history | Historical player comparisons |
| shortlist | Recruitment candidates and workflow status |
| user_inputs | Manual scouting and transfer-planning records |
| source_registry | Data provenance and source information |

The database is generated automatically at:

`data/transfer_intelligence.db`

The local database is excluded from version control.

## Project Structure

```text
football-transfer-intelligence/
│
├── assets/
├── data/
│   └── data_dictionary.md
├── models/
├── scripts/
│   ├── __init__.py
│   └── refresh_data.py
├── utils/
│   ├── __init__.py
│   ├── db.py
│   └── engine.py
│
├── app.py
├── README.md
├── requirements.txt
├── .gitignore
└── PROJECT_REPORT_NOTES.md
```

## Installation and Setup

### Prerequisites
- Python 3
- Git
- Windows PowerShell

### 1. Clone the Repository

```powershell
git clone https://github.com/YOUR_USERNAME/football-transfer-intelligence.git
cd football-transfer-intelligence
```

Replace `YOUR_USERNAME` with your GitHub username.

### 2. Create a Virtual Environment

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Load the Player Dataset

```powershell
$env:PYTHONPATH = (Get-Location).Path
python scripts\refresh_data.py
```

This downloads the configured CSV source, normalizes player records and loads them into SQLite.

### 5. Launch the Application

```powershell
streamlit run app.py
```

The application opens in your browser.

## Data Sources and Governance

The application currently uses an FBref-derived 2025/26 player statistics dataset through a configurable GitHub mirror.

Dataset source:
https://github.com/lkjmo123/EDA-NEW

The dataset is not included in this repository. Its original redistribution licence has not been independently verified. Users should review applicable upstream terms before reusing or redistributing the data.

Player performance statistics are kept separate from manually entered recruitment and transfer-planning values.

## Limitations

- Percentiles are relative to the loaded sample, not the entire global player population.
- Statistical comparisons do not replace professional scouting and tactical evaluation.
- The reliability adjustment is a heuristic rather than a calibrated uncertainty estimate.
- Similarity results depend on selected features and the dataset composition.
- Manual transfer fees and wages are user-entered references, not verified market valuations.
- The exploratory ExtraTrees model learns the engineered impact index and does not predict real transfer-market prices.
- Specialist goalkeeper statistics are not included in the current performance feature set.

## Future Improvements

- Additional performance and event-level metrics.
- Improved positional benchmarking.
- Model validation and evaluation.
- Enhanced source provenance and dataset versioning.
- Additional recruitment filters and scouting workflows.

---

**Football Transfer Intelligence (FTI)**  
Built with Python, Streamlit, Scikit-learn and SQLite.
