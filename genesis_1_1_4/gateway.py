"""Offline in-world information exchange. No network or file input from agents."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Query:
    topic: str
    context: str


@dataclass(frozen=True)
class Document:
    source: str
    topic: str
    context: str
    reference_runs: tuple
    summary: str


LIBRARY = (
    Document("DG-CAL-EMBER-01", "transitions", "ember",
             ((-1,-1,4.5,8.5),(-1,1,8.5,1.5),(1,-1,0.,1.5),(1,1,4.,8.5)),
             "Four observed switch, energy-loss and food-stock readings from a reference ember device."),
    Document("DG-CAL-GLASS-01", "transitions", "glass",
             ((-1,-1,4.,1.5),(-1,1,0.,8.5),(1,-1,8.5,8.5),(1,1,4.5,1.5)),
             "Four observed switch, energy-loss and food-stock readings from a reference glass device."),
    Document("DG-OPT-01", "gloss", "optics", (),
             "Two inactive sample panels had the same gloss reading."),
)


class Library:
    def __init__(self, tile, context, enabled, stale_catalog=False):
        self.tile, self.context = tile, context
        self._permit = object() if enabled else None
        self._stale = stale_catalog
        self.requests = 0

    def permit(self):
        return self._permit

    def retrieve(self, query, position, permit):
        if (self._permit is None or permit is not self._permit or position != self.tile
                or type(query) is not Query or query.topic != "transitions"
                or query.context != self.context or self.requests >= 1):
            return None
        self.requests += 1
        item = next(d for d in LIBRARY if d.source == "DG-OPT-01") if self._stale else next(
            d for d in LIBRARY if d.topic == query.topic and d.context == query.context)
        return asdict(item)


def interpret(query, document):
    """Accept scoped evidence about a reference device, not instructions or policy weights."""
    if not document or (document["topic"], document["context"]) != (query.topic, query.context):
        return None
    rows = document["reference_runs"]
    contrasts = (sum(a*loss for a,_,loss,_ in rows),sum(b*loss for _,b,loss,_ in rows),
                 sum(a*b*stock for a,b,_,stock in rows))
    return tuple(1 if x>0. else -1 if x<0. else 0 for x in contrasts)
