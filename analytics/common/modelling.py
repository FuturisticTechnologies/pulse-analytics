"""Small, dependency-free implementations of the models this platform needs.

Written out rather than imported from scikit-learn so a reviewer can see - and
challenge - the actual maths, and so the runtime image stays small enough to
start in a second. Each function is deterministic given its seed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# Scaling
# --------------------------------------------------------------------------- #
def standardise(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Z-score each column. Returns (scaled, mean, std).

    Zero-variance columns get std=1 so they scale to a constant zero instead of
    producing NaN and silently poisoning every distance computation.
    """
    mean = matrix.mean(axis=0)
    std = matrix.std(axis=0)
    std = np.where(std == 0, 1.0, std)
    return (matrix - mean) / std, mean, std


def log1p_positive(series: pd.Series) -> pd.Series:
    """log1p on a non-negative series - tames the long tail of money columns.

    Monetary and frequency features are strongly right-skewed. Clustering them
    raw produces one cluster containing everybody and four containing the
    whales, which is a technically valid and completely useless answer.
    """
    return np.log1p(series.clip(lower=0).astype(float))


# --------------------------------------------------------------------------- #
# k-means
# --------------------------------------------------------------------------- #
def kmeans(matrix: np.ndarray, k: int, *, seed: int = 42, max_iter: int = 300,
           tol: float = 1e-5) -> tuple[np.ndarray, np.ndarray, float]:
    """Lloyd's algorithm with k-means++ initialisation.

    Returns (labels, centroids, inertia). k-means++ rather than random starts
    because random initialisation on skewed retail data routinely converges to a
    degenerate solution, and a segmentation that changes every run cannot be
    operationalised.
    """
    rng = np.random.default_rng(seed)
    n_samples = matrix.shape[0]
    k = max(1, min(k, n_samples))

    # ---- k-means++ seeding
    centroids = np.empty((k, matrix.shape[1]), dtype=float)
    centroids[0] = matrix[rng.integers(n_samples)]
    closest = ((matrix - centroids[0]) ** 2).sum(axis=1)
    for index in range(1, k):
        probabilities = closest / closest.sum() if closest.sum() > 0 else None
        choice = rng.choice(n_samples, p=probabilities)
        centroids[index] = matrix[choice]
        closest = np.minimum(closest, ((matrix - centroids[index]) ** 2).sum(axis=1))

    labels = np.zeros(n_samples, dtype=int)
    inertia = float("inf")
    for _ in range(max_iter):
        distances = ((matrix[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        new_labels = distances.argmin(axis=1)
        new_inertia = float(distances[np.arange(n_samples), new_labels].sum())

        for index in range(k):
            members = matrix[new_labels == index]
            if len(members):
                centroids[index] = members.mean(axis=0)
            else:
                # An empty cluster steals the point furthest from its centroid,
                # which is the standard repair and keeps k clusters meaningful.
                centroids[index] = matrix[distances.min(axis=1).argmax()]

        converged = abs(inertia - new_inertia) <= tol * max(abs(inertia), 1.0)
        labels, inertia = new_labels, new_inertia
        if converged:
            break

    return labels, centroids, inertia


def silhouette_score(matrix: np.ndarray, labels: np.ndarray,
                     sample_size: int = 1500, seed: int = 42) -> float:
    """Mean silhouette coefficient, sampled for tractability.

    Silhouette is O(n^2); on a large customer base we sample. The sample is
    seeded so the reported score is reproducible.
    """
    rng = np.random.default_rng(seed)
    n = matrix.shape[0]
    if n > sample_size:
        index = rng.choice(n, sample_size, replace=False)
        matrix, labels = matrix[index], labels[index]
        n = sample_size
    if len(np.unique(labels)) < 2 or n < 3:
        return 0.0

    distances = np.sqrt(((matrix[:, None, :] - matrix[None, :, :]) ** 2).sum(axis=2))
    scores = np.zeros(n)
    for i in range(n):
        same = labels == labels[i]
        same[i] = False
        if not same.any():
            continue
        a = distances[i, same].mean()
        b = min(
            distances[i, labels == other].mean()
            for other in np.unique(labels) if other != labels[i]
        )
        scores[i] = (b - a) / max(a, b)
    return float(np.round(scores.mean(), 4))


def choose_k(matrix: np.ndarray, candidates=range(2, 8), seed: int = 42) -> pd.DataFrame:
    """Fit each candidate k and report inertia plus silhouette.

    Reported rather than auto-chosen: the right number of segments is a business
    decision about how many campaigns a team can actually run, informed - not
    decided - by the metrics.
    """
    rows = []
    for k in candidates:
        labels, _centroids, inertia = kmeans(matrix, k, seed=seed)
        rows.append({
            "k": k,
            "inertia": round(inertia, 2),
            "silhouette": silhouette_score(matrix, labels, seed=seed),
            "smallest_cluster_pct": round(
                float(pd.Series(labels).value_counts(normalize=True).min() * 100), 2
            ),
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Logistic regression (gradient descent)
# --------------------------------------------------------------------------- #
def fit_logistic(features: np.ndarray, target: np.ndarray, *, learning_rate: float = 0.1,
                 iterations: int = 800, l2: float = 0.01) -> np.ndarray:
    """Binary logistic regression by batch gradient descent, with L2.

    Enough for a churn *propensity score*: the ranking is what drives the
    retention campaign, and a well-calibrated ranking from a transparent linear
    model is worth more operationally than a marginally better black box nobody
    will sign off on.
    """
    design = np.hstack([np.ones((features.shape[0], 1)), features])
    weights = np.zeros(design.shape[1])
    n = design.shape[0]

    for _ in range(iterations):
        predictions = sigmoid(design @ weights)
        gradient = design.T @ (predictions - target) / n
        gradient[1:] += l2 * weights[1:]        # do not regularise the intercept
        weights -= learning_rate * gradient
    return weights


def sigmoid(values: np.ndarray) -> np.ndarray:
    # Clipped to avoid overflow warnings on confident predictions.
    return 1.0 / (1.0 + np.exp(-np.clip(values, -35, 35)))


def predict_logistic(weights: np.ndarray, features: np.ndarray) -> np.ndarray:
    design = np.hstack([np.ones((features.shape[0], 1)), features])
    return sigmoid(design @ weights)


def roc_auc(target: np.ndarray, scores: np.ndarray) -> float:
    """AUC via the rank-sum identity - no sorting of pairs required."""
    target = np.asarray(target).astype(int)
    positives, negatives = int(target.sum()), int((1 - target).sum())
    if positives == 0 or negatives == 0:
        return 0.5
    ranks = pd.Series(scores).rank().to_numpy()
    return float(round(
        (ranks[target == 1].sum() - positives * (positives + 1) / 2) / (positives * negatives),
        4,
    ))


def train_test_split(frame: pd.DataFrame, test_fraction: float = 0.25,
                     seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    mask = rng.random(len(frame)) >= test_fraction
    return frame[mask].copy(), frame[~mask].copy()


# --------------------------------------------------------------------------- #
# Time series
# --------------------------------------------------------------------------- #
def linear_trend(values: np.ndarray) -> tuple[float, float]:
    """Ordinary least squares against time index. Returns (slope, intercept)."""
    x = np.arange(len(values), dtype=float)
    if len(values) < 2:
        return 0.0, float(values[0] if len(values) else 0.0)
    slope, intercept = np.polyfit(x, values.astype(float), 1)
    return float(slope), float(intercept)


def holt_winters_additive(values: np.ndarray, season_length: int, horizon: int,
                          alpha: float = 0.3, beta: float = 0.08,
                          gamma: float = 0.25) -> tuple[np.ndarray, np.ndarray]:
    """Triple exponential smoothing with additive seasonality.

    Chosen over ARIMA because retail demand is level + trend + a stable weekly
    or monthly shape, which is exactly what Holt-Winters models, and because its
    three parameters are explainable to the person whose budget depends on the
    forecast.

    Returns (fitted_values, forecast).
    """
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n < max(2 * season_length, 4):
        # Not enough history for a seasonal model: fall back to a trend line.
        slope, intercept = linear_trend(values)
        fitted = intercept + slope * np.arange(n)
        forecast = intercept + slope * np.arange(n, n + horizon)
        return fitted, np.maximum(forecast, 0.0)

    seasons = n // season_length
    # Initial level and trend from the first two whole seasons.
    season_means = np.array([
        values[i * season_length:(i + 1) * season_length].mean() for i in range(seasons)
    ])
    level = season_means[0]
    trend = (season_means[1] - season_means[0]) / season_length
    seasonal = np.array([
        np.mean([values[i * season_length + j] - season_means[i] for i in range(seasons)])
        for j in range(season_length)
    ])

    fitted = np.zeros(n)
    for t in range(n):
        season_index = t % season_length
        fitted[t] = level + trend + seasonal[season_index]
        previous_level = level
        level = alpha * (values[t] - seasonal[season_index]) + (1 - alpha) * (level + trend)
        trend = beta * (level - previous_level) + (1 - beta) * trend
        seasonal[season_index] = (
            gamma * (values[t] - level) + (1 - gamma) * seasonal[season_index]
        )

    forecast = np.array([
        level + (h + 1) * trend + seasonal[(n + h) % season_length]
        for h in range(horizon)
    ])
    return fitted, np.maximum(forecast, 0.0)


def forecast_accuracy(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    """MAE, RMSE and MAPE. MAPE skips zero actuals rather than returning inf."""
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    errors = actual - predicted
    non_zero = actual != 0
    return {
        "mae": round(float(np.abs(errors).mean()), 2),
        "rmse": round(float(np.sqrt((errors ** 2).mean())), 2),
        "mape_pct": round(
            float(np.abs(errors[non_zero] / actual[non_zero]).mean() * 100), 2
        ) if non_zero.any() else 0.0,
        "bias": round(float(errors.mean()), 2),
    }


def prediction_interval(residuals: np.ndarray, horizon: int,
                        confidence: float = 0.80) -> np.ndarray:
    """Widening interval half-widths: residual sigma x z x sqrt(step).

    The sqrt growth reflects accumulating uncertainty. Approximate, and labelled
    as such wherever it is plotted - a forecast drawn without an interval
    invites the reader to treat one number as certain.
    """
    sigma = float(np.std(residuals)) if len(residuals) > 1 else 0.0
    z = {0.50: 0.674, 0.80: 1.282, 0.90: 1.645, 0.95: 1.960}.get(confidence, 1.282)
    return sigma * z * np.sqrt(np.arange(1, horizon + 1))
