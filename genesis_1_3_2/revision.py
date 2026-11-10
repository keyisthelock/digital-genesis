"""Bounded habituation and data-only structural revision for station experiments."""

from collections import Counter, deque
from itertools import combinations
from math import prod

from inquiry import CONCEPTS, InquiryModel, entropy, relation_value

TRIPLES = tuple(combinations(range(len(CONCEPTS)), 3))
WINDOW = 28


class Habituation:
    def __init__(self):
        self.recent = deque(maxlen=8)
        self.repetition = self.accuracy = self.progress = self.informative = self.level = 0.

    def update(self, pattern, confident, progress, informative, alternative, contradiction):
        repeated = self.recent.count(pattern) / max(1, len(self.recent))
        self.recent.append(pattern)
        self.repetition = .76 * self.repetition + .24 * repeated
        self.accuracy = .76 * self.accuracy + .24 * confident
        if progress is not None:
            self.progress = .70 * self.progress + .30 * max(0., min(1., progress))
        self.informative = .80 * self.informative + .20 * informative
        target = self.repetition * self.accuracy * (1 - self.progress) * (1 - self.informative)
        target *= .35 + .65 * min(1., max(0., alternative))
        self.level = .76 * self.level + .24 * target
        if contradiction or informative:
            self.level *= .60


def sign(context, rule):
    terms, polarity = rule
    return polarity * prod(context[i] for i in terms)


class Model(InquiryModel):
    def __init__(self, concepts):
        super().__init__(concepts)
        self.records = deque(maxlen=WINDOW)
        self.mismatches = deque(maxlen=8)
        self.validation = deque(maxlen=6)
        self.extension = None
        self.fixed_rules = tuple((terms, polarity) for terms in self.terms for polarity in (-1, 1))
        self.meter_seen = Counter()
        self.meter_checked = Counter()

    def forecast(self, context):
        if self.extension is None:
            return self.distribution(context)
        return (.035, .03, .935) if sign(context, self.extension) > 0 else (.935, .03, .035)

    def record(self, context, value, update):
        forecast = self.forecast(context)
        loss = 1. - forecast[value + 1]
        # Diffuse forecasts can be evidence of persistent inadequacy even
        # without a confident reversal on any single reading.
        mismatch = forecast[value + 1] < .45
        self.mismatches.append(mismatch)
        if update:
            self.records.append((context, value))
            self.observe(context, value, .98, "physical")
        else:
            self.validation.append((context, value))
        return loss, mismatch

    def review(self, enabled):
        """Train on recent physical observations, score a candidate on disjoint contexts."""
        if sum(self.mismatches) < 3 and self.extension is None:
            return None
        groups = {}
        for context, value in list(self.records)[-22:]:
            groups.setdefault(context, []).append(value)
        if len(groups) < 9:
            return None
        contradiction = sum(len(set(values)) > 1 for values in groups.values())
        if contradiction > len(groups) / 2:
            return {"status": "inconsistent repeats", "contexts": len(groups)}
        recent_validation = list(self.validation)[-4:]
        valid_keys = [c for c, y in recent_validation if c not in groups]
        if len(set(valid_keys)) >= 3:
            train = [(c, values[-1]) for c, values in groups.items()]
            check = list(dict(recent_validation).items())
            check = [(c, y) for c, y in check if c not in groups]
        else:
            samples = [(c, v[-1]) for c, v in groups.items()]
            train, check = samples[:-4], samples[-4:]
        # Extra terms use exactly the same supplied observations as the base.
        # The sign and triple are selected on training accuracy only.
        def accuracy(rule, records):
            self.operations += len(records) * (len(rule[0]) + 1)
            return sum(sign(c, rule) == y for c, y in records) / len(records)

        base = max(self.fixed_rules, key=lambda rule: accuracy(rule, train))
        candidates = ((terms, polarity) for terms in TRIPLES for polarity in (-1, 1))
        candidate = max(candidates, key=lambda rule: accuracy(rule, train))
        fit, old, new = accuracy(candidate, train), accuracy(base, check), accuracy(candidate, check)
        event = {"status": "unresolved", "proposed": candidate, "fit": fit, "base_validation": old,
                 "candidate_validation": new, "train_contexts": len(train), "validation_contexts": len(check)}
        if self.extension is not None and accuracy(self.extension, check) + .25 <= old:
            if enabled:
                self.extension = None
            event["status"] = "simplified" if enabled else "would simplify"
        elif fit >= .80 and new >= .75 and new - old >= .24 and self.extension != candidate:
            if enabled:
                self.extension = candidate
            event["status"] = "retained" if enabled else "shadow only"
        elif old >= .75:
            event["status"] = "familiar structure sufficient"
        return event

    def query_value(self, context, current, reliability, future):
        """Return information value and expected utility gain under observed hypotheses."""
        truth = self.predictions_for(context)
        payoff = self.predictions_for(current)
        masses, joint = [0., 0., 0.], [0., 0., 0.]
        for weight, x, y in zip(self.weights, truth, payoff):
            masses[x + 1] += weight
            joint[x + 1] += weight * y
        self.operations += 4 * len(truth) + 50
        if self.extension:
            direction = self.forecast(context)
            return max(0., entropy(direction) - .36) * max(0., 2 * reliability - 1), 0.
        error = (1 - reliability) / 2
        signal = reliability - error
        likelihood = [signal * p + error for p in masses]
        info = max(0., entropy(likelihood) - entropy((reliability, error, error)))
        total = sum(joint)
        gain = max(0., sum(abs(signal * v + error * total) for v in joint) - abs(total))
        return info, gain * future

    def strongest_rule(self):
        if self.extension:
            return self.extension
        i = max(range(1, len(self.weights)), key=self.weights.__getitem__)
        return self.fixed_rules[i - 1]

    def describe(self):
        terms, polarity = self.strongest_rule()
        return {"terms": [CONCEPTS[i] for i in terms], "sign": polarity, "extension": self.extension is not None}
