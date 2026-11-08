"""Five deterministic v0.3.3 communication trials on individual neural organisms."""

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

from cognition import INPUTS
from communication import Communication, SILENCE, broadcast, founder_genome
from first_survival import ROOT, write_csv, write_json
from neural_survival import SurvivalBrain, fingerprint
from organism import DEFAULT_GENOME, Organism

CASES = {
    'A': ('The Last Harvest', 400),
    'B': ('The Poisoned Garden', 400),
    'C': ('The Great Flood', 400),
    'D': ('The Two-Key Refuge', 850),
    'E': ('The Unseen Partner', 400),
}
ARMS = ('intact', 'shuffled', 'blocked', 'no_learning')
CHALLENGE = 64
FLOOD = 28
STEP = 6
EARLY = 12


def make_pair(genome, seed, offset):
    pair = []
    for i in range(2):
        body = Organism(offset+i, 1, (i*2, 0), dict(DEFAULT_GENOME), max_lifespan=5000)
        body.brain = SurvivalBrain(genome, learning=False)
        body.signal = Communication(founder_genome(random.Random(seed*1009+body.id)))
        body.action_rng = random.Random(seed*1297+body.id)
        body.noise_rng = random.Random(seed*1597+body.id)
        body.token_counts = Counter()
        pair.append(body)
    return pair


def role_action(body, own, symbol, epsilon):
    features = [0.] * INPUTS
    features[:6] = [max(0., body.energy)/100, body.hunger, body.health/100, body.pain/12,
                    body.growth, min(1., body.age/3000)]
    # No route cue in these inputs. In the refuge, own_cue goes only to the
    # individual's own receiver table, never the other organism's observation.
    scores, _, _, ops = body.brain.forward(features, (0, 1), context=True)
    debit = .000002*body.brain.complexity + .00001*ops
    body.brain_cost = getattr(body, 'brain_cost', 0.) + debit
    body.brain.ops += ops
    body.energy -= debit
    route, decision = body.signal.respond(own, symbol, scores[:2], body.action_rng, epsilon)
    return route, decision, debit


def resolve(pair, case, cues, tick, index, nursery, arm, cost, distance_limit, pending, flood_grace):
    learning = arm != 'no_learning' and (nursery or case in ('C', 'E'))
    epsilon = .20 if nursery and learning else .08 if learning else 0.
    bilateral = case == 'D'
    senders = pair if bilateral else pair[:1]
    receivers = pair if bilateral else pair[1:]
    before = sum(o.energy for o in pair)
    tokens, symbols, sends, debit, delivered = {}, {}, {}, 0., 0
    arrivals = []
    for i, actor in enumerate(senders):
        other = pair[1-i]
        token, decision = actor.signal.transmit(cues[i], actor.action_rng, epsilon)
        message, fee = broadcast(actor, other, token, tick, distance_limit=distance_limit,
                                 cost=cost, latency=2)
        debit += fee
        tokens[actor.id] = token
        if nursery and message:
            actor.token_counts[token] += 1
        if message and message.arrives_at <= tick+2 and (nursery or arm != 'blocked'):
            observed = token
            if not nursery and arm == 'shuffled':
                counts = [actor.token_counts[k] for k in range(SILENCE)]
                observed = actor.noise_rng.choices(range(SILENCE), counts, k=1)[0] if sum(counts) else actor.noise_rng.randrange(SILENCE)
            symbols[other.id] = observed
            if nursery or arm != 'shuffled':
                sends[actor.id] = decision
            delivered += 1
            arrivals.append(message.arrives_at)
    routes, decisions, neural_cost = [], [], 0.
    for actor in receivers:
        own = cues[pair.index(actor)] if bilateral else 0
        route, decision, fee = role_action(actor, own, symbols.get(actor.id,SILENCE), epsilon)
        routes.append(route)
        decisions.append((actor, decision))
        neural_cost += fee
    target = (cues[0]^cues[1]) if bilateral else cues[0]
    flooded = case == 'C' and not nursery and index >= FLOOD
    if flooded:
        target ^= 1
    # Refuge route 0 presses at tick+3, route 1 at tick+4. Both presses
    # must hit the window selected by the combination of local key states.
    success = all(route == target for route in routes)
    coordinated = bilateral and routes[0] == routes[1]
    shallow_flood = flooded and index < FLOOD + flood_grace
    safe_exposure = nursery or shallow_flood
    hazard = int(not safe_exposure and not success and case in ('B','C'))
    meal = (.35 if safe_exposure else 7.) if success else 0.
    upkeep = .04 if safe_exposure else (3.6 if bilateral else 3.2)
    loss = 0. if safe_exposure or success else (4.5 if case in ('B','C','D') else 4.)
    damage = (8 if case == 'B' else 5) if hazard else 0
    discarded = 0.
    for actor in pair:
        actor.energy -= upkeep+loss
        actor.acquired += meal
        discarded += max(0., actor.energy+meal-100)
        actor.energy = min(100., actor.energy+meal)
        actor.health -= damage
        actor.age += 1
        actor.check_death()
    expected = before-debit-neural_cost+2*(meal-upkeep-loss)-discarded
    assert math.isclose(expected, sum(o.energy for o in pair), abs_tol=1e-9)
    if learning:
        # Receivers learn from their own outcome. A scout receives an outcome
        # receipt for that packet only after the receiver has acted.
        reward = 1. if success else -1.
        for actor, decision in decisions:
            pending.append((tick+STEP, actor, decision, reward))
        for actor in senders:
            if actor.id in sends:
                pending.append((tick+STEP, actor, sends[actor.id], reward))
    return dict(success=int(success), coordination=int(coordinated), hazards=hazard,
                stale_response=int(flooded and routes[0] == (target^1)),
                in_flight_change=int(flooded and index==FLOOD and bool(delivered)),
                target=target, routes='/'.join(map(str,routes)), emitted='/'.join(map(str,tokens.values())),
                received='/'.join(str(symbols.get(o.id,SILENCE)) for o in receivers),
                delivered=delivered, sent_at=tick, arrived_at=max(arrivals,default=None),
                outcome_at=tick+4, feedback_due=tick+STEP if learning else None,
                message_energy=debit, neural_energy=neural_cost, food=meal*2,
                alive=sum(o.alive for o in pair), energy=sum(o.energy for o in pair))


