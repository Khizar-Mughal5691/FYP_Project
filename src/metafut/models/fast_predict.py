"""Faster predictions for fitted HistGradientBoostingClassifier models, with identical results.

sklearn predicts one tree at a time and checks its input on every call. The simulator calls each
model about 2,000 times per batch of matches, and for small batches that overhead took 87% of the
simulation time. FastHGB copies the fitted trees into flat numpy arrays and walks all of them
together, one tree level per step. It follows sklearn's own rules for categories and missing values
(sklearn/ensemble/_hist_gradient_boosting/_predictor.pyx), and a test checks that both give the
same probabilities. Large batches still go to sklearn, whose compiled code is faster there.
"""
import os

import numpy as np

# Which way is fastest depends on the number of rows (measured on the development laptop):
SMALL_BATCH = 20      # up to here: walk all trees together in numpy
THREADED_BATCH = 400  # from here: let the compiled tree walk use every core
LARGE_BATCH = 2000    # above here: sklearn's own predict
CORES = os.cpu_count() or 1


class FastHGB:
    def __init__(self, model):
        self.model = model
        self.classes_ = model.classes_
        self.k = model.n_trees_per_iteration_
        self.baseline = np.asarray(model._baseline_prediction, dtype=np.float64).reshape(1, -1)

        # Categorical columns are encoded and moved to the front, as sklearn does before predicting.
        if model._preprocessor is None:
            self.cat_cols = np.empty(0, dtype=np.int64)
            self.num_cols = np.arange(model.n_features_in_)
            self.categories = []
        else:
            self.cat_cols = np.flatnonzero(model.is_categorical_)
            self.num_cols = np.flatnonzero(~model.is_categorical_)
            self.categories = [np.asarray(c, dtype=np.float64)
                               for c in model._preprocessor.named_transformers_["encoder"].categories_]
        self.known, self.f_idx_map = model._bin_mapper.make_known_categories_bitsets()

        # All trees in one set of arrays; child and bitset indices made global.
        parts, bitsets, roots, tree_class = [], [np.zeros((1, 8), dtype=np.uint32)], [], []
        node_offset, bitset_offset = 0, 1
        for trees in model._predictors:
            for k, tree in enumerate(trees):
                nodes = tree.nodes
                roots.append(node_offset)
                tree_class.append(k)
                parts.append((nodes, node_offset, bitset_offset))
                bitsets.append(tree.raw_left_cat_bitsets.reshape(-1, 8))
                node_offset += len(nodes)
                bitset_offset += len(tree.raw_left_cat_bitsets)
        nodes = np.concatenate([p[0] for p in parts])
        offsets = np.concatenate([np.full(len(p[0]), p[1]) for p in parts])
        bit_offsets = np.concatenate([np.full(len(p[0]), p[2]) for p in parts])
        self.left = nodes["left"].astype(np.int64) + offsets
        self.right = nodes["right"].astype(np.int64) + offsets
        self.feature = nodes["feature_idx"].astype(np.int64)
        self.threshold = nodes["num_threshold"].astype(np.float64)
        self.missing_left = nodes["missing_go_to_left"].astype(bool)
        self.is_leaf = nodes["is_leaf"].astype(bool)
        self.is_cat = nodes["is_categorical"].astype(bool)
        self.value = nodes["value"].astype(np.float64)
        self.bitset_row = np.where(self.is_cat, nodes["bitset_idx"].astype(np.int64) + bit_offsets, 0)
        self.left_bitsets = np.concatenate(bitsets).astype(np.uint32)
        self.roots = np.asarray(roots, dtype=np.int64)
        self.tree_class = np.asarray(tree_class, dtype=np.int64)
        self.max_depth = int(nodes["depth"].max()) + 1
        self.has_cats = bool(self.is_cat.any())

    def _encode(self, X):
        """Same columns and codes as sklearn's internal encoder: categories first, unknown -> NaN."""
        X = np.asarray(X, dtype=np.float64)
        if not len(self.cat_cols):
            return X
        out = np.empty((len(X), len(self.cat_cols)))
        for j, cats in enumerate(self.categories):
            col = X[:, self.cat_cols[j]]
            idx = np.clip(np.searchsorted(cats, col), 0, len(cats) - 1)
            out[:, j] = np.where(cats[idx] == col, idx, np.nan)
        return np.hstack([out, X[:, self.num_cols]])

    @staticmethod
    def _in_bitset(bitsets, rows, codes):
        return ((bitsets[rows, codes >> 5] >> (codes & 31).astype(np.uint32)) & 1).astype(bool)

    def _raw(self, X):
        Xt = self._encode(X)
        m = len(Xt)
        node = np.repeat(self.roots[:, None], m, axis=1)          # (trees, rows)
        row = np.broadcast_to(np.arange(m)[None, :], node.shape)
        for _ in range(self.max_depth):
            leaf = self.is_leaf[node]
            if leaf.all():
                break
            f = self.feature[node]
            val = Xt[row, f]
            missing = np.isnan(val)
            missing_left = self.missing_left[node]
            go_left = val <= self.threshold[node]
            if self.has_cats:
                cat = self.is_cat[node]
                negative = val < 0
                codes = np.where(missing | negative, 0, val).astype(np.int64) & 0xFF
                in_left = self._in_bitset(self.left_bitsets, self.bitset_row[node], codes)
                known = self._in_bitset(self.known, self.f_idx_map[f].astype(np.int64), codes)
                cat_left = np.where(in_left, True, np.where(known, False, missing_left))
                cat_left = np.where(negative, missing_left, cat_left)
                go_left = np.where(cat, cat_left, go_left)
            go_left = np.where(missing, missing_left, go_left)
            node = np.where(leaf, node, np.where(go_left, self.left[node], self.right[node]))
        values = self.value[node]
        raw = np.repeat(self.baseline, m, axis=0)
        for k in range(self.k):
            raw[:, k] += values[self.tree_class == k].sum(axis=0)
        return raw

    def _raw_direct(self, X, n_threads=1):
        """sklearn's compiled tree walk, without its per-call input checks and encoder pipeline."""
        Xt = np.ascontiguousarray(self._encode(X))
        raw = np.repeat(self.baseline, len(Xt), axis=0)
        for trees in self.model._predictors:
            for k, tree in enumerate(trees):
                raw[:, k] += tree.predict(Xt, self.known, self.f_idx_map, n_threads)
        return raw

    def predict_proba(self, X):
        m = len(X)
        if m > LARGE_BATCH:
            return self.model.predict_proba(X)
        if m <= SMALL_BATCH:
            raw = self._raw(X)
        else:
            raw = self._raw_direct(X, CORES if m >= THREADED_BATCH else 1)
        if self.k == 1:
            p = 1 / (1 + np.exp(-raw[:, 0]))
            return np.column_stack([1 - p, p])
        e = np.exp(raw - raw.max(axis=1, keepdims=True))
        return e / e.sum(axis=1, keepdims=True)
