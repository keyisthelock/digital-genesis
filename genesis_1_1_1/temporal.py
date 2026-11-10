"""Bounded eligibility and matched short rollouts over previously observed cells."""

from collections import deque
from dataclasses import dataclass
from math import sqrt

from two_roads import DELAYS, HORIZON, direction, next_visible
from model import REST, EAT, State, TransitionModel, imagined, inputs, persistence

MINIMUM_RESIDUAL = 2.
RATE = .72
OP_ENERGY = .000002


@dataclass
class Estimate:
    count: int = 0
    penalty: float = 0.
    mean: float = 0.
    scatter: float = 0.

    def update(self, value):
        self.count += 1
        change = value-self.mean
        self.mean += change/self.count
        self.scatter += change*(value-self.mean)
        self.penalty += RATE*(value-self.penalty)

    @property
    def uncertainty(self):
        return sqrt(self.scatter/(self.count-1)) if self.count > 1 else None


class TemporalHead:
    """Learn an energy residual indexed by observable action context and age."""

    def __init__(self):
        self.weights = {}
        self.history = deque(maxlen=max(DELAYS)+1)

    def start(self):
        self.history.clear()

    def key(self, position, tile):
        return ("cue", tile) if tile in ("amber", "blue") else ("cell", *position)

    def penalty(self, history, tick):
        return sum(self.weights.get((key, tick-start), Estimate()).penalty
                   for start, key in history if tick-start in DELAYS)

    def observe(self, tick, physical_delta, observed_delta):
        residual = physical_delta-observed_delta
        loss = residual if residual > MINIMUM_RESIDUAL else 0.
        eligible = [(key, tick-start) for start, key in self.history if tick-start in DELAYS]
        updates = []
        # If contexts overlap, do not tell the learner which one actually caused the loss.
        for key in eligible:
            estimate = self.weights.setdefault(key, Estimate())
            before = estimate.penalty
            estimate.update(loss/len(eligible))
            updates.append(dict(context=key[0], lag=key[1], before=before, after=estimate.penalty))
        return loss, updates

    def uncertainty(self, key):
        estimates = [self.weights.get((key, lag), Estimate()) for lag in DELAYS]
        if any(e.uncertainty is None for e in estimates):
            return None
        return sqrt(sum(e.uncertainty**2 for e in estimates))


def rollout(state, action, step, previous, predictor, delayed, history, uncertainty):
    """Two forced corridor continuations are the width-two special case of lookahead.

    Beyond observed tiles, wait in the model while pending consequences mature.
    """
    score = energy = damage = penalty = 0.
    for depth in range(HORIZON):
        nxt, gain, harm = imagined(state, action, predictor)
        loss = delayed(history, step+depth)
        nxt.energy -= loss
        energy += gain-loss
        damage += harm
        penalty += loss
        utility = gain-loss-.45*harm
        if nxt.energy <= 0:
            utility -= 30.
        score += .94**depth*utility
        if nxt.position != state.position:
            previous = state.position
        state = nxt
        forward = next_visible(state.local, state.position, previous)
        if len(forward) == 1:
            action = direction(state.position, forward[0])
        elif state.local[state.position][1] > 1.:
            action = EAT
        else:
            action = REST
    return dict(score=score, predicted_delta=energy, predicted_damage=damage,
                predicted_penalty=penalty, uncertainty=uncertainty)


def choose_candidates(state, actions, step, previous, head, predictor, delayed, original, exploration=0.):
    candidates = {}
    for action in actions:
        position, _ = inputs(state, action)
        key = head.key(position, state.local[position][0])
        history = (*head.history, (step, key))
        uncertainty = head.uncertainty(key)
        row = rollout(state, action, step, previous, predictor, delayed, history, uncertainty)
        row["score"] += .035*(action == original)
        # Optional uncertainty-based exploration uses observed variability only.
        if exploration:
            row["score"] += exploration*(uncertainty if uncertainty is not None else 1.)
        candidates[action] = row
    return candidates
