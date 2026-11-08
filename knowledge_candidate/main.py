"""Digital Genesis v0.2: CPU-only artificial life."""
import argparse
import sys
import json
import time
from pathlib import Path

# Optional project-local dependency installation (keeps system Python untouched).
local_packages = Path(__file__).resolve().parent / '.packages'
if not local_packages.is_dir():
    local_packages = Path(__file__).resolve().parent.parent / '.packages'
if local_packages.is_dir():
    sys.path.insert(0, str(local_packages))
from evolution import Simulation


class Camera:
    def __init__(self, width, height, viewport=(880, 640)):
        self.width, self.height = width, height
        self.viewport = viewport
        self.minimum = min(viewport[0]/width, viewport[1]/height)
        self.scale = self.minimum
        self.x = (viewport[0]-width*self.scale)/2
        self.y = (viewport[1]-height*self.scale)/2

    def tile_at(self, x, y):
        import math
        return math.floor((x-self.x)/self.scale), math.floor((y-self.y)/self.scale)

    def zoom(self, factor, anchor):
        before = self.scale
        self.scale = max(self.minimum, min(self.minimum*8, before*factor))
        self.x = anchor[0]-(anchor[0]-self.x)*self.scale/before
        self.y = anchor[1]-(anchor[1]-self.y)*self.scale/before
        self.clamp()

    def clamp(self):
        for axis, size, view in (('x', self.width, self.viewport[0]), ('y', self.height, self.viewport[1])):
            extent = size*self.scale
            setattr(self, axis, (view-extent)/2 if extent <= view else min(0, max(view-extent, getattr(self, axis))))


