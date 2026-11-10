"""A small factored belief model and a separate renderer for typed inquiries."""

from collections import Counter, deque
from dataclasses import dataclass
from itertools import combinations
from math import log2
import random


CONCEPTS = ("signal", "cycle", "action", "delay", "neighbor", "memory",
            "contradiction", "own_effort", "occlusion")
OUTCOMES = (-1, 0, 1)
CHANNELS = ("physical", "peer", "reference")
RELIABILITY = (.97, .78, .84)
COSTS = (.90, .42, .52)
OP_ENERGY = .00001


@dataclass(frozen=True)
class Question:
    target: str
    relation: str
    conditions: tuple
    intervention: tuple
    channel: str
    expected_information: float
    expected_decision_gain: float


def render(question):
    joined = " and ".join(question.conditions)
    return f"How does {joined} predict {question.target}? Check by {question.channel} observation."


def relation_value(context, terms):
    value = context[terms[0]]
    return value if len(terms) == 1 else value * context[terms[1]]


def intervention(terms):
    return tuple(int(i in terms) for i in range(len(CONCEPTS)))


def likelihood(observed, predicted, reliability):
    return reliability if observed == predicted else (1 - reliability) / 2


def development_exposure(seeds=(13100, 13101, 13102)):
    """Vocabulary grounded in observed one-control contrasts, with no paired terms."""
    records = []
    for seed in seeds:
        rng = random.Random(seed)
        for i in range(len(CONCEPTS)):
            terms = (i,)
            before = tuple(rng.choice((-1, 1)) for _ in CONCEPTS)
            after = tuple(-value if i == j else value for j, value in enumerate(before))
            sign = rng.choice((-1, 1))
            records.append((terms, before, sign * relation_value(before, terms),
                            after, sign * relation_value(after, terms)))
    return tuple(records)


def learn_concepts(records):
    return tuple(sorted({terms[0] for terms, before, a, after, b in records
                         if len(terms) == 1 and before != after and a != b}))


def entropy(distribution):
    return -sum(p * log2(p) for p in distribution if p > 0)


class InquiryModel:
    """An expansion of the bounded Dawn hypothesis scaffold by feature products.

    Each world starts with equal weights over signed atomic and binary rules and
    a null rule. Only observed outcomes update the weights. Nothing in the policy
    takes the family name, actual terms, truth, or evaluator's observations.
    """

    def __init__(self, concepts, learn=True):
        atoms = tuple((i,) for i in concepts)
        self.terms = (*atoms, *combinations(concepts, 2))
        self.probes = tuple(intervention(terms) for terms in self.terms)
        self.weights = [1 / (2 * len(self.terms) + 1)] * (2 * len(self.terms) + 1)
        self.history = deque(maxlen=32)
        self.counts = Counter()
        self.predictions = {}
        self.learn = learn
        self.operations = 0

    def predictions_for(self, context):
        if context not in self.predictions:
            if len(self.predictions) >= 128:
                self.predictions.clear()
            values = [relation_value(context, terms) for terms in self.terms]
            self.predictions[context] = (0, *(v for value in values for v in (-value, value)))
        return self.predictions[context]

    def distribution(self, context):
        masses = [0., 0., 0.]
        for w, value in zip(self.weights, self.predictions_for(context)):
            masses[value + 1] += w
        return tuple(masses)

    def observe(self, context, result, reliability, source):
        scores = self.predictions_for(context)
        likelihoods = [likelihood(result, value, reliability) for value in scores]
        evidence = sum(p * l for p, l in zip(self.weights, likelihoods))
        self.operations += 6 * len(scores)
        # Remote contradictions are discounted. Surprise from direct observation
        # reopens possibilities when a previously reliable rule may have changed.
        if self.learn:
            if evidence < .14 and source in ("peer", "reference"):
                reliability = .40
                likelihoods = [likelihood(result, value, reliability) for value in scores]
            prior = self.weights
            if evidence < .14 and source in ("physical", "decision"):
                prior = [.60 * w + .40 / len(scores) for w in prior]
            posterior = [p * l for p, l in zip(prior, likelihoods)]
            total = sum(posterior)
            self.weights = [p / total for p in posterior]
        self.history.append((context, result, source, evidence))
        return evidence

    def question(self, current, available, template, self_mismatch=0.):
        """Rank affordable tests by predictive information and decision value."""
        forecast = self.predictions_for(current)
        prior_value = abs(sum(p * x for p, x in zip(self.weights, forecast)))
        best_score, selected = 0., None
        for terms, probe in zip(self.terms, self.probes):
            masses, totals = [0., 0., 0.], [0., 0., 0.]
            for p, value, consequence in zip(self.weights, self.predictions_for(probe), forecast):
                masses[value + 1] += p
                totals[value + 1] += p * consequence
            self.operations += 4 * len(self.weights)
            for channel, reliability, cost in zip(CHANNELS, RELIABILITY, COSTS):
                noise = (1 - reliability) / 2
                signal = reliability - noise
                response = [signal * p + noise for p in masses]
                info = max(0., entropy(response) - entropy((reliability, noise, noise)))
                aggregate = sum(totals)
                gain = max(0., sum(abs(signal * t + noise * aggregate) for t in totals) - prior_value)
                repeats = self.counts[probe, channel]
                score = .36 * info + 1.8 * gain - .13 * cost - .04 * repeats
                self_related = any(CONCEPTS[i] in ("own_effort", "occlusion") for i in terms)
                if self_related:
                    score += .15 * min(1., self_mismatch) * info
                self.operations += 42
                if (channel in available and (not template or len(terms) == 1)
                        and score > best_score):
                    best_score = score
                    target = "own observation or energy error" if self_related and self_mismatch > .35 else "later outcome"
                    selected = Question(target, "predicts", tuple(CONCEPTS[i] for i in terms),
                                        probe, channel, info, gain)
        return selected
