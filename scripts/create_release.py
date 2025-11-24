#!/usr/bin/env python3
"""
create_release_github.py

Usage:
  python3 create_release_github.py --source develop --version v1.2.3
"""
import os, time, argparse, requests, sys

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPOSITORY")  # owner/repo
API_BASE = f"https://api.github.com/repos/{REPO}"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True, help="Source branch (usually develop)")
parser.add_argument("--version", required=False, help="Optional tag version to create (vX.Y.Z)")
args = parser.parse_args()

def get_branch_sha(branch):
    url = f"{API_BASE}/git/ref/heads/{branch}"
    r = requests.get(url, headers=HEADERS)
    if r.ok:
        return r.json()["object"]["sha"]
    # fallback
    url = f"{API_BASE}/git/refs/heads/{branch}"
    r = requests.get(url, headers=HEADERS)
    if r.ok:
        return r.json()["object"]["sha"]
    return None

def create_branch(name, sha):
    url = f"{API_BASE}/git/refs"
    payload = {"ref": f"refs/heads/{name}", "sha": sha}
    r = requests.post(url, headers=HEADERS, json=payload)
    if r.ok:
        print(f"✔ Created branch {name}")
        return True
    print(f"[ERROR] Create branch failed: {r.status_code} {r.text}")
    return False

def create_pr(source, target="main", title=None):
    url = f"{API_BASE}/pulls"
    payload = {"head": source, "base": target, "title": title or f"Release {source}"}
    r = requests.post(url, headers=HEADERS, json=payload)
    if r.ok:
        print(f"✔ Created PR #{r.json()['number']}")
        return True
    print(f"[ERROR] Create PR failed: {r.status_code} {r.text}")
    return False

def create_tag(branch, version):
    # create lightweight tag pointing to branch head sha
    sha = get_branch_sha(branch)
    if not sha:
        print("[ERROR] Cannot determine sha to tag")
        return False
    url = f"{API_BASE}/git/refs"
    payload = {"ref": f"refs/tags/{version}", "sha": sha}
    r = requests.post(url, headers=HEADERS, json=payload)
    if r.ok:
        print(f"🏷 Created tag {version}")
        return True
    print(f"[ERROR] Tag create failed: {r.status_code} {r.text}")
    return False

if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN not set")
        sys.exit(1)

    src = args.source
    ts = time.strftime("%Y.%m.%d.%H%M%S")
    release_branch = f"release/{ts}"
    print("Creating release branch:", release_branch)

    sha = get_branch_sha(src)
    if not sha:
        print(f"[ERROR] Cannot get SHA for source branch {src}")
        sys.exit(1)

    ok = create_branch(release_branch, sha)
    if not ok:
        sys.exit(1)

    create_pr(release_branch, "main", f"Automated Release {release_branch}")

    if args.version:
        create_tag(release_branch, args.version)
