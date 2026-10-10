"""Regenerate GEMINI.md from the canonical AGENTS.md.

AGENTS.md is the single source of truth for portable agent instructions (used by Codex, OpenCode,
Antigravity). Gemini CLI reads GEMINI.md instead, so we keep an identical-body copy. Run after
editing AGENTS.md:

    python tools/sync_agent_docs.py            # write GEMINI.md
    python tools/sync_agent_docs.py --check     # exit 1 if GEMINI.md is stale (for CI)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "AGENTS.md"
TARGET = ROOT / "GEMINI.md"

GEMINI_HEADER = (
    "<!-- GENERATED from AGENTS.md by tools/sync_agent_docs.py. Do not edit directly; "
    "edit AGENTS.md and re-run the script. -->\n"
)


def render() -> str:
    lines = SOURCE.read_text(encoding="utf-8").splitlines(keepends=True)
    # Drop the leading canonical-note HTML comment so the bodies match.
    if lines and lines[0].lstrip().startswith("<!--"):
        lines = lines[1:]
        while lines and lines[0].strip() == "":
            lines = lines[1:]
    return GEMINI_HEADER + "\n" + "".join(lines)


def main(argv: list[str]) -> int:
    expected = render()
    if "--check" in argv:
        actual = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if actual != expected:
            print("GEMINI.md is out of date — run: python tools/sync_agent_docs.py")
            return 1
        print("GEMINI.md is up to date.")
        return 0
    TARGET.write_text(expected, encoding="utf-8")
    print(f"Wrote {TARGET.relative_to(ROOT)} from {SOURCE.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
