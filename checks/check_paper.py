# -*- coding: utf-8 -*-
"""Structural lint for paper/main.tex. No LaTeX toolchain is installed here.

Catches what a first compile would throw: undefined references, duplicate
labels, citations with no bib entry, unbalanced braces and environments, odd
math delimiters, and tabular rows with more cells than the column spec allows.
It cannot check typesetting -- no overfull boxes, no float placement.

This exists because main_standalone.tex once carried five cited keys with no
\\bibitem, including the safe-bounds reference behind Appendix A. Those compile
to a bold [?] without failing the build. BibTeX catches that class of error in
main.tex automatically, but nothing catches the rest.

    python checks/check_paper.py            # lints paper/main.tex
    python checks/check_paper.py path.tex

Exit code is 1 if any hard problem is found, so it can gate a commit.
"""
from __future__ import annotations
import collections
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

HARD = ("DUPLICATE", "UNDEFINED", "MISSING", "MISMATCH", "IMBALANCE", "ODD", "ROW")


def strip_comments(t: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", t)


def lint(path: str, bib_keys: set | None):
    t = strip_comments(io.open(path, encoding="utf-8").read())
    problems: list[str] = []

    labels = re.findall(r"\\label\{([^}]*)\}", t)
    refs: set[str] = set()
    for m in re.finditer(r"\\(?:ref|autoref|eqref|Cref|cref)\{([^}]*)\}", t):
        refs.update(x.strip() for x in m.group(1).split(","))

    dup = [k for k, v in collections.Counter(labels).items() if v > 1]
    if dup:
        problems.append("DUPLICATE labels: %s" % ", ".join(sorted(dup)))
    undef = refs - set(labels)
    if undef:
        problems.append("UNDEFINED refs: %s" % ", ".join(sorted(undef)))
    unused = set(labels) - refs
    if unused:
        problems.append("note: unused labels (harmless): %s" % ", ".join(sorted(unused)))

    cites: set[str] = set()
    for m in re.finditer(r"\\cite[tp]?\*?(?:\[[^\]]*\])*\{([^}]*)\}", t):
        cites.update(x.strip() for x in m.group(1).split(","))
    if bib_keys is not None:
        miss = cites - bib_keys
        if miss:
            problems.append("MISSING bib entries: %s" % ", ".join(sorted(miss)))
        unc = bib_keys - cites
        if unc:
            problems.append("note: uncited bib entries (BibTeX omits them): %s"
                            % ", ".join(sorted(unc)))

    opens = collections.Counter(re.findall(r"\\begin\{([^}]*)\}", t))
    closes = collections.Counter(re.findall(r"\\end\{([^}]*)\}", t))
    for e in sorted(set(opens) | set(closes)):
        if opens[e] != closes[e]:
            problems.append("ENV MISMATCH %s: %d begin / %d end" % (e, opens[e], closes[e]))

    b = re.sub(r"\\[{}]", "", t)
    if b.count("{") != b.count("}"):
        problems.append("BRACE IMBALANCE: %d { vs %d }" % (b.count("{"), b.count("}")))

    if t.count("$$") % 2:
        problems.append("ODD number of $$")
    singles = len(re.findall(r"(?<!\\)(?<!\$)\$(?!\$)", t))
    if singles % 2:
        problems.append("ODD number of inline $ (%d)" % singles)

    for m in re.finditer(r"\\begin\{tabular\}\{([^}]*)\}(.*?)\\end\{tabular\}", t, re.S):
        spec, body = m.group(1), m.group(2)
        ncol = len(re.findall(r"[lcrp]", re.sub(r"p\{[^}]*\}", "p", spec)))
        for line in body.split(r"\\"):
            line = line.strip()
            if (not line or line.startswith("\\") or "multicolumn" in line
                    or "cmidrule" in line or "midrule" in line):
                continue
            n = line.count("&") + 1
            if n > ncol:
                problems.append("ROW OVERFLOW: %d cells vs %d cols: %s"
                                % (n, ncol, line[:60]))
                break

    return problems, len(set(labels)), len(cites)


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "paper/main.tex"
    if not os.path.exists(path):
        print("no such file: %s" % path)
        return 1

    bib_keys = None
    bib = os.path.join(os.path.dirname(path), "refs.bib")
    if os.path.exists(bib):
        bib_keys = set(re.findall(r"@\w+\{([^,]+),",
                                  io.open(bib, encoding="utf-8").read()))
        print("refs.bib: %d entries" % len(bib_keys))

    problems, nlab, ncit = lint(path, bib_keys)
    print("%s   labels=%d  cites=%d" % (path, nlab, ncit))
    hard = [p for p in problems if p.startswith(HARD)]
    for p in problems:
        print("  - %s" % p)
    if not problems:
        print("  clean")
    print("\n%d hard problem(s)" % len(hard))
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
