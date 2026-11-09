"""FastHGB must give the same probabilities as sklearn for every batch size it handles."""
import numpy as np
import pytest
from sklearn.ensemble import HistGradientBoostingClassifier

from metafut.models import fast_predict
from metafut.models.fast_predict import FastHGB


def data(n, seed=0):
    rng = np.random.default_rng(seed)
    X = np.column_stack([rng.normal(size=n), rng.integers(0, 5, n), rng.uniform(0, 100, n),
                         rng.integers(2, 9, n), rng.normal(size=n)])
    y3 = (X[:, 0] + (X[:, 1] == 3) + X[:, 2] / 50 + rng.normal(scale=0.5, size=n) > 1.5).astype(int)
    y3 += (X[:, 3] > 6).astype(int)
    return X, y3


@pytest.fixture(scope="module")
def models():
    X, y = data(3000)
    binary = HistGradientBoostingClassifier(max_iter=40, categorical_features=[1, 3], random_state=0).fit(X, y > 0)
    multi = HistGradientBoostingClassifier(max_iter=30, categorical_features=[1, 3], random_state=0).fit(X, y)
    plain = HistGradientBoostingClassifier(max_iter=30, random_state=0).fit(X, y)
    return binary, multi, plain


@pytest.mark.parametrize("rows", [1, 7, 60, 500, 2500])
def test_same_probabilities_as_sklearn(models, rows):
    X, _ = data(rows, seed=1)
    X[0, 0] = np.nan                     # a missing value
    X[-1, 1] = 4.0
    if rows > 2:
        X[1, 3] = 42.0                   # a category never seen in training
        X[2, 1] = -1.0                   # a negative category counts as missing
    for model in models:
        assert np.allclose(FastHGB(model).predict_proba(X), model.predict_proba(X), atol=1e-12)


def test_every_path_is_used(models, monkeypatch):
    binary = models[0]
    X, _ = data(100, seed=2)
    fast = FastHGB(binary)
    expected = binary.predict_proba(X)
    for small, threaded in ((200, 400), (5, 400), (5, 50)):   # numpy walk, one thread, all cores
        monkeypatch.setattr(fast_predict, "SMALL_BATCH", small)
        monkeypatch.setattr(fast_predict, "THREADED_BATCH", threaded)
        assert np.allclose(fast.predict_proba(X), expected, atol=1e-12)
