"""A bounded structural ensemble and decision-relevant information estimates."""

from itertools import product
from math import log2, prod

OPTIONS = tuple(product((-1, 1), repeat=2))
DOCUMENT_LABELS = tuple(product((-1,1),repeat=3))
SOURCE_RELIABILITY = .92
HYPOTHESES = tuple(product((-1, 0, 1), repeat=3))
REWARD_STOCK = .90


def outcomes(hypothesis, choice):
    a, b, stock = hypothesis
    x, y = choice
    return 4.5*(x == a)+4.*(y == b), 5.+3.5*stock*x*y


OUTCOMES = tuple(tuple(outcomes(h, c) for c in OPTIONS) for h in HYPOTHESES)


def means(weights):
    return tuple(tuple(sum(p*o[i][j] for p,o in zip(weights, OUTCOMES)) for j in range(2))
                 for i in range(len(OPTIONS)))


def variance(weights, forecast=None):
    forecast = forecast or means(weights)
    return sum(p*sum((v[0]-m[0])**2+(v[1]-m[1])**2 for v,m in zip(o,forecast))
               for p,o in zip(weights,OUTCOMES))/len(OPTIONS)


def updated(weights, likelihood):
    values = [p*q for p,q in zip(weights,likelihood)]
    total = sum(values)
    return tuple(v/total for v in values)


def document_likelihood(labels):
    return tuple(prod(SOURCE_RELIABILITY if expected==label else .5 if not expected else 1-SOURCE_RELIABILITY
                      for expected,label in zip(h,labels)) for h in HYPOTHESES)


class Beliefs:
    def __init__(self):
        self.weights = (1/len(HYPOTHESES),)*len(HYPOTHESES)
        self.anomalies = 0
        self.observations = 0
        self.meter_correct, self.meter_wrong = 2., 1.
        self.meter_history = []

    def description(self):
        best = sorted(range(len(HYPOTHESES)), key=self.weights.__getitem__, reverse=True)[:3]
        return dict(hypotheses=[dict(id=i, parameters=HYPOTHESES[i], probability=self.weights[i]) for i in best],
                    entropy=-sum(p*log2(p) for p in self.weights if p),
                    evidence_count=self.observations, anomalies=self.anomalies,
                    epistemic_variance=variance(self.weights), meter_noise_variance=.25)

    def observe(self, choice, loss, stock):
        if loss is None:
            return None
        i = OPTIONS.index(choice)
        likelihood = tuple(.98 if (abs(o[i][0]-loss)<.15 and
                                   (stock is None or abs(o[i][1]-stock)<.15)) else .02
                           for o in OUTCOMES)
        plausibility = sum(p*q for p,q in zip(self.weights,likelihood))
        if plausibility < .12:
            self.anomalies += 1
            self.weights = tuple(.35*p+.65/len(HYPOTHESES) for p in self.weights)
        self.weights = updated(self.weights,likelihood)
        self.observations += 1
        return plausibility

    def label_likelihood(self, sign, reliability):
        return tuple(reliability if h[0] == sign else .5 if not h[0] else 1-reliability
                     for h in HYPOTHESES)

    def meter_reliability(self):
        total = self.meter_correct+self.meter_wrong
        return .5+.35*max(0.,2*self.meter_correct/total-1)

    def calibrate_meter(self, sign):
        self.meter_history.append(sign)
        self.meter_history = self.meter_history[-4:]
        strength = sum(p*h[0] for p,h in zip(self.weights,HYPOTHESES))
        if abs(strength) > .65:
            if sign*strength > 0.:
                self.meter_correct += 1.
            else:
                self.meter_wrong += 1.

    @staticmethod
    def utilities(weights, energy):
        return tuple(sum(p*(-o[i][0]+REWARD_STOCK*o[i][1]-(8. if o[i][0]+5. >= energy else 0.))
                         for p,o in zip(weights,OUTCOMES)) for i in range(len(OPTIONS)))

    def physical_channels(self, i, energy):
        keys = tuple((o[i][0], o[i][1] if o[i][0]+5. < energy else None) for o in OUTCOMES)
        return [tuple(float(key == sample) for key in keys) for sample in sorted(set(keys),key=str)]

    def value(self, channels, energy, baseline, uncertainty):
        decision = resolution = 0.
        for likelihood in channels:
            mass = sum(p*q for p,q in zip(self.weights,likelihood))
            if mass < 1e-10:
                continue
            posterior = updated(self.weights,likelihood)
            decision += mass*max(self.utilities(posterior,energy))
            resolution += mass*variance(posterior)
        gain = max(0.,decision-baseline)
        improvement = max(0.,uncertainty-resolution)
        return gain, improvement, gain+.06*improvement*min(1.,gain/.2)
