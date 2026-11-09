"""Step 2: build the decisions, matches, lineups and players tables from the raw files."""
from metafut.data.actions import build_players, build_tables

if __name__ == "__main__":
    t = build_tables()
    print(f"decisions: {len(t):,}")
    print(t.action.value_counts().to_string())
    print(t.split.value_counts().to_string())
    print(t.result.value_counts().to_string())
    players = build_players()
    print(f"players: {len(players):,} team-player pairs, {players.nickname.notna().sum():,} with a nickname")
