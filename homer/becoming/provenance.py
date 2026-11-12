"""Pinned local archives and the historical model used in the published runs."""
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OMEGA = ROOT / "genesis_1_4/results/pilot/14030/preserved/final.pkl"
IDENTITY = ROOT / "homer/HOMER_01_Starter_Pack/homer_identity.json"
CHECKPOINT = "26b5c61aa5a51c03648cf289c957fcbe03bc75fa9038642c693b15bfb18217ad"
WEIGHT_SHA = "e8bf47d40c5ba68baf8f3e503ee36710da6e8641cb0a670a508cff5b3f0cfbf7"


def archive_hashes():
    hashes = {name: sha256(path.read_bytes()).hexdigest() if path.is_file() else None
              for name, path in (("omega", OMEGA), ("identity", IDENTITY))}
    if hashes["omega"] not in (None, CHECKPOINT):
        raise ValueError("Omega checkpoint differs")
    return hashes
