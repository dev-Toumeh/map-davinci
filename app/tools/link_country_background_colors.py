#!/usr/bin/env python3
"""Make Wide country backgrounds inherit colors from their Detail counterparts."""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


WIDE_BACKGROUND = re.compile(
    r"(?m)^(?P<indent>\s*)(?P<base>[A-Za-z0-9_]+)_Wide_(?P<kind>Fill|Border)"
    r" = Background \{"
)


def _balanced_end(text: str, opening: int) -> int:
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError("unterminated Fusion block")


def _remove_input(block: str, name: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(name)} = Input \{{", block)
    if not match:
        return block
    opening = block.find("{", match.start())
    end = _balanced_end(block, opening)
    if end < len(block) and block[end] == ",":
        end += 1
    if end < len(block) and block[end] == "\n":
        end += 1
    return block[:match.start()] + block[end:]


def link_colors(text: str) -> tuple[str, int]:
    replacements: list[tuple[int, int, str]] = []
    for match in WIDE_BACKGROUND.finditer(text):
        opening = text.find("{", match.start())
        end = _balanced_end(text, opening)
        block = text[match.start():end]
        detail = f'{match.group("base")}_Detail_{match.group("kind")}'
        if not re.search(rf"(?m)^\s*{re.escape(detail)} = Background \{{", text):
            continue
        source = f'SourceOp = "{detail}",'
        inputs_start = block.find("Inputs = {")
        header = block[:inputs_start]
        body = block[inputs_start:]
        if re.search(r"(?m)^\s*SourceOp = ", header):
            header = re.sub(r'(?m)^(\s*)SourceOp = "[^"]+",',
                            rf'\1{source}', header, count=1)
        else:
            header = re.sub(r"(?m)^(\s*NameSet = true,)$",
                            rf'\1\n\t\t\t{source}', header, count=1)
        block = header + body
        for channel in ("TopLeftRed", "TopLeftGreen", "TopLeftBlue"):
            block = _remove_input(block, channel)
        replacements.append((match.start(), end, block))
    for start, end, block in reversed(replacements):
        text = text[:start] + block + text[end:]
    return text, len(replacements)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("composition", type=Path)
    args = parser.parse_args()
    path = args.composition.resolve()
    original = path.read_text(encoding="utf-8")
    updated, count = link_colors(original)
    if not count:
        raise SystemExit("No Wide/Detail country background pairs found")
    backup = path.with_suffix(path.suffix + ".before_shared_colors.bak")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(updated, encoding="utf-8")
    print(f"linked {count} Wide backgrounds to Detail color masters")
    print(f"backup: {backup}")


if __name__ == "__main__":
    main()
