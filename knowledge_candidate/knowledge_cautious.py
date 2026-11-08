"""Next-run hypothesis: exploration uses surplus energy, not survival reserves."""
from knowledge import KnowledgeDrive


class CautiousKnowledgeDrive(KnowledgeDrive):
    def bonus(self, organism, position, risk):
        reserve = 75 if organism.mature else 55
        surplus = max(0, min(1, (organism.energy-reserve)/(100-reserve)))
        if risk > 0 or organism.pain > 0:
            return 0.0
        return super().bonus(organism, position, risk)*surplus