def apply_feedback(pending, tick):
    for due, actor, decision, reward in pending:
        assert due <= tick
        if actor.alive:
            actor.signal.learn(decision,reward)
    pending.clear()


def run_case(case, seed, arm, genome, cost, distance_limit, flood_grace=0):
    nursery_rounds = CASES[case][1]
    pairs = [make_pair(genome,seed,0)]
    if case == 'E':
        pairs.append(make_pair(genome,seed,2))
    pending = []
    nursery_totals = Counter()
    for i in range(nursery_rounds):
        tick=i*STEP
        apply_feedback(pending,tick)
        for j,pair in enumerate(pairs):
            if all(o.alive for o in pair):
                rng = random.Random(seed*4099+i*23+j)
                row = resolve(pair,case,(rng.randrange(2),rng.randrange(2)),tick,i,True,
                              arm,cost,distance_limit,pending,flood_grace)
                nursery_totals['attempts']+=1
                nursery_totals['correct']+=row['success']
                nursery_totals['message_energy']+=row['message_energy']
    apply_feedback(pending,nursery_rounds*STEP)
    nursery_survivors = sum(o.alive for pair in pairs for o in pair)
    if case == 'E' and arm != 'familiar':
        a,b=pairs
        pairs=[[a[0],b[1]],[b[0],a[1]]]
        for pair in pairs:
            for i,body in enumerate(pair):
                body.position=(i*2,0)
    traces=[]
    recovery=None
    recent=[]
    for i in range(CHALLENGE):
        tick=(nursery_rounds+i)*STEP
        apply_feedback(pending,tick)
        successes=[]
        for j,pair in enumerate(pairs):
            if not all(o.alive for o in pair):
                continue
            rng=random.Random(seed*104729+i*23+j)
            cue=(rng.randrange(2),rng.randrange(2))
            row=resolve(pair,case,cue,tick,i,False,arm,cost,distance_limit,pending,flood_grace)
            traces.append(dict(case=case,seed=seed,arm=arm,round=i+1,pair=j,
                               sender=pair[0].id,receiver=pair[1].id,cue=cue[0],own_key=cue[1] if case=='D' else None,**row))
            successes.append(row['success'])
        if case=='C' and i>=FLOOD and successes:
            recent.extend(successes)
            if recovery is None and len(recent)>=8 and sum(recent[-8:])>=7:
                recovery=i-FLOOD+1
    apply_feedback(pending,(nursery_rounds+CHALLENGE)*STEP)
    final_pairs=sum(all(o.alive for o in pair) and any(r['pair']==j and r['round']==CHALLENGE for r in traces)
                    for j,pair in enumerate(pairs))
    early=[r for r in traces if r['round']<=EARLY]
    pre=[r for r in traces if r['round']<=FLOOD]
    post=[r for r in traces if r['round']>FLOOD]
    stats=dict(case=case,seed=seed,arm=arm,pairs=len(pairs),surviving_pairs=final_pairs,
               surviving_organisms=sum(o.alive for pair in pairs for o in pair),
               nursery_survivors=nursery_survivors,nursery_attempts=nursery_totals['attempts'],
               nursery_successes=nursery_totals['correct'],nursery_message_energy=nursery_totals['message_energy'],
               attempts=len(traces),successes=sum(r['success'] for r in traces),
               early_attempts=len(early),early_successes=sum(r['success'] for r in early),
               pre_attempts=len(pre),pre_successes=sum(r['success'] for r in pre),
               post_attempts=len(post),post_successes=sum(r['success'] for r in post),
               hazard_encounters=sum(r['hazards'] for r in traces),
               stale_responses=sum(r['stale_response'] for r in traces),
               in_flight_changes=sum(r['in_flight_change'] for r in traces),
               flood_recovery_rounds=recovery,coordination=sum(r['coordination'] for r in traces),
               packets_delivered=sum(r['delivered'] for r in traces),
               message_energy=sum(r['message_energy'] for r in traces),
               brain_energy=sum(o.brain_cost for pair in pairs for o in pair if hasattr(o,'brain_cost')),
               brain_ops=sum(o.brain.ops for pair in pairs for o in pair),
               lifetime_updates=sum(o.signal.updates for pair in pairs for o in pair))
    weights=[dict(id=o.id, inherited=o.signal.genome, send=o.signal.send, receive=o.signal.receive,
                  updates=o.signal.updates) for pair in pairs for o in pair]
    return stats,traces,weights


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seeds',type=int,choices=range(1,101),default=12)
    parser.add_argument('--modules',type=int,choices=(32,67),default=32)
    parser.add_argument('--case',choices=tuple(CASES),help='Run only the selected environment')
    parser.add_argument('--seed-start',type=int,default=23300)
    parser.add_argument('--flood-grace',type=int,choices=range(CHALLENGE-FLOOD),default=0)
    parser.add_argument('--send-cost',type=float,default=.035)
    parser.add_argument('--range',dest='distance_limit',type=int,default=2)
    args=parser.parse_args()
    if not math.isfinite(args.send_cost) or args.send_cost<0 or args.distance_limit<0:
        parser.error('send cost and transmission range must be finite and nonnegative')
    out=args.output
    out.mkdir(parents=True)
    source=ROOT/'experiments/first_survival_v031'/f'trained_{args.modules}.json'
    genome=json.loads(source.read_text())
    seeds=list(range(args.seed_start,args.seed_start+args.seeds))
    cases = (args.case,) if args.case else tuple(CASES)
    write_json(out/'protocol.json',dict(cases={case: CASES[case] for case in cases},seeds=seeds,modules=args.modules,
        neural_genome_sha=fingerprint(genome),arms=ARMS,case_e_control='familiar intact partners',
        symbols=4,send_cost=args.send_cost,distance=args.distance_limit,arrival_delay=2,
        outcome_delay=4,feedback_delay=STEP,challenge_rounds=CHALLENGE,flood_after_round=FLOOD,
        flood_grace=args.flood_grace,
        reward='local route outcome, +1 or -1; senders credited after delivered packet is used',
        neural='existing frozen neural forward scores + individual receiver values',
        ecology='controlled two-organism arenas; no reproduction during comparison',
        metric='a pair survives when both members complete the full challenge'))
    results=[]
    all_weights={}
    with (out/'decisions.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=None
        for case in cases:
            for seed in seeds:
                for arm in ARMS+ (('familiar',) if case=='E' else ()):
                    row,traces,weights=run_case(case,seed,arm,genome,args.send_cost,args.distance_limit,args.flood_grace)
                    results.append(row)
                    if traces:
                        if writer is None:
                            writer=csv.DictWriter(stream,fieldnames=list(traces[0]))
                            writer.writeheader()
                        writer.writerows(traces)
                    all_weights[f'{case}_{seed}_{arm}']=weights
            write_csv(out/'results.csv',results)
            print(f'Case {case} complete',flush=True)
    write_json(out/'weights.json',all_weights)


if __name__=='__main__':
    main()
