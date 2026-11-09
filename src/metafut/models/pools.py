"""Sampling pools: real observed values grouped by a key, sampled quickly for many matches at once.

Where a value has no simple formula (where a pass ends, what happens after a ball goes out), the
simulator draws a real example from the same situation. This keeps set pieces, stoppages and
turnovers realistic without a hand-written rule for each.
"""
import numpy as np


class Pool:
    """Rows of a numeric array grouped by an integer key.

    A key with too few examples falls back to the next, coarser key in `fallbacks`, a list of
    (keys, number of keys) pairs, and finally to all rows.
    """

    def __init__(self, keys, values, n_keys, fallbacks=None, min_count=20):
        keys = np.asarray(keys, dtype=np.int64)
        values = np.asarray(values, dtype=np.float32)
        order = np.argsort(keys, kind="stable")
        self.values = values[order]
        self.n_keys = n_keys
        self.start = np.searchsorted(keys[order], np.arange(n_keys))
        self.count = np.searchsorted(keys[order], np.arange(n_keys), side="right") - self.start
        self.min_count = min_count
        self.global_count = len(values)
        self.fallback = None
        if fallbacks:
            (next_keys, next_n), rest = fallbacks[0], fallbacks[1:]
            self.fallback = Pool(next_keys, values, next_n, fallbacks=rest, min_count=min_count)

    def sample(self, keys, rng, fallbacks=None):
        """One random row per key. `fallbacks` lists the coarser keys for the same rows."""
        keys = np.asarray(keys, dtype=np.int64)
        count = self.count[keys]
        start = self.start[keys]
        out = np.empty((len(keys), self.values.shape[1]), dtype=np.float32)
        ok = count >= self.min_count
        if ok.any():
            out[ok] = self.values[start[ok] + (rng.random(ok.sum()) * count[ok]).astype(np.int64)]
        if not ok.all():
            miss = ~ok
            if self.fallback is not None and fallbacks:
                out[miss] = self.fallback.sample(np.asarray(fallbacks[0], dtype=np.int64)[miss], rng,
                                                 [np.asarray(f)[miss] for f in fallbacks[1:]])
            else:
                out[miss] = self.values[(rng.random(miss.sum()) * self.global_count).astype(np.int64)]
        return out


def rate_table(keys, hits, n_keys, prior=20.0, base=None):
    """Smoothed probability per key, pulled toward `base` (one rate per key, for example the rate
    of a coarser key) or, without it, toward the overall rate where examples are few."""
    keys = np.asarray(keys, dtype=np.int64)
    hits = np.asarray(hits, dtype=np.float64)
    mean = hits.mean() if base is None else np.asarray(base, dtype=np.float64)
    total = np.bincount(keys, weights=hits, minlength=n_keys)
    count = np.bincount(keys, minlength=n_keys)
    return ((total + prior * mean) / (count + prior)).astype(np.float32)
