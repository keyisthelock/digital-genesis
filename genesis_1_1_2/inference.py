"""Small Bayesian residual heads over bounded action history."""

from itertools import product
from math import sqrt

CONFIGS = tuple(product((-1, 1), repeat=2))
LAGS = ((2, 0), (3, 0), (4, 2), (0, 3), (0, 4))
FOOD_WEIGHT = .90
INFO_HORIZON = 5.


def features(config, lag=(1, 1)):
    a, b = (v if seen else 0 for v, seen in zip(config, lag))
    return (1., a, b, a*b)


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


class Regression:
    """Rank-one Gaussian updates with a modest process-noise allowance."""

    def __init__(self, intercept, variance, noise):
        self.weights = [intercept, 0., 0., 0.]
        self.cov = [[variance*(i == j) for j in range(4)] for i in range(4)]
        self.noise = noise
        self.count = 0

    def mean(self, x):
        return dot(self.weights, x)

    def covariance(self, x, y):
        return dot(x, [dot(row, y) for row in self.cov])

    def update(self, x, y):
        for i in range(4):
            self.cov[i][i] += .10
        projection = [dot(row, x) for row in self.cov]
        variance = self.noise + dot(x, projection)
        error = y-self.mean(x)
        for i, value in enumerate(projection):
            self.weights[i] += value*error/variance
            for j, other in enumerate(projection):
                self.cov[i][j] -= value*other/variance
        self.count += 1
        return error, sqrt(variance)


class ResidualModel:
    """Five age-pattern heads and a separate observed stock head."""

    def __init__(self):
        self.loss = {lag: Regression(0., 2., .8) for lag in LAGS}
        self.stock = Regression(5., 2.5, 1.)

    def forecast(self, config):
        losses = tuple(max(0., self.loss[lag].mean(features(config, lag))) for lag in LAGS)
        stock = min(10., max(0., self.stock.mean(features(config))))
        return losses, stock

    def utility_covariance(self, a, b):
        loss = sum(self.loss[lag].covariance(features(a, lag), features(b, lag)) for lag in LAGS)
        return loss + FOOD_WEIGHT**2*self.stock.covariance(features(a), features(b))

    def information(self, candidate, utilities):
        """One-step knowledge gradient for a noisy net consequence observation."""
        variance = self.utility_covariance(candidate, candidate) + 5.
        shifts = {c: self.utility_covariance(c, candidate)/sqrt(variance) for c in utilities}
        baseline = max(utilities.values())
        return max(0., sum(weight*max(utilities[c]+z*shifts[c] for c in utilities)
                           for z, weight in ((-1.5, .22), (0., .56), (1.5, .22))) - baseline)
