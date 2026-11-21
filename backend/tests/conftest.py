import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def fake_embed(texts):
    """Deterministic bag-of-words embedding so tests need no Ollama."""
    out = []
    for t in texts:
        v = [0.0] * 128
        for w in re.findall(r"[a-z0-9]+", t.lower()):
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 128] += 1.0
        out.append(v)
    return out
