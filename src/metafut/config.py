"""Paths and constants shared by the whole project.

Data and models live outside the repo and outside OneDrive. Set the METAFUT_DATA
environment variable to move them; the default is <home>/metafut-data.
"""
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("METAFUT_DATA", Path.home() / "metafut-data"))
RAW_DIR = DATA_DIR / "raw"
TABLE_DIR = DATA_DIR / "tables"
MODEL_DIR = DATA_DIR / "models"
REPORT_DIR = Path(__file__).resolve().parents[2] / "reports"

OPEN_DATA_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

# League name -> (StatsBomb competition name, season). Full 2015/16 seasons in open data.
LEAGUES = {
    "premier_league": ("Premier League", "2015/2016"),
    "la_liga": ("La Liga", "2015/2016"),
    "serie_a": ("Serie A", "2015/2016"),
    "ligue_1": ("Ligue 1", "2015/2016"),
}

# StatsBomb pitch, in the attacking direction of the team on the ball.
PITCH_X = 120.0
PITCH_Y = 80.0
GOAL_X = 120.0
GOAL_Y = 40.0

# Date-ordered split inside each league. The test part stays unread until the final evaluation.
TRAIN_FRACTION = 0.6
VAL_FRACTION = 0.2

ACTIONS = ["pass", "carry", "dribble", "shot", "loss", "clear"]
PHASES = ["open", "kick_off", "throw_in", "goal_kick", "corner", "free_kick", "penalty"]
HEIGHTS = ["none", "ground", "low", "high"]
POSITIONS = ["GK", "DEF", "MID", "FWD"]
# What the previous on-ball decision was and how it ended.
RESULTS = ["start", "pass_complete", "pass_incomplete", "pass_out", "pass_offside", "carry",
           "dribble_success", "dribble_fail", "shot_goal", "shot_nogoal", "loss", "clear"]

ACTION_ID = {name: i for i, name in enumerate(ACTIONS)}
PHASE_ID = {name: i for i, name in enumerate(PHASES)}
HEIGHT_ID = {name: i for i, name in enumerate(HEIGHTS)}
POSITION_ID = {name: i for i, name in enumerate(POSITIONS)}
RESULT_ID = {name: i for i, name in enumerate(RESULTS)}
