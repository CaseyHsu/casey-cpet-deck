"""Shared helpers for reading and rewriting .pptx packages at the XML-part level.

python-pptx does not model animation (p:timing), so the finalize tools work on
the raw package: read every part, edit a few XML trees with lxml, and write a
new zip with the remaining parts copied byte-for-byte.
"""
from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

from lxml import etree

# Windows zh-TW consoles default to cp950; slide text (−, μ, ω…) would crash print().
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
P = "{%s}" % NS["p"]
A = "{%s}" % NS["a"]
R = "{%s}" % NS["r"]


def md5(path: str | Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Package:
    """In-memory view of a pptx: ordered part names -> bytes, plus parsed-tree cache."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        with zipfile.ZipFile(self.path) as z:
            self.infos = z.infolist()
            self.parts = {i.filename: z.read(i.filename) for i in self.infos}
        self._trees: dict[str, etree._Element] = {}

    # ---- parts ----
    def tree(self, name: str) -> etree._Element:
        if name not in self._trees:
            self._trees[name] = etree.fromstring(self.parts[name])
        return self._trees[name]

    def mark_dirty(self, name: str) -> None:
        self.parts[name] = etree.tostring(
            self._trees[name], xml_declaration=True, encoding="UTF-8", standalone=True
        )

    def rels(self, part: str) -> dict[str, tuple[str, str]]:
        """rId -> (type, absolute target part name) for a part's .rels."""
        d, f = part.rsplit("/", 1)
        rp = f"{d}/_rels/{f}.rels"
        if rp not in self.parts:
            return {}
        out = {}
        for r in etree.fromstring(self.parts[rp]):
            tgt = r.get("Target")
            if r.get("TargetMode") == "External":
                out[r.get("Id")] = (r.get("Type"), tgt)
                continue
            out[r.get("Id")] = (r.get("Type"), _resolve(d, tgt))
        return out

    def slides(self) -> list[str]:
        """Slide part names in presentation order."""
        pres = self.tree("ppt/presentation.xml")
        rmap = self.rels("ppt/presentation.xml")
        return [rmap[s.get(R + "id")][1] for s in pres.findall(".//p:sldIdLst/p:sldId", NS)]

    def notes_part(self, slide: str) -> str | None:
        for typ, tgt in self.rels(slide).values():
            if typ.endswith("/notesSlide"):
                return tgt
        return None

    def save(self, out: str | Path) -> None:
        for name in list(self._trees):
            self.mark_dirty(name)
        out = Path(out)
        tmp = out.with_suffix(out.suffix + ".tmp")
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for info in self.infos:
                if info.filename in self.parts:
                    z.writestr(info, self.parts[info.filename], compress_type=zipfile.ZIP_DEFLATED)
        tmp.replace(out)


def _resolve(base_dir: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    parts = base_dir.split("/") if base_dir else []
    for seg in target.split("/"):
        if seg == "..":
            parts.pop()
        elif seg and seg != ".":
            parts.append(seg)
    return "/".join(parts)


def c14n(el: etree._Element) -> bytes:
    return etree.tostring(el, method="c14n")


def shape_index(slide_tree: etree._Element) -> dict[str, dict]:
    """id -> {name, kind, el} for every shape-like element on a slide (groups included)."""
    out = {}
    for nv in slide_tree.iter(P + "cNvPr"):
        owner = nv.getparent().getparent()  # p:nvSpPr -> p:sp etc.
        out[nv.get("id")] = {"name": nv.get("name"), "kind": etree.QName(owner).localname, "el": owner}
    return out


def shape_text(el: etree._Element) -> str:
    return "".join(t.text or "" for t in el.iter(A + "t"))
