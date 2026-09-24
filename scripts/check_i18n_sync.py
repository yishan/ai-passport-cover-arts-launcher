#!/usr/bin/env python3
"""Check that every English Markdown file and its .zh_CN.md translation agree.

English files are canonical. A translation may word things differently, but it
must keep the same structure so an agent reading either language follows the
same workflow:

- the counterpart file exists, and the language switcher links to it;
- front-matter keys match, and the `name` value is identical;
- the heading outline (level of each heading, in order) matches;
- fenced code blocks are byte-identical and in the same order;
- the relative link paths match once `.zh_CN.md` is mapped to `.md`.

Usage: scripts/check_i18n_sync.py [repo-root]
"""

import re
import sys
from pathlib import Path

SUFFIX = ".zh_CN.md"
SKIP_DIRS = {".git", "node_modules", "build"}
FENCE = re.compile(r"^(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+\S")
LINK = re.compile(r"\]\(([^)\s]+)\)|href=\"([^\"]+)\"")


def split_front_matter(text):
    if not text.startswith("---\n"):
        return {}, text
    end = text.index("\n---\n", 4)
    keys = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            keys[key.strip()] = value.strip()
    return keys, text[end + 5:]


def parse(text):
    """Return heading levels, code blocks, and relative link targets."""
    headings, blocks, links = [], [], []
    block = None
    for line in text.splitlines():
        if block is not None:
            if FENCE.match(line):
                blocks.append("\n".join(block))
                block = None
            else:
                block.append(line)
            continue
        if FENCE.match(line):
            block = [line]
            continue
        match = HEADING.match(line)
        if match:
            headings.append(len(match.group(1)))
        for found in LINK.finditer(line):
            target = found.group(1) or found.group(2)
            if not re.match(r"^[a-z]+:", target) and not target.startswith("#"):
                links.append(target)
    if block is not None:
        raise ValueError("unterminated code fence")
    return headings, blocks, links


def canonical_links(links, own_name, other_name):
    """Drop the language switcher and map translated targets to English."""
    result = []
    for target in links:
        path = target.split("#", 1)[0]
        if path in (own_name, other_name):
            continue
        # Fragments are heading slugs, which are language-specific.
        result.append(path.replace(SUFFIX, ".md"))
    return sorted(result)


def check_pair(english, chinese):
    problems = []
    en_text = english.read_text(encoding="utf-8")
    zh_text = chinese.read_text(encoding="utf-8")

    if f'href="{chinese.name}"' not in en_text:
        problems.append(f"{english.name} does not link to {chinese.name}")
    if f'href="{english.name}"' not in zh_text:
        problems.append(f"{chinese.name} does not link to {english.name}")

    en_meta, en_body = split_front_matter(en_text)
    zh_meta, zh_body = split_front_matter(zh_text)
    if sorted(en_meta) != sorted(zh_meta):
        problems.append(f"front-matter keys differ: {sorted(en_meta)} vs {sorted(zh_meta)}")
    if en_meta.get("name") != zh_meta.get("name"):
        problems.append("front-matter `name` differs")

    try:
        en_headings, en_blocks, en_links = parse(en_body)
        zh_headings, zh_blocks, zh_links = parse(zh_body)
    except ValueError as error:
        return problems + [str(error)]

    if en_headings != zh_headings:
        problems.append(
            f"heading outline differs: {en_headings} vs {zh_headings}")
    if len(en_blocks) != len(zh_blocks):
        problems.append(
            f"code block count differs: {len(en_blocks)} vs {len(zh_blocks)}")
    for index, (en_block, zh_block) in enumerate(zip(en_blocks, zh_blocks), 1):
        if en_block != zh_block:
            problems.append(f"code block {index} differs")

    en_targets = canonical_links(en_links, english.name, chinese.name)
    zh_targets = canonical_links(zh_links, chinese.name, english.name)
    if en_targets != zh_targets:
        only_en = sorted(set(en_targets) - set(zh_targets))
        only_zh = sorted(set(zh_targets) - set(en_targets))
        problems.append(
            f"link targets differ; only English: {only_en}; only Chinese: {only_zh}")
    return problems


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    failed = False
    pairs = 0
    for path in sorted(root.rglob("*.md")):
        if SKIP_DIRS.intersection(path.relative_to(root).parts):
            continue
        rel = path.relative_to(root)
        if path.name.endswith(SUFFIX):
            english = path.with_name(path.name[:-len(SUFFIX)] + ".md")
            if not english.exists():
                print(f"{rel}: missing English counterpart {english.name}")
                failed = True
            continue
        chinese = path.with_name(path.stem + SUFFIX)
        if not chinese.exists():
            print(f"{rel}: missing translation {chinese.name}")
            failed = True
            continue
        pairs += 1
        for problem in check_pair(path, chinese):
            print(f"{rel}: {problem}")
            failed = True
    if failed:
        return 1
    print(f"{pairs} English/Chinese pair(s) in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
