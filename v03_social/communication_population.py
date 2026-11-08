"""Opt-in communication genes for the existing reproductive lifecycle."""

import random

from communication import Communication, founder_genome, inherited_genome
from reproduction import ReproductiveSimulation


class CommunicationPopulation(ReproductiveSimulation):
    def __init__(self, *, communication_mutation=.08, **kwargs):
        if not 0 <= communication_mutation <= 1:
            raise ValueError('invalid communication mutation probability')
        self.communication_mutation = communication_mutation
        super().__init__(**kwargs)

    def birth(self, parent=None):
        organism = super().birth(parent)
        rng = random.Random(self.seed_value*1709 + organism.id)
        organism.signal = Communication(founder_genome(rng))
        return organism

    def child(self, parents):
        organism, sources, scalars = super().child(parents)
        rng = random.Random(self.seed_value*1717 + organism.id)
        mutation = 0. if self.freeze else self.communication_mutation
        organism.signal = Communication(inherited_genome([p.signal.genome for p in parents], rng, mutation))
        organism.reproductive_record['communication_genome'] = organism.signal.genome
        return organism, sources, scalars
