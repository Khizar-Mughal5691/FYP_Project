"""Step 3: train the pass, action and shot models and build the sampling pools."""
import json

from metafut.models.train import train_all

if __name__ == "__main__":
    print(json.dumps(train_all(), indent=2))
