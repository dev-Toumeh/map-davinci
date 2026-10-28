"""Editor-only country stack layout; never modify render coordinates or links."""
from __future__ import annotations

import re


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
TOOL_START = re.compile(r"(?m)^\t\t([A-Za-z_]\w*) = [A-Za-z_]\w* \{")
POSITION = re.compile(
    rf"(ViewInfo = (?:OperatorInfo|GroupInfo)\s*\{{\s*Pos = \{{\s*)"
    rf"({NUMBER}),\s*({NUMBER})(\s*\}})")
GROUP_OFFSET = re.compile(
    rf"(ViewInfo = GroupInfo\s*\{{.*?Offset = \{{\s*)"
    rf"({NUMBER}),\s*({NUMBER})(\s*\}})", re.S)
GROUP_SIZE = re.compile(
    rf"(ViewInfo = GroupInfo\s*\{{.*?Size = \{{\s*)"
    rf"({NUMBER}),\s*({NUMBER}),\s*({NUMBER}),\s*({NUMBER})(\s*\}})", re.S)


def arrange_country_stacks(content: str, countries: list[str], *, center_x: int) -> str:
    """First ceil(N/2) countries left, remainder right, in saved country order.

    Left stacks flow left-to-right; right stacks flow right-to-left into the
    central scene. Move whole countries, including child territories and
    expanded native groups. Preserve spacing, wiring, render values, and
    all non-country nodes. Column heights are measured from positions, so large
    geometry/highlight stacks do not collide with the next country.
    """
    countries = list(dict.fromkeys(countries))
    if not countries:
        return content
    matches = list(TOOL_START.finditer(content))
    blocks = [content[m.start():matches[i + 1].start() if i + 1 < len(matches)
                      else len(content)] for i, m in enumerate(matches)]
    owners = []
    bounds: dict[str, list[float]] = {}
    for match, block in zip(matches, blocks):
        name = match.group(1)
        owner = next((iso for iso in countries if name.startswith(iso + "_")), None)
        owners.append(owner)
        if owner is None:
            continue
        for pos in POSITION.finditer(block):
            x, y = float(pos.group(2)), float(pos.group(3))
            b = bounds.setdefault(owner, [x, y, x, y])
            b[:] = [min(b[0], x), min(b[1], y), max(b[2], x), max(b[3], y)]
    shifts = {}
    next_y = [360.0, 360.0]
    midpoint = (len(countries) + 1) // 2
    local_right = max((b[2] for b in bounds.values()), default=0)
    for index, country in enumerate(countries):
        if country not in bounds:
            continue
        side = int(index >= midpoint)
        _x0, y0, _x1, y1 = bounds[country]
        # Leave a central lane for scene/renderer/output; imagery stays above.
        # One transform per side keeps equivalent processing columns aligned
        # even when one country's geometry uses a compact optional-island group.
        direction = 1 if side == 0 else -1
        dx = center_x - 400 - local_right if side == 0 else center_x + 1000 + local_right
        dy = next_y[side] - y0
        shifts[country] = direction, dx, dy
        next_y[side] += y1 - y0 + 160
    result = [content[:matches[0].start()]] if matches else [content]
    for owner, block in zip(owners, blocks):
        if owner in shifts:
            direction, dx, dy = shifts[owner]
            block = POSITION.sub(
                lambda m: f"{m[1]}{direction * float(m[2]) + dx:.12g}, {float(m[3]) + dy:.12g}{m[4]}", block)
            # Group offsets are inverses of their Flow positions. Move those
            # too, so expanding a translated group retains its internal view.
            block = GROUP_OFFSET.sub(
                lambda m: f"{m[1]}{direction * float(m[2]) - dx:.12g}, {float(m[3]) - dy:.12g}{m[4]}", block)
            if direction == -1:
                # Size stores width, height and the anchor's left/top insets.
                # Reflect the left inset too, keeping expanded frames around
                # their mirrored contents rather than leaving the frame behind.
                block = GROUP_SIZE.sub(
                    lambda m: f"{m[1]}{m[2]}, {m[3]}, {float(m[2]) - float(m[4]):.12g}, {m[5]}{m[6]}", block)
        result.append(block)
    return "".join(result)
