#!/usr/bin/env python3
"""
Pulls the numbers for the stats cards straight from GitHub's GraphQL API
(the same data your profile's contribution graph uses) and writes generator/stats.json.

Needs the env var GITHUB_TOKEN (the workflow provides it) and GH_USER (your username).
"""
import datetime, json, os, sys, urllib.request

API = "https://api.github.com/graphql"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
USER = os.environ.get("GH_USER", "")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats.json")


def gql(query, variables):
    req = urllib.request.Request(
        API, data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": "bearer " + TOKEN, "Content-Type": "application/json", "User-Agent": "profile-builder"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data["data"]


Q_MAIN = """
query($login:String!){ user(login:$login){
  createdAt
  followers{ totalCount }
  pullRequests{ totalCount }
  issues{ totalCount }
  contributionsCollection{ totalCommitContributions }
  repositories(ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC, first:100){
    totalCount
    nodes{ stargazerCount languages(first:12, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name } } } }
  }
}}"""

Q_YEAR = """
query($login:String!,$from:DateTime!,$to:DateTime!){ user(login:$login){
  contributionsCollection(from:$from, to:$to){
    contributionCalendar{ weeks{ contributionDays{ date contributionCount } } }
  }
}}"""


def streaks(days, today):
    """days: {date: count}. Returns (current, longest) as dicts with n/start/end."""
    def cnt(d):
        return days.get(d, 0)
    one = datetime.timedelta(days=1)
    # current streak (today may still be empty, then count from yesterday)
    d = today if cnt(today) > 0 else today - one
    end = d
    n = 0
    while cnt(d) > 0:
        n += 1
        d -= one
    cur = {"n": n, "start": (d + one).isoformat() if n else "", "end": end.isoformat() if n else ""}
    # longest streak
    best = {"n": 0, "start": "", "end": ""}
    if days:
        d, last = min(days), max(days)
        run, start = 0, None
        while d <= last:
            if cnt(d) > 0:
                if run == 0:
                    start = d
                run += 1
                if run > best["n"]:
                    best = {"n": run, "start": start.isoformat(), "end": d.isoformat()}
            else:
                run = 0
            d += one
    return cur, best


def build(main, year_blocks, today):
    u = main["user"]
    created = datetime.date.fromisoformat(u["createdAt"][:10])
    days = {}
    for blk in year_blocks:
        for w in blk["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for dd in w["contributionDays"]:
                days[datetime.date.fromisoformat(dd["date"])] = dd["contributionCount"]
    cur, longest = streaks(days, today)
    active = sorted(d for d, c in days.items() if c > 0)
    langs = {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    return {
        "login": USER, "created": created.isoformat(),
        "repos": u["repositories"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in u["repositories"]["nodes"]),
        "followers": u["followers"]["totalCount"],
        "prs": u["pullRequests"]["totalCount"], "issues": u["issues"]["totalCount"],
        "commits_year": u["contributionsCollection"]["totalCommitContributions"],
        "total_contrib": sum(days.values()),
        "first_day": (active[0] if active else created).isoformat(),
        "cur_streak": cur, "longest": longest,
        "langs": sorted(langs.items(), key=lambda kv: -kv[1]),
        "updated": today.isoformat(),
    }


def main():
    if not TOKEN or not USER:
        sys.exit("GITHUB_TOKEN and GH_USER are required")
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    m = gql(Q_MAIN, {"login": USER})
    first_year = int(m["user"]["createdAt"][:4])
    blocks = []
    for y in range(first_year, today.year + 1):
        frm = f"{y}-01-01T00:00:00Z"
        to = now.strftime("%Y-%m-%dT%H:%M:%SZ") if y == today.year else f"{y}-12-31T23:59:59Z"
        blocks.append(gql(Q_YEAR, {"login": USER, "from": frm, "to": to}))
    stats = build(m, blocks, today)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=1)
    print("stats.json written:", {k: v for k, v in stats.items() if k != "langs"})


if __name__ == "__main__":
    main()
