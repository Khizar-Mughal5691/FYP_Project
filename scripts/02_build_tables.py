"""Step 2: build the decisions, matches and lineups tables from the raw files."""
from metafut.data.actions import build_tables

if __name__ == "__main__":
    t = build_tables()
    print(f"decisions: {len(t):,}")
    print(t.action.value_counts().to_string())
    print(t.split.value_counts().to_string())
    print(t.result.value_counts().to_string())
