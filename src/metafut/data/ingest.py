"""Download StatsBomb open data for the configured leagues. Safe to re-run: finished files are kept."""
import gzip
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from metafut.config import LEAGUES, OPEN_DATA_URL, RAW_DIR


def _get(path, tries=5):
    for attempt in range(tries):
        try:
            r = requests.get(f"{OPEN_DATA_URL}/{path}", timeout=60)
            r.raise_for_status()
            return r.content
        except requests.RequestException:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)


def _save(kind, match_id):
    """Save one match's file of the given kind ("events" or "lineups"), gzipped."""
    target = RAW_DIR / kind / f"{match_id}.json.gz"
    if target.exists():
        return
    tmp = target.with_suffix(".tmp")
    tmp.write_bytes(gzip.compress(_get(f"{kind}/{match_id}.json"), compresslevel=6))
    tmp.replace(target)


def _save_all(kind, match_ids, workers, progress):
    (RAW_DIR / kind).mkdir(parents=True, exist_ok=True)
    failed = []
    with ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(_save, kind, mid): mid for mid in match_ids}
        for done, future in enumerate(as_completed(futures), 1):
            try:
                future.result()
            except Exception as e:
                failed.append((futures[future], str(e)))
            if done % 250 == 0:
                progress(f"{kind}: {done}/{len(match_ids)} matches")
    if failed:
        raise RuntimeError(f"{len(failed)} {kind} downloads failed, first: {failed[0]}")


def download_lineups(match_ids, workers=8, progress=print):
    """Lineup files: each player's nickname and shirt number, used only to label players."""
    _save_all("lineups", match_ids, workers, progress)


def download(workers=8, progress=print):
    """Fetch match lists, event files and lineup files. Returns {league: number of matches}."""
    (RAW_DIR / "matches").mkdir(parents=True, exist_ok=True)
    competitions = json.loads(_get("competitions.json"))
    counts, match_ids = {}, []
    for league, (comp_name, season) in LEAGUES.items():
        row = next(c for c in competitions
                   if c["competition_name"] == comp_name and c["season_name"] == season
                   and c["competition_gender"] == "male")
        content = _get(f"matches/{row['competition_id']}/{row['season_id']}.json")
        (RAW_DIR / "matches" / f"{league}.json").write_bytes(content)
        matches = json.loads(content)
        counts[league] = len(matches)
        match_ids += [m["match_id"] for m in matches]

    _save_all("events", match_ids, workers, progress)
    download_lineups(match_ids, workers, progress)
    return counts


ODDS_URL = "https://www.football-data.co.uk/mmz4281/1516/{code}.csv"


def download_odds(codes):
    """Results and closing bookmaker odds for 2015/16 from football-data.co.uk, one small CSV per
    league. Used only as a benchmark for match forecasts. `codes` maps league to file code."""
    (RAW_DIR / "odds").mkdir(parents=True, exist_ok=True)
    sizes = {}
    for league, code in codes.items():
        target = RAW_DIR / "odds" / f"{league}.csv"
        if not target.exists():
            r = requests.get(ODDS_URL.format(code=code), timeout=60)
            r.raise_for_status()
            target.write_bytes(r.content)
        sizes[league] = target.stat().st_size
    return sizes
