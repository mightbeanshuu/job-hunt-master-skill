"""Terminal UI helpers shared by the scripts: boxes, tables, progress bars, status marks.
Plain Unicode, no colour codes unless stdout is a real terminal, so the output reads the same when Claude relays it
inside a ```text block. Stdlib only."""
import os, sys, unicodedata

COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
_C = {"green": "32", "yellow": "33", "red": "31", "dim": "2", "bold": "1", "cyan": "36"}
OK, BAD, WARN, DOT = "✓", "✗", "⚠", "●"


def c(text, color):
    return f"\033[{_C[color]}m{text}\033[0m" if COLOR else text


def width(s):
    """Display width (CJK/emoji count double, combining marks zero)."""
    s = str(s)
    for code in _C.values():
        s = s.replace(f"\033[{code}m", "")
    s = s.replace("\033[0m", "")
    return sum(0 if unicodedata.combining(ch) else 2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in s)


def pad(s, w):
    return str(s) + " " * max(0, w - width(s))


def cut(s, n):
    s = " ".join(str(s).split())
    return s if width(s) <= n else s[: max(0, n - 1)] + "…"


def bar(value, total, size=24, lo=None):
    """█ filled, ░ empty; a │ tick marks `lo` (e.g. the daily minimum) when given."""
    total = max(total, 1)
    filled = min(size, round(size * value / total))
    cells = ["█"] * filled + ["░"] * (size - filled)
    if lo is not None and 0 < lo < total:
        i = min(size - 1, round(size * lo / total))
        if cells[i] == "░":
            cells[i] = "│"
    return "".join(cells)


def box(title, lines, w=None):
    w = w or max([width(title) + 4] + [width(l) for l in lines]) + 2
    out = [f"╭─ {title} " + "─" * max(0, w - width(title) - 3) + "╮"]
    out += [f"│ {pad(l, w - 2)} │" for l in lines]
    out.append("╰" + "─" * w + "╯")
    return "\n".join(out)


def banner(text):
    return f"━━ {text} " + "━" * max(4, 66 - width(text))


def table(headers, rows, maxw=None):
    maxw = maxw or {}
    rows = [[cut(x, maxw.get(i, 60)) for i, x in enumerate(r)] for r in rows]
    w = [max(width(h), *(width(r[i]) for r in rows)) if rows else width(h) for i, h in enumerate(headers)]
    line = lambda l, m, r: l + m.join("─" * (x + 2) for x in w) + r
    out = [line("┌", "┬", "┐"), "│" + "│".join(f" {pad(h, w[i])} " for i, h in enumerate(headers)) + "│", line("├", "┼", "┤")]
    out += ["│" + "│".join(f" {pad(x, w[i])} " for i, x in enumerate(r)) + "│" for r in rows]
    out.append(line("└", "┴", "┘"))
    return "\n".join(out)
