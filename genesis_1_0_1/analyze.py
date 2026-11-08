"""Derive comparable accuracy and information summaries from saved CSVs."""

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

from ecosystem import CHANNELS, SILENCE
from first_survival import write_csv


def read(path):
    with path.open(newline='',encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def information(pairs):
    """Empirical mutual information in bits, with finite-sample bias."""
    joint=Counter(pairs)
    n=sum(joint.values())
    if not n:
        return None
    left,right=Counter(),Counter()
    for (marker,token),count in joint.items():
        left[marker]+=count
        right[token]+=count
    return sum(count/n*math.log2(count*n/(left[m]*right[t]))
               for (m,t),count in joint.items())


def summarize(root):
    groups=defaultdict(list)
    for row in read(root/'results.csv'):
        groups[row['arm']].append(row)
    result=[]
    for arm in CHANNELS:
        if arm not in groups:
            continue
        for row in groups[arm]:
            seed=row['seed']
            events=read(root/f'{seed}_{arm}'/'interactions.csv')
            for phase,scout,receiver in (('establish','resident','resident'),
                ('contact','resident','foster'),('after','resident','foster'),('after','foster','foster')):
                selected=[r for r in events if (r['phase'],r['scout_origin'],r['receiver_origin'])
                          ==(phase,scout,receiver)]
                delivered=[r for r in selected if int(r['symbol_received'])!=SILENCE]
                unrelated=[r for r in delivered if r['unrelated']=='1']
                result.append(dict(seed=seed,arm=arm,phase=phase,scout=scout,receiver=receiver,
                    attempts=len(selected),correct=sum(int(r['outcome']) for r in selected),
                    delivered=len(delivered),delivered_correct=sum(int(r['outcome']) for r in delivered),
                    unrelated_packets=len(unrelated),unrelated_correct=sum(int(r['outcome']) for r in unrelated),
                    marker_symbol_bits=information((r['marker'],r['symbol_received']) for r in unrelated)))
    write_csv(root/'information.csv',result)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path)
    summarize(parser.parse_args().results)
