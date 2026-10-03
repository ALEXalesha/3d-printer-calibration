"""Start and end code templates.

A template is a list of lines. Two kinds of markers:

- {name} - replaced by a value (always a ready string; numbers are formatted by the
  generator, never here). A value with line breaks becomes several lines.
- {?flag} at the very start of a line - the line stays only if the flag is on
  ({?!flag} - only if it is off). Flags: the printer's options (canvas, nozzle_wipe, ...)
  plus a few the generator computes (pla_hot_bed).

Unknown names are left as they are and reported: the G-code check refuses any '{...}'
left in a file.
"""
import re

_NAME = re.compile(r"\{([a-z_][a-z0-9_]*)\}")
_FLAG = re.compile(r"^\{\?(!?)([a-z_][a-z0-9_]*)\}")


def expand(lines, values, flags):
    """-> (lines, unknown names in order of appearance)."""
    out, unknown = [], []
    for line in lines:
        m = _FLAG.match(line)
        if m:
            on = bool(flags.get(m.group(2), False))
            if m.group(1) == "!":
                on = not on
            if not on:
                continue
            line = line[m.end():]

        def sub(mm):
            key = mm.group(1)
            if key in values:
                return values[key]
            if key not in unknown:
                unknown.append(key)
            return mm.group(0)

        out.extend(_NAME.sub(sub, line).split("\n"))
    return out, unknown


def placeholders(lines):
    """Names and flags a template uses."""
    names, flags = [], []
    for line in lines:
        m = _FLAG.match(line)
        if m:
            if m.group(2) not in flags:
                flags.append(m.group(2))
            line = line[m.end():]
        for n in _NAME.findall(line):
            if n not in names:
                names.append(n)
    return names, flags
