"""Step 1: download four leagues of StatsBomb open data (about 1,500 matches)."""
from metafut.config import DATA_DIR
from metafut.data.ingest import download

if __name__ == "__main__":
    print("Saving to", DATA_DIR)
    print(download())
