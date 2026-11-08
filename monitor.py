"""Native, read-only display of the actual overnight comparison."""
import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import main  # Makes the existing project-local Pygame installation available.
import pygame as pg


def load(folder):
    manifest = json.loads((folder/'experiment.json').read_text())
    with (folder/'comparison.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    return manifest, rows


def main_monitor():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', default='results/v02_overnight')
    args = parser.parse_args()
    folder = Path(args.results)
    pg.init()
    screen = pg.display.set_mode((1160, 720))
    pg.display.set_caption('Digital Genesis v0.2 — LIVE Overnight Comparison')
    font = pg.font.SysFont('consolas', 17)
    title = pg.font.SysFont('consolas', 25, bold=True)
    clock = pg.time.Clock()
    manifest, rows, error = {}, [], ''
    next_read = 0
    fixed_view = False
    comparison_index = 0
    running = True
    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                running = False
            elif event.type == pg.KEYDOWN and event.key == pg.K_TAB:
                fixed_view = not fixed_view
                comparison_index += 1
        if time.monotonic() >= next_read:
            try:
                manifest, rows = load(folder)
                error = ''
            except (OSError, ValueError) as exc:
                error = 'Waiting for a complete checkpoint: '+str(exc)[:85]
            next_read = time.monotonic()+1
        screen.fill((16, 23, 31))

        def label(text, x, y, color=(214, 226, 235), big=False):
            screen.blit((title if big else font).render(text, True, color), (x, y))

        label('DIGITAL GENESIS v0.2 | OVERNIGHT COMPARISON', 25, 20, big=True)
        status = manifest.get('status', 'loading').upper()
        knowledge = manifest.get('parameters', {}).get('knowledge', False)
        cautious = manifest.get('parameters', {}).get('cautious', False)
        label(f'{status}   |   10 seeds / {4 if cautious else 3 if knowledge else 2} treatments   |   Same terrain   |   Fruit OFFLINE', 25, 63,
            (245, 125, 125) if status == 'FAILED' else (107, 216, 166))
        started = manifest.get('started_utc')
        elapsed = (datetime.now(timezone.utc)-datetime.fromisoformat(started.replace('Z', '+00:00'))).total_seconds() if started else 0
        elapsed = manifest.get('elapsed_seconds', elapsed)
        hours = manifest.get('parameters', {}).get('hours', 6)
        label(f'Elapsed {int(elapsed//3600):02}:{int(elapsed%3600//60):02}:{int(elapsed%60):02} / {hours:g} hours', 25, 94)
        age = time.time()-(folder/'comparison.csv').stat().st_mtime if (folder/'comparison.csv').exists() else 0
        ticks = min((int(r['ticks']) for r in rows), default=0)
        duty = manifest.get('parameters', {}).get('duty', .15)
        label(f'Checkpoint tick {ticks:,}   |   Updated {int(age)}s ago   |   CPU duty target {duty:.0%}', 25, 122)
        ordinary = knowledge and not fixed_view
        left_mode, right_mode = 'evolving', 'evolving_without_knowledge' if ordinary else 'baseline'
        if cautious:
            choices = [('cautious_knowledge', 'evolving'), ('cautious_knowledge', 'evolving_without_knowledge'),
                       ('cautious_knowledge', 'baseline'), ('evolving', 'baseline')]
            left_mode, right_mode = choices[comparison_index % len(choices)]
        names = dict(cautious_knowledge='CAUTIOUS KNOWLEDGE', evolving='ORIGINAL KNOWLEDGE' if knowledge else 'EVOLVING',
                     evolving_without_knowledge='EVOLUTION WITHOUT DRIVE', baseline='FIXED GENOME BASELINE')
        label(names[left_mode], 130, 172, (110, 221, 172), True)
        label(names[right_mode], 635, 172, (113, 180, 249), True)
        label('Seed     Alive  Births Starved Fitness Food-eff      Alive  Births Starved Fitness Food-eff', 25, 211)
        by_key = {(int(r['seed']), r['treatment']): r for r in rows}
        for seed in range(10):
            y = 247+seed*30
            label(f'{seed:>2}', 35, y)
            for mode, x in ((left_mode, 130), (right_mode, 635)):
                r = by_key.get((seed, mode))
                if r:
                    eff = f"{float(r['food_efficiency']):.2f}" if r['food_efficiency'] else '--'
                    label(f"{r['living']:>5} {r['births']:>6} {r['starvation_deaths']:>7} {float(r['average_fitness']):>7.1f} {eff:>8}", x, y)
        label('Food-eff = organism-ticks per food unit consumed. Fitness alone is not proof of adaptation.', 25, 567)
        if status == 'RUNNING' and age > 300:
            label('WARNING: checkpoint is stale; review the runner. The last data is retained.', 25, 600, (248, 180, 100))
        else:
            label('Live measured results from the existing experiment; refreshes once per second.', 25, 600)
        detail = manifest.get('error') if status == 'FAILED' else manifest.get('reason', 'still running')
        if status == 'RECOVERING':
            detail = f"Reconstructing tick {ticks:,} / {manifest.get('resume_tick', 0):,}; new progress awaits verification"
        label(error or str(detail)[:105], 25, 631)
        label('TAB switches control group. Closing this window does not stop the experiment.', 25, 665, (148, 168, 184))
        pg.display.flip()
        clock.tick(15)
    pg.quit()


if __name__ == '__main__':
    main_monitor()
