"""Tests for pitch zones, sampling pools and rate tables."""
import numpy as np

from metafut.models.features import N_ZONES, zone
from metafut.models.pools import Pool, rate_table


def test_zone_corners_stay_in_range():
    assert zone(np.array([0.0]), np.array([0.0]))[0] == 0
    assert zone(np.array([120.0]), np.array([80.0]))[0] == N_ZONES - 1
    assert zone(np.array([15.0]), np.array([5.0]))[0] == 1
    assert zone(np.array([5.0]), np.array([15.0]))[0] == 12


def test_pool_only_returns_values_from_the_right_key():
    keys = np.array([0] * 30 + [1] * 30)
    values = np.column_stack([keys.astype(float)])
    pool = Pool(keys, values, 3)
    out = pool.sample(np.array([0, 1, 1, 0]), np.random.default_rng(0))
    assert list(out[:, 0]) == [0, 1, 1, 0]


def test_pool_uses_fallback_for_rare_keys():
    keys = np.array([0] * 30 + [1] * 2)
    fallback = np.array([7] * 32)
    values = np.column_stack([keys.astype(float)])
    pool = Pool(keys, values, 3, fallbacks=[(fallback, 8)])
    out = pool.sample(np.full(50, 2), np.random.default_rng(0), fallbacks=[np.full(50, 7)])
    assert set(out[:, 0]) <= {0.0, 1.0}


def test_pool_walks_down_a_chain_of_fallbacks():
    keys = np.array([0] * 25 + [1] * 25)
    middle = np.zeros(50, dtype=int)
    last = np.zeros(50, dtype=int)
    values = np.column_stack([keys.astype(float)])
    pool = Pool(keys, values, 4, fallbacks=[(middle, 2), (last, 1)])
    out = pool.sample(np.array([3, 3]), np.random.default_rng(0),
                      fallbacks=[np.array([1, 1]), np.array([0, 0])])
    assert set(out[:, 0]) <= {0.0, 1.0}


def test_pool_sampling_is_repeatable_with_a_seed():
    pool = Pool(np.zeros(100, dtype=int), np.arange(100.0)[:, None], 1)
    a = pool.sample(np.zeros(20, dtype=int), np.random.default_rng(5))
    b = pool.sample(np.zeros(20, dtype=int), np.random.default_rng(5))
    assert (a == b).all()


def test_rate_table_shrinks_small_samples_toward_the_mean():
    keys = np.array([0] * 1000 + [1])
    hits = np.array([0] * 1000 + [1])
    table = rate_table(keys, hits, 2, prior=20)
    assert table[1] < 0.1
    assert table[0] < 0.01
