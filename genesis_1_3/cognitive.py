"""Bounded lifetime records and a local, typed symbolic channel."""

from collections import OrderedDict, deque
from dataclasses import dataclass
from math import exp
from types import MappingProxyType

from gateway import Query
from hypotheses import Beliefs, HYPOTHESES


FOUNDATION = MappingProxyType({
    "movement": ("Adjacent land permits movement. Water can block a move.", ("adjacency", "movement")),
    "resources": ("Food replenishes on marked patches. Eating transfers stored food into body energy.",
                  ("food", "energy")),
    "survival": ("Actions use energy. Severe depletion or damage can end a lifetime.",
                 ("energy", "survival")),
    "reproduction": ("Mature individuals can fund offspring from their own energy.",
                     ("energy", "reproduction")),
    "geography": ("Local terrain, daylight and seasonal water changes can be observed.",
                  ("season", "geography")),
    "experiment": ("The trial station has two binary controls. A trial consumes energy and returns local readings.",
                   ("action", "consequence")),
    "identity": ("Individuals have stable IDs. Events have a tick and a location.",
                 ("identity", "time")),
})


def retrieve(query, position, fruit, permitted):
    if type(query) is not Query or query.context != "foundation" or not permitted or position != fruit:
        return None
    entry = FOUNDATION.get(query.topic)
    return None if entry is None else dict(source=f"DG13/{query.topic}", classification="reference",
                                           text=entry[0], relation=entry[1])


@dataclass(frozen=True)
class Frame:
    act: str
    entity: str
    property: str
    tense: str
    negated: bool
    condition: str
    relation: str
    uncertainty: int
    symbol: int

    def __post_init__(self):
        if (self.act not in ("question","answer","statement") or self.entity not in ("station","self","peer")
                or self.property not in ("loss","stock","boundary") or self.tense not in ("past","present","future")
                or type(self.negated) is not bool or self.condition not in ("none","switch_a","switch_b","joint")
                or self.relation not in ("causes","predicts","observed") or type(self.uncertainty) is not int
                or not 0<=self.uncertainty<=3 or type(self.symbol) is not int or not 0<=self.symbol<=3):
            raise ValueError("invalid symbolic frame")

    @classmethod
    def parse(cls, fields):
        return cls(**fields)

    def render(self):
        when = "" if self.condition=="none" else f" given {self.condition}"
        polarity = "negated " if self.negated else ""
        return (f"Rendered {self.act}: {self.tense} {self.entity} {self.relation} "
                f"{polarity}{self.property}{when} [symbol {self.symbol}, uncertainty {self.uncertainty}/3]")


class Lifetime:
    def __init__(self, foundation=False):
        self.episodes = deque(maxlen=64)
        self.semantic = OrderedDict()
        self.documents = OrderedDict()
        self.beliefs = Beliefs()
        self.self_bias = [0.]*8
        self.external_bias = [0.]*4
        self.cooldown = 0
        self.feedback = None
        self.phase = -1
        if foundation:
            for topic,(text,relation) in FOUNDATION.items():
                if topic in ("geography","experiment"):
                    continue
                self.documents[topic] = dict(source=f"DG13/{topic}",text=text,relation=relation,
                                             classification="reference")

    def remember(self, label, value, tick, confidence):
        self.semantic[label] = (value,tick,min(1.,max(0.,confidence)))
        self.semantic.move_to_end(label)
        if len(self.semantic)>32:
            self.semantic.popitem(last=False)

    def confidence(self, label, tick):
        item = self.semantic.get(label)
        return 0. if item is None else item[2]*exp(-(tick-item[1])/5000.)

    def best(self):
        index = max(range(len(HYPOTHESES)),key=self.beliefs.weights.__getitem__)
        return HYPOTHESES[index],self.beliefs.weights[index]
