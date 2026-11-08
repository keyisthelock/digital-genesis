"""Local intrinsic motivation and automatically recorded experience; no network."""
from dataclasses import dataclass, field
from collections import OrderedDict


@dataclass
class KnowledgeDrive:
    ambition: float = .8
    target: int = 5
    discoveries: int = 0
    goals_completed: int = 0
    associations: OrderedDict = field(default_factory=OrderedDict)
    pending: list = field(default_factory=list)

    def bonus(self, organism, position, risk):
        # Energy stress suppresses information seeking. No reward energy is created.
        readiness = max(0, min(1, (organism.energy-25)/60))
        novelty = position not in organism.visited
        return self.ambition * readiness * novelty / (1+4*risk)

    def register(self, organism, food, damage):
        """Called automatically after a local experience; never receives the map."""
        position = organism.position
        old_food, old_damage = self.associations.get(position, (0, 0))
        novel = position not in organism.visited
        if novel:
            self.discoveries += 1
        if food > 2 and old_food <= 2:
            self.pending.append(dict(event='food_association', position=position, observed_food=food))
        if damage > 0 and old_damage == 0:
            self.pending.append(dict(event='danger_association', position=position, damage=damage))
        self.associations[position] = (food, damage)
        self.associations.move_to_end(position)
        if len(self.associations) > 64:
            self.associations.popitem(last=False)
        if self.discoveries >= self.target:
            self.goals_completed += 1
            self.pending.append(dict(event='exploration_goal_completed',
                discoveries=self.discoveries, goals_completed=self.goals_completed))
            self.target += min(50, 5+5*self.goals_completed)

    def summary(self):
        return dict(ambition=self.ambition, next_exploration_target=self.target,
            discoveries=self.discoveries, goals_completed=self.goals_completed,
            remembered_associations=len(self.associations))
