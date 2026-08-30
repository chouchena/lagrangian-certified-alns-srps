# -*- coding: utf-8 -*-
"""Fail if any assistant attribution would ship with the repository.

The published artifact must carry no trace of the tooling used to build it.
Three surfaces have to be clean, and they need different treatment:

  1. FILE CONTENTS of tracked files
  2. FILE AND DIRECTORY NAMES (CLAUDE.md, .claude/)
  3. COMMIT MESSAGES -- Co-Authored-By trailers live in git history, which a
     content check cannot see and an edit cannot remove

Surface 3 is the awkward one: 37 of 68 commits in this repository carry a
trailer. Rewriting history changes every hash downstream of the first rewritten
commit. The recommended remedy is therefore NOT a rewrite but a clean export:
publish a snapshot with a fresh history, which also drops the development
scaffolding (.claude/, CLAUDE.md, dev_*/, archive/) that has no place in a
replication package anyway.

    python checks/check_no_attribution.py            # audit the working tree
    python checks/check_no_attribution.py --history  # also audit commit messages
    python checks/check_no_attribution.py --export ../srps-alns-public

Exit code 1 if anything would leak.
"""
from __future__ import annotations
import argparse
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# Patterns that must not appear. Word-boundaried so "claim", "clause" and
# "anthropic" inside a citation title do not trip it.
PATTERNS = [
    r"\bclaude\b",
    r"\banthropic\b",
    r"co-authored-by:\s*claude",
    r"generated with .*claude",
    r"\bai[- ]assisted\b",
    r"\bllm[- ]generated\b",
]
RX = re.compile("|".join(PATTERNS), re.I)

# Development scaffolding that should never reach a replication package.
EXCLUDE_FROM_EXPORT = [
    ".claude", "CLAUDE.md", "dev_dual_guided", "dev_bpc_replica", "dev_exact",
    "archive", "scratch", ".git", "__pycache__", ".venv", "paper_overleaf.zip",
]

TEXT_EXT = {".py", ".md", ".tex", ".txt", ".yaml", ".yml", ".json", ".csv",
            ".sh", ".bib", ".cfg", ".toml", ".ini", ".gitignore"}


def tracked_files():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    return [p for p in out.stdout.splitlines() if p.strip()]


def audit_tree():
    problems = []
    for p in tracked_files():
        base = os.path.basename(p)
        if RX.search(p):
            problems.append(("PATH", p, p))
        ext = os.path.splitext(base)[1].lower()
        if ext and ext not in TEXT_EXT:
            continue
        try:
            with open(p, encoding="utf-8", errors="ignore") as fh:
                for n, line in enumerate(fh, 1):
                    if RX.search(line):
                        problems.append(("CONTENT", "%s:%d" % (p, n), line.strip()[:90]))
        except (OSError, IsADirectoryError):
            pass
    return problems


def audit_history():
    out = subprocess.run(["git", "log", "--all", "--format=%H%x1f%s%x1f%b%x1e"],
                         capture_output=True, text=True)
    hits = []
    for rec in out.stdout.split("\x1e"):
        if not rec.strip():
            continue
        parts = rec.strip().split("\x1f")
        if len(parts) < 2:
            continue
        sha, subject = parts[0], parts[1]
        body = parts[2] if len(parts) > 2 else ""
        if RX.search(subject) or RX.search(body):
            hits.append((sha[:9], subject[:70]))
    return hits


def do_export(dest):
    if os.path.exists(dest):
        sys.exit("refusing to overwrite existing path: %s" % dest)
    os.makedirs(dest)
    n = 0
    for p in tracked_files():
        top = p.split("/")[0]
        if top in EXCLUDE_FROM_EXPORT or RX.search(p):
            continue
        d = os.path.join(dest, os.path.dirname(p))
        if d:
            os.makedirs(d, exist_ok=True)
        shutil.copy2(p, os.path.join(dest, p))
        n += 1
    print("exported %d files to %s" % (n, dest))
    print("\nNext steps (fresh history, no trailers):")
    print("  cd %s && git init && git add -A" % dest)
    print("  git commit -m 'SRPS-ALNS: certified primal-dual method for the "
          "Selective Routing Problem with Synchronization'")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", action="store_true")
    ap.add_argument("--export", metavar="DEST")
    cli = ap.parse_args()

    if cli.export:
        return do_export(cli.export)

    rc = 0
    tree = audit_tree()
    print("WORKING TREE: %d issue(s)" % len(tree))
    for kind, where, what in tree:
        print("  %-8s %-46s %s" % (kind, where, what))
    if tree:
        rc = 1

    if cli.history:
        hist = audit_history()
        print("\nCOMMIT HISTORY: %d commit(s) with attribution" % len(hist))
        for sha, subj in hist[:10]:
            print("  %s  %s" % (sha, subj))
        if len(hist) > 10:
            print("  ... and %d more" % (len(hist) - 10))
        if hist:
            print("\n  History cannot be cleaned by editing files. Either rewrite")
            print("  history (changes every downstream hash) or publish a clean")
            print("  export: python checks/check_no_attribution.py --export DEST")
            rc = 1

    print("\n%s" % ("CLEAN" if rc == 0 else "NOT CLEAN — see above"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
