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


def _save_events(match_id):
    target = RAW_DIR / "events" / f"{match_id}.json.gz"
    if target.exists():
        return
    tmp = target.with_suffix(".tmp")
    tmp.write_bytes(gzip.compress(_get(f"events/{match_id}.json"), compresslevel=6))
    tmp.replace(target)


def download(workers=8, progress=print):
    """Fetch match lists and event files. Returns {league: number of matches}."""
    (RAW_DIR / "events").mkdir(parents=True, exist_ok=True)
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

    failed = []
    with ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(_save_events, mid): mid for mid in match_ids}
        for done, future in enumerate(as_completed(futures), 1):
            try:
                future.result()
            except Exception as e:
                failed.append((futures[future], str(e)))
            if done % 100 == 0:
                progress(f"{done}/{len(match_ids)} matches")
    if failed:
        raise RuntimeError(f"{len(failed)} downloads failed, first: {failed[0]}")
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
