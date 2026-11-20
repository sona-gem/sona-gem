#!/usr/bin/env python3
"""
Commit Constellation (dark): your GitHub activity as a small star map.

  python generate_constellation.py            # live data from GitHub
  python generate_constellation.py --demo     # built-in sample data
  python generate_constellation.py someuser   # a different username

Set GITHUB_TOKEN to avoid API rate limits.

How to read it (the image carries a tiny caption too):
  Orion          = your projects: repos you own, plus team repos where you have
                   TEAM_MIN_PRS or more merged PRs (the busiest sits in the belt)
  ringed stars   = other projects you've had pull requests merged into
  orbiting dot   = a quantum project
  size           = commits (own repos) or merged PRs (contributions)
  glow           = how recently you pushed or merged
  colour         = the repo's main language
"""
import json, math, os, random, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

USER = next((a for a in sys.argv[1:] if not a.startswith("--")), "sona-gem")
DEMO = "--demo" in sys.argv
OUT = "constellation.svg"
TEAM_MIN_PRS = 3  # merged PRs that make a team repo count as "yours"
W, H = 800, 300

PALETTE = {  # muted on purpose
    "Python": "#8fb8de", "Jupyter Notebook": "#8fb8de", "JavaScript": "#e6cf8c",
    "TypeScript": "#a99bd9", "Java": "#e0a08a", "C++": "#8fd1b6", "Dart": "#8fd6e8", "HTML": "#e0a08a",
}
DEFAULT = "#c9d1d9"

# ---------- Orion template (x, y in "units", y points down) ----------
ORION = {
    "Meissa": (0, -2.3), "Betelgeuse": (-1.15, -1.55), "Bellatrix": (1.15, -1.5),
    "Alnitak": (-0.6, 0.05), "Alnilam": (0, -0.05), "Mintaka": (0.6, -0.15),
    "Saiph": (-1.0, 1.7), "Rigel": (1.25, 1.6), "Sword1": (-0.1, 0.75), "Sword2": (-0.1, 1.15),
    "Shield1": (1.95, -1.95), "Shield2": (2.3, -1.2), "Shield3": (2.15, -0.4), "Club": (-1.95, -2.25),
}
# busiest repo first; every prefix of this list stays connected
ORDER = ["Alnilam", "Alnitak", "Mintaka", "Betelgeuse", "Bellatrix", "Saiph", "Rigel",
         "Meissa", "Sword1", "Sword2", "Shield1", "Shield2", "Shield3", "Club"]
LINKS = [("Meissa", "Betelgeuse"), ("Meissa", "Bellatrix"), ("Betelgeuse", "Alnitak"),
         ("Bellatrix", "Mintaka"), ("Alnitak", "Alnilam"), ("Alnilam", "Mintaka"),
         ("Alnitak", "Saiph"), ("Mintaka", "Rigel"), ("Alnilam", "Sword1"), ("Sword1", "Sword2"),
         ("Bellatrix", "Shield1"), ("Shield1", "Shield2"), ("Shield2", "Shield3"), ("Betelgeuse", "Club")]
OX, OY, U = 520, 150, 52

# left-hand sky for contribution stars (pixel positions, busiest project first)
OSS_SLOTS = [(196, 134), (156, 176), (118, 118), (272, 122), (234, 194), (152, 72), (82, 190), (238, 52),
             (308, 210), (72, 58), (318, 78), (200, 236), (48, 128), (336, 150), (118, 242), (276, 246)]
QUANTUM_HINTS = ("quantum", "qiskit", "qutip", "qulacs", "deltakit", "cirq", "pennylane", "qubit")

# ---------- data ----------
def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "commit-constellation"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request("https://api.github.com" + path, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r), r.headers

def days_since(iso):
    t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - t).days

def commit_count(full):
    data, headers = api(f"/repos/{full}/commits?author={USER}&per_page=1")
    m = re.search(r'[?&]page=(\d+)>; rel="last"', headers.get("Link", ""))
    return int(m.group(1)) if m else len(data)

def live_own():
    repos, _ = api(f"/users/{USER}/repos?per_page=100&type=owner")
    out = []
    for r in repos:
        if r["fork"] or r["name"].lower() == USER.lower():  # skip forks and the profile repo itself
            continue
        try:
            c = commit_count(f"{USER}/{r['name']}")
        except Exception:
            c = 0
        if c:
            text = " ".join([r["name"], r.get("description") or "", *r.get("topics", [])]).lower()
            out.append(dict(name=r["name"], lang=r["language"] or "", n=c, days=days_since(r["pushed_at"]),
                            quantum=any(h in text for h in QUANTUM_HINTS)))
    return out

