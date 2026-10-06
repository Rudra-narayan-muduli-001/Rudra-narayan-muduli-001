#!/usr/bin/env python3
"""
Scrape public profile totals from GitHub's unauthenticated REST API and write
data/profile.json: stars earned, PRs authored, issues opened, public repo
count, and repos-per-language for the "most used language" panel.

No token, no auth. Run daily by .github/workflows/update-profile-art.yml.
"""
import datetime
import json
import os
import urllib.parse
import urllib.request
from collections import Counter

USERNAME = os.environ.get("GH_PROFILE_USER", "Rudra-narayan-muduli-001")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "profile.json")


def get(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "profile-readme-bot/1.0",
                      "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def search_total(query):
    q = urllib.parse.quote(query)
    d = get(f"https://api.github.com/search/issues?q={q}&per_page=1")
    return d.get("total_count", 0)


user = get(f"https://api.github.com/users/{USERNAME}")

repos = []
page = 1
while True:
    batch = get(f"https://api.github.com/users/{USERNAME}/repos"
                f"?per_page=100&page={page}&type=owner")
    repos.extend(batch)
    if len(batch) < 100:
        break
    page += 1

stars = sum(r.get("stargazers_count", 0) for r in repos)
langs = Counter(r["language"] for r in repos if r.get("language"))
top_langs = [{"language": lang, "repos": n}
             for lang, n in langs.most_common(6)]

data = {
    "username": USERNAME,
    "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "stars": stars,
    "prs": search_total(f"author:{USERNAME} type:pr"),
    "issues": search_total(f"author:{USERNAME} type:issue"),
    "public_repos": user.get("public_repos", len(repos)),
    "top_languages": top_langs,
}

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w") as f:
    json.dump(data, f, indent=2)
print(f"wrote {OUT_PATH}: {stars} stars, {data['prs']} PRs, "
      f"{data['issues']} issues, {data['public_repos']} repos, "
      f"top lang {top_langs[0]['language'] if top_langs else '—'}")
