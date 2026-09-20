#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Variable-precision schedule dates for the WBS roadmap.

A commitment is not always made to the day. "Q1 next year" and "12 March
2026" are both real answers and they are not the same answer, so the register
stores the string the user typed and precision is derived here at read time:
writing `Q1-26` back as `2026-03-31` would invent a confidence nobody has.

    2026-Mar-12   that day                       day
    Mar-26        2026-03-01 -> 2026-03-31       month
    Q1-26         2026-01-01 -> 2026-03-31       quarter

The rule that makes this worth the trouble is `variance`: a comparison runs
at the *coarser* of the two precisions involved. Baseline `Q1-26` against a
plan of `2026-Mar-12` is on plan, not nineteen days early - the commitment
was only ever quarter-accurate, and reporting days against it would be a
precision the baseline never had.

This module is the only place any of that is decided. The dashboard receives
instants already resolved by `refresh_wbs.py` and never parses a date itself,
so there is one implementation rather than a Python one and a JavaScript one
drifting apart.
"""
import re

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_NUM = {m.lower(): i for i, m in enumerate(MONTHS, 1)}
DAYS_IN = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# Coarse to fine. A comparison runs at the coarsest precision present.
PRECISIONS = ("quarter", "month", "day")

DAY_RE = re.compile(r"^(\d{4})-([A-Za-z]{3})-(\d{1,2})$")
MONTH_RE = re.compile(r"^([A-Za-z]{3})-(\d{2})$")
QUARTER_RE = re.compile(r"^Q([1-4])-(\d{2})$", re.IGNORECASE)

FORMS = "YYYY-Mon-DD (2026-Mar-12), Mon-YY (Mar-26), or Qn-YY (Q1-26)"


def _last_day(year, month):
    if month == 2 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
        return 29
    return DAYS_IN[month - 1]


def _iso(year, month, day):
    return "%04d-%02d-%02d" % (year, month, day)


def resolve(text):
    """One of the three forms -> {text, start, end, precision}, else None.

    Two-digit years are 2000-2099. This is a personal planning horizon, not
    an archive format, and a four-digit year in the month and quarter forms
    would make the common case wordier to serve a case that will not arise.
    """
    if text is None:
        return None
    text = str(text).strip()
    if not text:
        return None

    m = DAY_RE.match(text)
    if m:
        year, mon, day = int(m.group(1)), MONTH_NUM.get(m.group(2).lower()), int(m.group(3))
        if not mon or not 1 <= day <= _last_day(year, mon):
            return None
        stamp = _iso(year, mon, day)
        return {"text": text, "start": stamp, "end": stamp, "precision": "day"}

    m = MONTH_RE.match(text)
    if m:
        mon = MONTH_NUM.get(m.group(1).lower())
        if not mon:
            return None
        year = 2000 + int(m.group(2))
        return {"text": text, "start": _iso(year, mon, 1),
                "end": _iso(year, mon, _last_day(year, mon)), "precision": "month"}

    m = QUARTER_RE.match(text)
    if m:
        q, year = int(m.group(1)), 2000 + int(m.group(2))
        first = 3 * (q - 1) + 1
        return {"text": text, "start": _iso(year, first, 1),
                "end": _iso(year, first + 2, _last_day(year, first + 2)),
                "precision": "quarter"}
    return None


def coarser(a, b):
    """The less precise of two precisions - the one a comparison must use."""
    return a if PRECISIONS.index(a) <= PRECISIONS.index(b) else b


def bucket(iso, precision):
    """The index of the period `iso` falls in, at `precision`.

    Comparable across dates: subtracting two buckets at the same precision
    gives the distance in that precision's own unit, which is what R14 asks
    for. Day buckets count from 2000-01-01, an arbitrary epoch that only
    ever appears in a difference.
    """
    year, month, day = (int(p) for p in iso.split("-"))
    if precision == "quarter":
        return year * 4 + (month - 1) // 3
    if precision == "month":
        return year * 12 + (month - 1)
    total = 0
    for y in range(2000, year):
        total += 366 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 365
    for mm in range(1, month):
        total += _last_day(year, mm)
    return total + day


UNITS = {"day": "day", "month": "month", "quarter": "quarter"}


def variance(baseline, current):
    """How far `current` sits from `baseline`, at the coarser precision.

    Both are resolved dicts. Returns {amount, unit, precision}, where a
    positive amount is late. Returns None if either is missing, so a row
    with no baseline simply has no variance rather than a misleading zero.
    """
    if not baseline or not current:
        return None
    precision = coarser(baseline["precision"], current["precision"])
    amount = bucket(current["end"], precision) - bucket(baseline["end"], precision)
    return {"amount": amount, "unit": UNITS[precision], "precision": precision}


def describe(var):
    """Variance as the phrase a person would say. `None` -> 'no baseline'."""
    if var is None:
        return "no baseline"
    n, unit = var["amount"], var["unit"]
    if n == 0:
        return "on plan"
    word = unit if abs(n) == 1 else unit + "s"
    return "%d %s %s" % (abs(n), word, "late" if n > 0 else "early")


def earliest(resolved):
    """The earliest start among resolved dates, for rolling a parent up."""
    starts = [r["start"] for r in resolved if r]
    return min(starts) if starts else None


def latest(resolved):
    ends = [r["end"] for r in resolved if r]
    return max(ends) if ends else None