def live_oss():
    q = urllib.parse.quote(f"author:{USER} type:pr is:merged -user:{USER}")
    data, _ = api(f"/search/issues?q={q}&per_page=100&sort=updated")
    found = {}
    for it in data["items"]:
        full = it["repository_url"].split("/repos/")[1]
        e = found.setdefault(full, dict(name=full.split("/")[1], full=full, n=0, days=10**6))
        e["n"] += 1
        e["days"] = min(e["days"], days_since(it["closed_at"]))
    for e in found.values():
        try:
            info = api(f"/repos/{e['full']}")[0]
        except Exception:
            info = {}
        e["lang"] = info.get("language") or ""
        text = " ".join([e["full"], info.get("description") or "", *info.get("topics", [])]).lower()
        e["quantum"] = any(h in text for h in QUANTUM_HINTS)
    return list(found.values())

def demo_own():  # snapshot of real data (Nov 2026), so --demo works offline
    rows = [["SmartSplit", "JavaScript", 4, 125, False], ["Sudoku_Solver", "Python", 21, 133, False], ["clinic-management-system", "HTML", 7, 384, False], ["salary-prediction", "Jupyter Notebook", 3, 484, False], ["ShowBuzz", "JavaScript", 3, 530, False], ["QuantumCheckers", "Python", 12, 33, True], ["NeuroBridge", "JavaScript", 17, 84, False], ["LogFlow", "TypeScript", 11, 93, False], ["cellexis", "TypeScript", 8, 411, False]]
    return [dict(name=n, lang=l, n=c, days=d, quantum=q) for n, l, c, d, q in rows]

def demo_oss():
    rows = [["qiskit", "Python", 1, 52, True], ["qulacs", "C++", 1, 52, True], ["qutip", "Python", 1, 52, True], ["deltakit-core", "Python", 1, 50, True], ["deltakit", "Python", 1, 51, True], ["Civora", "JavaScript", 2, 136, False], ["DailyForge", "JavaScript", 1, 165, False], ["TourEase", "JavaScript", 1, 175, False], ["Brownie-Bliss", "HTML", 1, 175, False], ["Safelens", "Dart", 1, 377, False], ["TravelGrid", "JavaScript", 1, 473, False]]
    return [dict(name=n, lang=l, n=c, days=d, quantum=q) for n, l, c, d, q in rows]

# ---------- drawing helpers ----------
def star_path(r):
    k = r * 0.16
    return (f"M0 {-r:.1f}Q{k:.1f} {-k:.1f} {r:.1f} 0Q{k:.1f} {k:.1f} 0 {r:.1f}"
            f"Q{-k:.1f} {k:.1f} {-r:.1f} 0Q{-k:.1f} {-k:.1f} 0 {-r:.1f}Z")

def place_labels(stars, limit=24):
    box = lambda s: (s["x"] - s["r"] - 3, s["y"] - s["r"] - 3, s["x"] + s["r"] + 3, s["y"] + s["r"] + 3)
    hit = lambda a, b: not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])
    taken, out = [], []
    # biggest first; open-source stars get a boost so they are always named
    order = sorted(stars, key=lambda s: -(s["r"] + (6 if s["ring"] else 0)))[:limit]
    for s in order:
        w, r = len(s["name"]) * 6.2, s["r"]
        cands = [("start", s["x"] + r + 6, s["y"] + 3.5, (s["x"] + r + 6, s["y"] - 8, s["x"] + r + 6 + w, s["y"] + 4)),
                 ("end", s["x"] - r - 6, s["y"] + 3.5, (s["x"] - r - 6 - w, s["y"] - 8, s["x"] - r - 6, s["y"] + 4))]
        for extra in (0, 8, 16):  # above / below, stepping further out if the neighbours are tight
            cands.append(("middle", s["x"], s["y"] - r - 7 - extra, (s["x"] - w / 2, s["y"] - r - 16 - extra, s["x"] + w / 2, s["y"] - r - 5 - extra)))
            cands.append(("middle", s["x"], s["y"] + r + 15 + extra, (s["x"] - w / 2, s["y"] + r + 6 + extra, s["x"] + w / 2, s["y"] + r + 17 + extra)))
        for anchor, x, y, bb in cands:
            if bb[0] < 8 or bb[2] > W - 8 or bb[1] < 8 or bb[3] > H - 24:
                continue
            if any(hit(bb, box(o)) for o in stars if o is not s) or any(hit(bb, t) for t in taken):
                continue
            taken.append(bb); out.append((s["name"], x, y, anchor)); break
    return out

