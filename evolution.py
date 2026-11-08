"""Deterministic selection, generation lifecycle, and streamed experiment logs."""
import csv
import json
import random
import math
from pathlib import Path
from world import World
from organism import Organism, WeightedPolicy, DEFAULT_GENOME

FIELDS = 'generation population deaths average_fitness best_fitness average_lifespan exploration_score fruit_discoveries'.split()


class Simulation:
    def __init__(self, population=30, ticks=400, seed=42, mutation_rate=.2,
                 mutation_strength=.25, output='results', max_lifespan=600,
                 lifetime=False, baseline=False, resource_fraction=1.0,
                 max_population=100, maturity_age=100, reproduction_cost=40,
                 birth_energy=30, reproduction_threshold=85, birth_cooldown=60,
                 terrain=None):
        if (population < 1 or ticks < 1 or max_lifespan < 1 or max_population < population
                or maturity_age < 0 or birth_cooldown < 1
                or not 0 < birth_energy <= reproduction_cost < reproduction_threshold <= 100
                or not 0 <= mutation_rate <= 1
                or not math.isfinite(mutation_strength) or mutation_strength < 0):
            raise ValueError('invalid population, lifespan or reproduction settings')
        self.rng = random.Random(seed)
        self.size, self.duration = population, ticks
        self.rate, self.strength = mutation_rate, mutation_strength
        self.max_lifespan = max_lifespan
        self.lifetime, self.baseline = lifetime, baseline
        self.max_population, self.maturity_age = max_population, maturity_age
        self.reproduction_cost, self.birth_energy = reproduction_cost, birth_energy
        self.reproduction_threshold, self.birth_cooldown = reproduction_threshold, birth_cooldown
        self.total_births = self.organism_ticks = self.starvations = 0
        self.archived_fitness = self.archived_food = 0.0
        self.world = World.load(terrain, self.rng) if terrain else World(self.rng)
        self.world.scarcity(resource_fraction)
        self.policy = WeightedPolicy()
        self.generation, self.tick, self.next_id = 1, 0, 1
        self.total_deaths = self.discoveries = 0
        self.generation_discoveries = 0
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.csv = (self.output/'generations.csv').open('w', newline='', encoding='utf-8')
        self.writer = csv.DictWriter(self.csv, fieldnames=FIELDS)
        self.writer.writeheader()
        self.records = (self.output/'ancestry.jsonl').open('w', encoding='utf-8')
        self.events = (self.output/'fruit_events.jsonl').open('w', encoding='utf-8')
        self.births = (self.output/'births.jsonl').open('w', encoding='utf-8')
        self.closed = False
        (self.output/'config.json').write_text(json.dumps(dict(population=population,
            ticks=ticks, seed=seed, mutation_rate=mutation_rate,
            mutation_strength=mutation_strength, max_lifespan=max_lifespan,
            lifetime=lifetime, baseline=baseline, resource_fraction=resource_fraction,
            max_population=max_population, maturity_age=maturity_age,
            reproduction_cost=reproduction_cost, birth_energy=birth_energy,
            reproduction_threshold=reproduction_threshold, birth_cooldown=birth_cooldown,
            terrain=str(terrain) if terrain else None), indent=2))
        self.organisms = [self.birth() for _ in range(population)]

    def birth(self, parent=None):
        genome = dict(parent.genome if parent and not self.baseline else DEFAULT_GENOME)
        if parent and not self.baseline:
            for key in genome:
                if self.rng.random() < self.rate:
                    genome[key] = max(.01, min(6, genome[key] + self.rng.gauss(0, self.strength)))
        o = Organism(self.next_id, self.generation, self.rng.choice(self.world.land),
                     genome, parent.id if parent else None, self.max_lifespan)
        self.next_id += 1
        if self.lifetime:
            o.maturity_age = self.maturity_age
            if parent:
                o.generation = parent.generation+1
                o.position = parent.position
                o.energy = self.birth_energy
        return o

    def step(self):
        self.world.advance()
        self.tick += 1
        for o in self.organisms:
            was_alive = o.alive
            if was_alive:
                self.organism_ticks += 1
            for event in o.step(self.world, self.rng, self.policy):
                self.events.write(json.dumps(dict(generation=self.generation, tick=self.tick,
                    organism_id=o.id, event=event))+'\n')
                if event == 'discovery':
                    self.discoveries += 1
                    self.generation_discoveries += 1
            if was_alive and not o.alive:
                self.total_deaths += 1
                self.starvations += o.death_cause == 'starvation'
        if self.lifetime:
            survivors = []
            for o in self.organisms:
                if o.alive:
                    survivors.append(o)
                else:
                    self.record(o)
                    self.archived_fitness += o.fitness
                    self.archived_food += o.acquired
            self.organisms = survivors
            newborns = []
            # Rotate opportunities each tick to avoid permanently favoring low IDs.
            candidates = survivors[:]
            self.rng.shuffle(candidates)
            for parent in candidates:
                if len(survivors)+len(newborns) >= self.max_population:
                    break
                if (parent.mature and parent.energy >= self.reproduction_threshold
                        and parent.age-parent.last_birth_age >= self.birth_cooldown):
                    parent.energy -= self.reproduction_cost
                    parent.last_birth_age = parent.age
                    parent.offspring += 1
                    child = self.birth(parent)
                    newborns.append(child)
                    self.total_births += 1
                    self.births.write(json.dumps(dict(tick=self.world.tick, parent_id=parent.id,
                        id=child.id, generation=child.generation, genome=child.genome))+'\n')
            self.organisms.extend(newborns)
        return self.tick >= self.duration

    def record(self, o):
        self.records.write(json.dumps(dict(id=o.id, parent_id=o.parent_id,
            generation=o.generation, genome=o.genome, fitness=o.fitness,
            age=o.age, alive_at_boundary=o.alive, offspring=o.offspring,
            death_cause=o.death_cause, world_tick=self.world.tick))+'\n')

    def metrics(self):
        living = [o for o in self.organisms if o.alive]
        food = self.archived_food + sum(o.acquired for o in living)
        fitness = self.archived_fitness + sum(o.fitness for o in living)
        return dict(ticks=self.world.tick, living=len(living), deaths=self.total_deaths,
            starvation_deaths=self.starvations, births=self.total_births,
            founder_survival=sum(o.parent_id is None for o in living)/self.size,
            survival_fraction=len(living)/(self.size+self.total_births),
            average_observed_lifespan=self.organism_ticks/(self.size+self.total_births),
            organism_ticks=self.organism_ticks, food_consumed=food,
            food_efficiency=self.organism_ticks/food if food > 0 else None,
            average_fitness=fitness/(self.size+self.total_births))

    def finish_generation(self, reproduce=True):
        cohort = self.organisms
        if self.lifetime:
            m = self.metrics()
            row = dict(generation=self.generation, population=len(cohort),
                deaths=self.total_deaths, average_fitness=m['average_fitness'],
                best_fitness=max((o.fitness for o in cohort), default=0),
                average_lifespan=sum(o.age for o in cohort)/max(1, len(cohort)),
                exploration_score=sum(len(o.visited) for o in cohort)/max(1,len(cohort)),
                fruit_discoveries=self.generation_discoveries)
            self.writer.writerow(row)
            for o in cohort:
                self.record(o)
            if cohort:
                champion = max(cohort, key=lambda o: o.fitness)
                (self.output/'selected_genomes.json').write_text(json.dumps(dict(
                    generation=self.generation, id=champion.id, genome=champion.genome), indent=2))
            self.flush()
            if reproduce:
                self.generation += 1
                self.tick = self.generation_discoveries = 0
            return row
        row = dict(generation=self.generation, population=len(cohort),
            deaths=sum(not o.alive for o in cohort),
            average_fitness=sum(o.fitness for o in cohort)/len(cohort),
            best_fitness=max(o.fitness for o in cohort),
            average_lifespan=sum(o.age for o in cohort)/len(cohort),
            exploration_score=sum(len(o.visited) for o in cohort)/len(cohort),
            fruit_discoveries=self.generation_discoveries)
        self.writer.writerow(row)
        self.csv.flush()
        for o in cohort:
            self.records.write(json.dumps(dict(id=o.id, parent_id=o.parent_id,
                generation=o.generation, genome=o.genome, fitness=o.fitness,
                age=o.age, alive_at_boundary=o.alive))+'\n')
        self.records.flush()
        self.events.flush()
        champion = max(cohort, key=lambda o: o.fitness)
        (self.output/'selected_genomes.json').write_text(json.dumps(dict(
            generation=self.generation, id=champion.id, genome=champion.genome), indent=2))
        if reproduce:
            # A non-overlapping cohort is replaced; deceased parents contribute only
            # archived genomes. No organism instance or ID is ever revived.
            parents = self.rng.choices(cohort, weights=None if self.baseline else [1+o.fitness for o in cohort], k=self.size)
            self.generation += 1
            self.tick = self.generation_discoveries = 0
            self.organisms = [self.birth(p) for p in parents]
        return row

    def flush(self):
        for stream in (self.csv, self.records, self.events, self.births):
            stream.flush()

    def close(self):
        if not self.closed:
            self.csv.close()
            self.records.close()
            self.events.close()
            self.births.close()
            self.closed = True
