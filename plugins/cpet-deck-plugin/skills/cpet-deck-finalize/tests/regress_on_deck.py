"""Regression against a real finished project (paths as arguments; nothing is copied into the repo).

    python regress_on_deck.py <Final.pptx> <NoAnim.pptx> <work_dir>

1. derive verify-noanim: re-deriving the no-animation deck from Final must give
   identical parts (c14n) to the delivered no-animation deck.
2. anim round trip: extract Final's animation, strip it, re-inject, and the
   per-click (target, class, node type) sequence must be identical; lint clean.
Run it on copies (e.g. in a scratch folder); the decks are only read.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import anim  # noqa: E402
import derive  # noqa: E402
from pptx_xml import Package  # noqa: E402


def signature(path):
    p = Package(path)
    out = {}
    for i, n in enumerate(p.slides(), 1):
        cl = anim.read_clicks(p.tree(n))
        if cl:
            out[i] = [[(e["spid"], e["class"], e["node"]) for e in c] for c in cl]
    return out


def main(final, noanim, work):
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    ok = derive.main(["verify-noanim", final, noanim]) == 0
    spec = work / "spec.json"
    anim.main(["extract", final, str(spec)])
    pkg = Package(final)
    derive.strip_animation(pkg, None)
    pkg.save(work / "stripped.pptx")
    rc = anim.main(["inject", str(work / "stripped.pptx"), str(spec), str(work / "reinjected.pptx")])
    a, b = signature(final), signature(work / "reinjected.pptx")
    same = a == b
    total = sum(len(v) for v in a.values())
    print(f"verify-noanim: {'PASS' if ok else 'FAIL'}")
    print(f"anim round trip: {'PASS' if same and rc == 0 else 'FAIL'} ({len(a)} animated slides, {total} clicks)")
    return 0 if ok and same and rc == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(*sys.argv[1:]))