def mesh(group):
    """Link a loose cluster: a spanning tree plus a few short extra links."""
    if len(group) < 2:
        return []
    d = lambda a, b: math.hypot(a["x"] - b["x"], a["y"] - b["y"])
    inside, rest, links = [group[0]], list(group[1:]), []
    while rest:
        a, b = min(((a, b) for a in inside for b in rest), key=lambda p: d(*p))
        links.append((a, b)); inside.append(b); rest.remove(b)
    have = {frozenset((id(a), id(b))) for a, b in links}
    extra = sorted(((d(a, b), a, b) for i, a in enumerate(group) for b in group[i + 1:]
                    if frozenset((id(a), id(b))) not in have and d(a, b) < 85), key=lambda t: t[0])
    return links + [(a, b) for _, a, b in extra[:4]]

# ---------- build ----------
def build(own, oss):
    own = sorted(own, key=lambda r: -r["n"])[:len(ORDER)]
    oss = sorted(oss, key=lambda r: (-r["n"], not r.get("quantum"), r["days"]))[:len(OSS_SLOTS)]
    rng = random.Random(USER)
    top_own = math.log1p(max(s["n"] for s in own))
    top_oss = math.log1p(max([3] + [s["n"] for s in oss]))
    pos = {}
    for s, slot in zip(own, ORDER):
        ux, uy = ORION[slot]
        s["x"], s["y"], s["ring"] = OX + ux * U, OY + uy * U, False
        s["r"] = 4.5 + 8 * math.log1p(s["n"]) / top_own
        pos[slot] = s
    oss_pos = []
    for s, (x, y) in zip(oss, OSS_SLOTS):
        s["x"], s["y"], s["ring"] = x, y, True
        s["r"] = 4 + 5 * math.log1p(s["n"]) / top_oss
        oss_pos.append(s)
    stars = own + oss
    links = [(pos[a], pos[b]) for a, b in LINKS if a in pos and b in pos]
    links += mesh(oss_pos)

    keys = {}
    for s in stars:
        s["col"] = PALETTE.get(s["lang"], DEFAULT)
        s["op"] = 0.42 + 0.58 * math.exp(-s["days"] / 120)
        keys.setdefault(s["col"], len(keys))

    css = [".ln{stroke:#8b949e;opacity:.42}.amb{fill:#c9d1d9}",
           ".lab{fill:#9aa4b2;font:10px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}",
           ".cap{fill:#6e7681;font:9.5px -apple-system,Segoe UI,Helvetica,Arial,sans-serif}",
           ".ring{fill:none;stroke:currentColor;stroke-width:.9;stroke-dasharray:1.2 3.2;opacity:.65}",
           ".tw{animation:tw 5s ease-in-out infinite}@keyframes tw{0%,100%{opacity:1}50%{opacity:.62}}",
           ".shoot{opacity:0;animation:shoot 14s cubic-bezier(.3,.5,.4,1) 4s infinite}",
           "@keyframes shoot{0%{opacity:0;transform:translate(0,0)}1.5%{opacity:1}8%{opacity:1}10%{opacity:0;transform:translate(640px,90px)}100%{opacity:0;transform:translate(640px,90px)}}",
           "@media (prefers-reduced-motion:reduce){.tw{animation:none}.shoot,.orb{display:none}}"]
    defs = ['<radialGradient id="neb" gradientUnits="userSpaceOnUse" cx="%d" cy="%d" r="120">'
            '<stop offset="0" stop-color="#4a3a8a" stop-opacity=".30"/><stop offset="1" stop-color="#4a3a8a" stop-opacity="0"/></radialGradient>'
            % (OX - 0.1 * U, OY + 0.95 * U),
            '<radialGradient id="sky" gradientUnits="userSpaceOnUse" cx="%d" cy="%d" r="380">'
            '<stop offset="0" stop-color="#1a2342" stop-opacity=".55"/><stop offset="1" stop-color="#1a2342" stop-opacity="0"/></radialGradient>'
            % (OX, OY)]
    defs.append('<linearGradient id="tail" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                '<stop offset="1" stop-color="#fff" stop-opacity=".9"/></linearGradient>'
                '<radialGradient id="hg"><stop offset="0" stop-color="#fff" stop-opacity=".7"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>')
    for col, i in keys.items():
        css.append(f".c{i}{{color:{col}}}.g{i}{{stop-color:{col}}}")
        defs.append(f'<radialGradient id="gl{i}"><stop class="g{i}" offset="0" stop-opacity=".38"/>'
                    f'<stop class="g{i}" offset="1" stop-opacity="0"/></radialGradient>')

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="A star map of {USER}\'s repositories. Own projects form the constellation Orion; ringed stars are open-source contributions.">',
         "<style>" + "".join(css) + "</style>", "<defs>" + "".join(defs) + "</defs>",
         f'<rect width="{W}" height="{H}" rx="12" fill="#0d1117"/>',
         f'<rect width="{W}" height="{H}" rx="12" fill="url(#sky)"/>',
         f'<rect width="{W}" height="{H}" rx="12" fill="url(#neb)"/>',
         f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="#21262d"/>']

    # faint background stars (decoration only)
    for _ in range(60):
        x, y = rng.uniform(12, W - 12), rng.uniform(12, H - 12)
        if any(math.hypot(x - s["x"], y - s["y"]) < 30 for s in stars) or (y > H - 28 and x < 520):
            continue
        if rng.random() > 0.88:
            o.append(f'<path class="amb" opacity="{rng.uniform(.25,.45):.2f}" transform="translate({x:.0f} {y:.0f})" d="{star_path(rng.uniform(2.8,4.2))}"/>')
        else:
            o.append(f'<circle class="amb" opacity="{rng.uniform(.15,.4):.2f}" cx="{x:.0f}" cy="{y:.0f}" r="{rng.uniform(.6,1.3):.1f}"/>')

    # dotted lines, stopping just short of each star
    for a, b in links:
        L = math.hypot(b["x"] - a["x"], b["y"] - a["y"])
        ux, uy = (b["x"] - a["x"]) / L, (b["y"] - a["y"]) / L
        pa, pb = a["r"] + 7, b["r"] + 7
        o.append(f'<line class="ln" stroke-width="1.5" stroke-linecap="round" stroke-dasharray="0.1 5.5" '
                 f'x1="{a["x"]+ux*pa:.0f}" y1="{a["y"]+uy*pa:.0f}" x2="{b["x"]-ux*pb:.0f}" y2="{b["y"]-uy*pb:.0f}"/>')

    # stars
    for s in stars:
        i, delay, dur = keys[s["col"]], rng.uniform(0, 5), rng.uniform(4, 7)
        R = s["r"] * 1.9 + 3
        ring = f'<circle class="ring" r="{R:.1f}"/>' if s["ring"] else ""
        if s.get("quantum"):
            if not s["ring"]:
                ring += f'<circle r="{R:.1f}" fill="none" stroke="currentColor" stroke-width=".8" opacity=".22"/>'
            ring += (f'<circle class="orb" r="1.8" fill="currentColor"><animateMotion dur="{rng.uniform(5,8):.1f}s" '
                     f'begin="-{rng.uniform(0,5):.1f}s" repeatCount="indefinite" '
                     f'path="M{R:.1f} 0A{R:.1f} {R:.1f} 0 1 1 {-R:.1f} 0A{R:.1f} {R:.1f} 0 1 1 {R:.1f} 0"/></circle>')
        o.append(f'<g transform="translate({s["x"]:.0f} {s["y"]:.0f})" class="c{i}" opacity="{s["op"]:.2f}">'
                 f'<circle r="{s["r"]*2.6:.1f}" fill="url(#gl{i})"/>{ring}'
                 f'<path class="tw" style="animation-duration:{dur:.1f}s;animation-delay:-{delay:.1f}s" fill="currentColor" d="{star_path(s["r"])}"/></g>')

    for name, x, y, anchor in place_labels(stars):
        o.append(f'<text class="lab" x="{x:.0f}" y="{y:.0f}" text-anchor="{anchor}" opacity=".9">{name}</text>')

    o.append('<g transform="translate(24 20)"><g class="shoot"><g transform="rotate(8)">'
             '<path d="M-110 0L0 -1.3L0 1.3Z" fill="url(#tail)"/><circle r="7" fill="url(#hg)"/>'
             f'<path fill="#fff" d="{star_path(3.4)}"/></g></g></g>')
    o.append(f'<text class="cap" x="18" y="{H-12}">my projects form Orion · ringed stars are projects I contribute to · orbiting dot: quantum</text>')
    o.append("</svg>")
    return "\n".join(o)

def promote_team_repos(own, oss):
    """Team repos with enough merged PRs join Orion; their size uses your commit count."""
    keep = []
    for e in oss:
        if e["n"] < TEAM_MIN_PRS:
            keep.append(e)
            continue
        try:
            e["n"] = commit_count(e["full"]) or e["n"]
        except Exception:
            pass
        own.append(e)
    return own, keep

if __name__ == "__main__":
    own, oss = (demo_own(), demo_oss()) if DEMO else promote_team_repos(live_own(), live_oss())
    if not own:
        sys.exit("No repos with commits found.")
    open(OUT, "w", encoding="utf-8").write(build(own, oss))
    print(f"Wrote {OUT}: {min(len(own), len(ORDER))} own + {min(len(oss), len(OSS_SLOTS))} open-source stars ({'demo' if DEMO else 'live'})")
