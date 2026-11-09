"""Step 3: train the models, build the pools and profiles, then calibrate the simulator."""
import json

import joblib

from metafut.config import BUNDLE, MODEL_DIR, REPORT_DIR
from metafut.models.train import train_all
from metafut.sim.calibrate import calibrate_shots
from metafut.sim.engine import Simulator

if __name__ == "__main__":
    report = train_all()
    bundle = joblib.load(MODEL_DIR / BUNDLE)
    report["calibration"] = calibrate_shots(Simulator(bundle))
    joblib.dump(bundle, MODEL_DIR / BUNDLE)
    (REPORT_DIR / "model_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
