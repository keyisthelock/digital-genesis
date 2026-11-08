"""Visual or headless v0.3 prototype; no networking or model dependencies."""
import argparse,json
from pathlib import Path
from datetime import datetime,timezone
from social_sim import SocialSimulation,TREATMENTS
from reproduction import MODES, ReproductiveSimulation
from main import visual

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--headless',action='store_true');p.add_argument('--modules',type=int,choices=(8,16,32,67),default=67)
    p.add_argument('--treatment',choices=TREATMENTS,default='D_social_evolving')
    p.add_argument('--ticks',type=int,default=1500);p.add_argument('--population',type=int,default=12)
    p.add_argument('--seed',type=int,default=0);p.add_argument('--speed',type=float,default=20)
    p.add_argument('--output',type=Path,default=Path(__file__).parent/'results'/('visual_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')))
    p.add_argument('--brain-parameter-cost',type=float,default=.000002);p.add_argument('--brain-op-cost',type=float,default=.00001)
    p.add_argument('--no-learning',action='store_true');p.add_argument('--shuffle-social',action='store_true')
    p.add_argument('--reproductive-mode',choices=MODES,help='Enable v0.3.2 with the selected reproduction mode')
    p.add_argument('--type-a-probability',type=float,default=.5)
    p.add_argument('--interaction-distance',type=int,default=2)
    p.add_argument('--trained-neural',type=Path,help='Optional saved founder neural genome JSON')
    p.add_argument('--quality',choices=('low','medium','high'),default='medium')
    p.add_argument('--no-animations',action='store_true');p.add_argument('--paused',action='store_true')
    p.add_argument('--ui-benchmark-seconds',type=float,default=0,help='Measure the visible UI, then exit')
    args=p.parse_args()
    if args.output.exists() and any(args.output.iterdir()):p.error('choose an empty output directory')
    if not 0 <= args.type_a_probability <= 1 or args.interaction_distance < 0:
        p.error('type probability must be 0 to 1 and interaction distance must be nonnegative')
    if args.reproductive_mode and args.treatment not in ('D_social_evolving', 'A_rule'):
        p.error('v0.3.2 requires the evolving neural or rule treatment')
    gene=json.loads(args.trained_neural.read_text()) if args.trained_neural else None
    if gene and (args.treatment=='A_rule' or len(gene['modules'])!=args.modules):
        p.error('saved genome must match the selected neural module count')
    options=dict(neural_pool=[gene] if gene else None)
    if args.reproductive_mode:
        options.update(reproductive_mode=args.reproductive_mode,
                       type_a_probability=args.type_a_probability,
                       interaction_distance=args.interaction_distance)
    simulation=ReproductiveSimulation if args.reproductive_mode else SocialSimulation
    sim=simulation(population=args.population,ticks=args.ticks,seed=args.seed,output=args.output,
        max_lifespan=3000,max_population=max(24,args.population),maturity_age=100,resource_fraction=.35,
        modules=args.modules,treatment=args.treatment,shuffled=args.shuffle_social,learning=not args.no_learning,
        brain_energy_parameter=args.brain_parameter_cost,brain_energy_op=args.brain_op_cost,**options)
    (args.output/'v03_config.json').write_text(json.dumps(vars(args),default=str,indent=2))
    try:
        if args.headless:
            for _ in range(args.ticks):
                if sim.step():break
            sim.finish_generation(reproduce=False)
            print(json.dumps(dict(**sim.metrics(),cognition=sim.extra_metrics()),indent=2))
        else:visual(sim,1,args.speed,quality=args.quality,animate=not args.no_animations,
                    benchmark_seconds=args.ui_benchmark_seconds,paused=args.paused)
    finally:sim.close()

if __name__=='__main__':main()
