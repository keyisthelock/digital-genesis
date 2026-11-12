"""Bounded, explicit personality revision derived from recorded results."""
import argparse
import json
from pathlib import Path

from ..journal import Journal, utc_now
from .runner import ROOT


def propose(journal):
    observed=[e for e in journal.review() if e["event_type"]=="learning_result"]
    if not observed:
        raise ValueError("No verified educational results")
    profile=json.loads((ROOT/"HOMER_PERSONALITY_V2.json").read_text(encoding="utf-8"))
    failures=[e for e in observed[-10:] if not e["metadata"]["passed"]]
    old=profile["tendencies"]["reflection"]
    new=round(min(1.,old+.02*len(failures)),2)
    profile["tendencies"]["reflection"]=new
    return profile,dict(timestamp=utc_now(),origin="bounded_preference_rule",field="reflection",
                        old=old,new=new,observed_ids=[e["event_id"] for e in failures],
                        reason="Increase practice weight slightly after verified failures")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("journal",type=Path)
    p.add_argument("out",type=Path)
    args=p.parse_args()
    if not args.journal.is_file():
        p.error("An existing isolated education journal is required")
    journal=Journal(args.journal)
    try:
        profile,log=propose(journal)
    finally:
        journal.close()
    args.out.mkdir(parents=True,exist_ok=False)
    (args.out/"profile.json").write_text(json.dumps(profile,indent=2),encoding="utf-8")
    (args.out/"revision.json").write_text(json.dumps(log,indent=2),encoding="utf-8")
