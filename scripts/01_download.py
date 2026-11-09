"""Step 1: download four leagues of StatsBomb open data (about 1,500 matches, with their events and
lineups) and, as a benchmark for match forecasts, the 2015/16 bookmaker odds for the same leagues
(four small CSV files)."""
from metafut.config import DATA_DIR
from metafut.data.ingest import download, download_odds
from metafut.eval.forecast import ODDS_CODES

if __name__ == "__main__":
    print("Saving to", DATA_DIR)
    print(download())
    print("odds files (bytes):", download_odds(ODDS_CODES))