def visual(sim, generations, speed, follow=None):
    try:
        import pygame as pg
    except ImportError:
        raise SystemExit('Visual mode requires pygame: python -m pip install -r requirements.txt')
    pg.init()
    screen = pg.display.set_mode((1160, 640))
    pg.display.set_caption('Digital Genesis — 2D Earth — checkpoint replay of overnight seed 0' if follow else 'Digital Genesis — The First Amoeba')
    font = pg.font.SysFont('consolas', 15)
    clock = pg.time.Clock()
    camera = Camera(sim.world.width, sim.world.height)
    dragging = False
    paused, running, selected, finished = False, True, None, False
    accumulator = 0.0
    target_tick, next_refresh = 0, 0
    colors = dict(land=(42, 82, 53), water=(30, 79, 125),
                  tree=(27, 59, 36), hazard=(120, 48, 48), fruit=(188, 94, 245))
    while running:
        dt = min(clock.tick(30)/1000, .1)
        if follow and time.monotonic() >= next_refresh:
            try:
                target_tick = json.loads((Path(follow)/'experiment.json').read_text())['completed_ticks']
            except (OSError, ValueError, KeyError):
                pass
            next_refresh = time.monotonic()+1
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    running = False
                elif event.key == pg.K_SPACE:
                    paused = not paused
                elif event.key in (pg.K_EQUALS, pg.K_PLUS, pg.K_KP_PLUS):
                    speed = min(1000, speed*2)
                elif event.key in (pg.K_MINUS, pg.K_KP_MINUS):
                    speed = max(1, speed/2)
                elif event.key == pg.K_HOME:
                    camera = Camera(sim.world.width, sim.world.height)
            elif event.type == pg.MOUSEWHEEL:
                mouse = pg.mouse.get_pos()
                if mouse[0] < camera.viewport[0]:
                    camera.zoom(1.25**event.y, mouse)
            elif event.type == pg.MOUSEBUTTONDOWN:
                x, y = event.pos
                if x < camera.viewport[0]:
                    if event.button == 1:
                        selected = next((o for o in sim.organisms if o.alive and o.position == camera.tile_at(x, y)), None)
                    elif event.button in (2, 3):
                        dragging = True
            elif event.type == pg.MOUSEBUTTONUP and event.button in (2, 3):
                dragging = False
            elif event.type == pg.MOUSEMOTION and dragging:
                camera.x += event.rel[0]
                camera.y += event.rel[1]
                camera.clamp()
        if not paused and not finished:
            accumulator += dt*speed
            while accumulator >= 1:
                if follow and sim.world.tick >= target_tick:
                    accumulator = 0
                    break
                accumulator -= 1
                if sim.step():
                    finished = sim.generation >= generations
                    sim.finish_generation(reproduce=not finished)
                    selected = None
                    if finished:
                        break
        screen.fill((17, 21, 29))
        screen.set_clip((0, 0, *camera.viewport))
        light = .45 + .55*sim.world.daylight
        size = camera.scale
        for (x, y), tile in sim.world.tiles.items():
            color = tuple(int(c*light) for c in colors[tile])
            px, py = camera.x+x*size, camera.y+y*size
            if px+size < 0 or py+size < 0 or px > camera.viewport[0] or py > camera.viewport[1]:
                continue
            pg.draw.rect(screen, color, (round(px), round(py), round(px+size)-round(px), round(py+size)-round(py)))
            if sim.world.food.get((x, y), 0) > 5:
                pg.draw.circle(screen, (142, 190, 66), (round(px+size/2), round(py+size/2)), max(1, round(size*.12)))
        fx, fy = sim.world.fruit
        cx, cy = camera.x+(fx+.5)*size, camera.y+(fy+.5)*size
        r = size*.43
        pg.draw.polygon(screen, (230, 155, 255), [(cx,cy-r),(cx+r,cy),(cx,cy+r),(cx-r,cy)], 2)
        living = [o for o in sim.organisms if o.alive]
        for o in living:
            x, y = o.position
            center = round(camera.x+(x+.5)*size), round(camera.y+(y+.5)*size)
            pg.draw.circle(screen, (250, 224, 130) if o is selected else (211, 231, 225), center, max(2, round(size*.3*o.growth)))
        screen.set_clip(None)
        lines = ['DIGITAL GENESIS', f'Generation {sim.generation}', f'Tick {sim.tick}/{sim.duration}',
            f'Living {len(living)}', f'Deaths {sim.total_deaths}',
            f'Avg energy {sum(o.energy for o in living)/max(1,len(living)):.1f}',
            f'Best fit {max((o.fitness for o in sim.organisms), default=0):.1f}',
            f'Avg fit {sum(o.fitness for o in sim.organisms)/max(1,len(sim.organisms)):.1f}',
            f'Food {sum(sim.world.food.values()):.0f}', f'Discoveries {sim.discoveries}',
            f'Speed {speed:g} ticks/s', 'COMPLETE' if finished else 'PAUSED' if paused else 'RUNNING',
            f'Zoom {camera.scale/camera.minimum:.1f}x', 'Wheel: zoom', 'Right drag: pan', 'Home: whole Earth',
            'SPACE pause | +/- speed', 'ESC exit | Click amoeba']
        if follow:
            lines[2] = f'World {sim.world.tick}/{target_tick}'
            lines[11] = 'CHECKPOINT REPLAY'
        if selected:
            o = selected
            lines += ['', f'ID {o.id} / Gen {o.generation}', f'Parent {o.parent_id}',
                f'Energy {o.energy:.1f}', f'Health {o.health:.1f}', f'Age {o.age}/{o.max_lifespan}',
                f'Hunger {o.hunger:.2f}', f'Pain {o.pain:.1f}', f'Fear {o.fear:.2f}']
            lines += [f'{k}: {v:.2f}' for k, v in o.genome.items()]
            lines += [f'Growth {o.growth:.0%} / Kids {o.offspring}']
            if o.knowledge is not None:
                lines += [f'Goals {o.knowledge.goals_completed}', f'New places {o.knowledge.discoveries}']
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, (215, 224, 235)), (892, 10+i*15))
        pg.display.flip()
    pg.quit()
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--generations', type=int, default=20)
    parser.add_argument('--population', type=int, default=30)
    parser.add_argument('--ticks-per-generation', type=int, default=400)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--mutation-rate', type=float, default=.2)
    parser.add_argument('--mutation-strength', type=float, default=.25)
    parser.add_argument('--max-lifespan', type=int, default=600)
    parser.add_argument('--speed', type=float, default=30)
    parser.add_argument('--output', default='results')
    parser.add_argument('--legacy-generations', action='store_true', help='Use v0.1 cohort replacement')
    parser.add_argument('--baseline', action='store_true', help='Fixed genomes, no fitness selection or mutation')
    parser.add_argument('--resource-fraction', type=float, default=.35, help='0=no food, 1=original abundance')
    parser.add_argument('--max-population', type=int, default=100)
    parser.add_argument('--maturity-age', type=int, default=100)
    parser.add_argument('--terrain', help='Saved terrain JSON')
    parser.add_argument('--knowledge', action='store_true')
    parser.add_argument('--follow-experiment', help='Read-only deterministic visualization of overnight seed 0 checkpoints')
    parser.add_argument('--follow-treatment', default='evolving', choices=('evolving', 'cautious_knowledge', 'evolving_without_knowledge', 'baseline'))
    args = parser.parse_args()
    if min(args.generations, args.population, args.ticks_per_generation, args.max_lifespan) < 1:
        parser.error('population, generations, ticks and lifespan must be positive')
    import math
    if not all(math.isfinite(v) for v in (args.mutation_rate, args.mutation_strength, args.speed)) or not 0 <= args.mutation_rate <= 1 or args.mutation_strength < 0 or args.speed <= 0:
        parser.error('invalid mutation parameters or speed')
    if not 0 <= args.resource_fraction <= 1 or args.max_population < args.population or args.maturity_age < 0:
        parser.error('invalid resource fraction, population cap or maturity age')
    restart = True
    while restart:
        if args.follow_experiment:
            configuration = json.loads((Path(args.follow_experiment)/f'seed_0_{args.follow_treatment}'/'config.json').read_text())
            configuration['output'] = args.output
            sim = Simulation(**configuration)
        else:
            sim = Simulation(args.population, args.ticks_per_generation, args.seed,
                         args.mutation_rate, args.mutation_strength, args.output, args.max_lifespan,
                         lifetime=not args.legacy_generations, baseline=args.baseline,
                         resource_fraction=args.resource_fraction, max_population=args.max_population,
                         maturity_age=args.maturity_age, terrain=args.terrain, knowledge=args.knowledge)
        try:
            if args.headless:
                for g in range(args.generations):
                    for _ in range(args.ticks_per_generation):
                        sim.step()
                    print(sim.finish_generation(reproduce=g+1 < args.generations))
                restart = False
            else:
                restart = visual(sim, args.generations, args.speed, follow=args.follow_experiment)
        finally:
            sim.close()


if __name__ == '__main__':
    main()
