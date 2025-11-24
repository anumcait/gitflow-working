#!/usr/bin/env python3
"""
auto_merge_github.py

Usage:
  python3 auto_merge_github.py --action feature_to_develop --branch feature/abc
  python3 auto_merge_github.py --action hotfix_to_main_and_dev --branch hotfix/1
  python3 auto_merge_github.py --action promote_release --branch release/2025.11.20.120000 --hold-hours 0.01 --tag-version v1.2.3
"""
import os
import time
import argparse
import requests
import sys

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPOSITORY")  # owner/repo
if not REPO:
    print("ERROR: GITHUB_REPOSITORY env must be set (owner/repo).")
    sys.exit(1)
API_BASE = f"https://api.github.com/repos/{REPO}"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

parser = argparse.ArgumentParser()
parser.add_argument(
    "--action",
    required=True,
    choices=["feature_to_develop", "promote_release", "hotfix_to_main_and_dev"],
)
parser.add_argument("--branch", required=True)
parser.add_argument("--hold-hours", type=float, default=0)
parser.add_argument("--tag-version", type=str, default=None)
args = parser.parse_args()

MAX_RETRIES = 8
RETRY_INTERVAL = 15  # seconds


def get_open_pr(source, target):
    # GitHub: filter by head (owner:branch)
    owner = REPO.split("/")[0]
    head = f"{owner}:{source}"
    url = f"{API_BASE}/pulls?state=open&head={head}&base={target}"
    r = requests.get(url, headers=HEADERS)
    if r.ok and r.json():
        return r.json()[0]
    return None


def create_pr(source, target, title=None, body=None):
    payload = {
        "head": source,
        "base": target,
        "title": title or f"Auto PR: {source} → {target}",
        "body": body or "",
    }
    url = f"{API_BASE}/pulls"
    r = requests.post(url, headers=HEADERS, json=payload)
    if r.ok:
        pr = r.json()
        print(f"✔ Created PR #{pr['number']} {pr['html_url']}")
        return pr
    print(f"[ERROR] Create PR failed: {r.status_code} {r.text}")
    return None


def get_pr(number):
    url = f"{API_BASE}/pulls/{number}"
    r = requests.get(url, headers=HEADERS)
    return r.json() if r.ok else None


def try_merge_pr(number):
    pr = get_pr(number)
    if not pr:
        print("[ERROR] PR not found")
        return False
    # GitHub 'mergeable' may be null initially; poll
    poll = 0
    while pr.get("mergeable") is None and poll < 10:
        time.sleep(3)
        pr = get_pr(number)
        poll += 1
    if not pr.get("mergeable"):
        print(f"⚠ PR #{number} is not mergeable. state: {pr.get('mergeable_state')}")
        return False
    # Attempt merge
    url = f"{API_BASE}/pulls/{number}/merge"
    r = requests.put(url, headers=HEADERS, json={"merge_method": "merge"})
    if r.ok:
        print(f"✅ PR #{number} merged")
        return True
    print(f"[WARN] Merge attempt failed: {r.status_code} {r.text}")
    return False


def create_ref(branch, sha):
    url = f"{API_BASE}/git/refs"
    payload = {"ref": f"refs/heads/{branch}", "sha": sha}
    r = requests.post(url, headers=HEADERS, json=payload)
    return r.ok


def get_ref_sha(branch):
    url = f"{API_BASE}/git/ref/heads/{branch}"
    r = requests.get(url, headers=HEADERS)
    if r.ok:
        return r.json()["object"]["sha"]
    # fallback to heads path
    url = f"{API_BASE}/git/refs/heads/{branch}"
    r = requests.get(url, headers=HEADERS)
    if r.ok:
        return r.json()["object"]["sha"]
    return None


def tag_release(branch, version):
    # create tag referencing latest commit of branch
    sha = get_ref_sha(branch)
    if not sha:
        print("[ERROR] Cannot get sha for branch", branch)
        return False
    url = f"{API_BASE}/git/refs"
    payload = {"ref": f"refs/tags/{version}", "sha": sha}
    r = requests.post(url, headers=HEADERS, json=payload)
    if r.ok:
        print(f"🏷 Created tag {version} -> {sha}")
        return True
    print(f"[ERROR] Tag creation failed: {r.status_code} {r.text}")
    return False


def ensure_pr_and_merge(source, target, create_if_missing=True, tag_version=None):
    pr = get_open_pr(source, target)
    if not pr and create_if_missing:
        pr = create_pr(source, target)
    if not pr:
        print("❌ No PR available")
        return False
    number = pr["number"]
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"🔁 Attempt {attempt}/{MAX_RETRIES} to merge PR #{number}")
        if try_merge_pr(number):
            if tag_version and target == "main":
                tag_release(target, tag_version)
            return True
        time.sleep(RETRY_INTERVAL)
    print("❌ Failed to auto-merge after retries")
    return False


def main():
    action = args.action
    src = args.branch
    if action == "feature_to_develop":
        print(f"Feature -> develop: {src} -> develop")
        ensure_pr_and_merge(src, "develop")
        return

    if action == "hotfix_to_main_and_dev":
        print(f"Hotfix -> main AND develop: {src} -> main")
        ok = ensure_pr_and_merge(src, "main")
        if ok:
            print("Now also creating/merging to develop...")
            ensure_pr_and_merge(src, "develop")
        return

    if action == "promote_release":
        print(f"Promote release branch {src} to main (with preprod hold)")
        hold = args.hold_hours
        if hold and float(hold) > 0:
            sec = int(float(hold) * 3600)
            print(f"⏳ Holding for {sec}s before promotion (preprod validation)")
            time.sleep(sec)
        # Create PR to main and attempt merge
        ok = ensure_pr_and_merge(src, "main", tag_version=args.tag_version)
        if ok:
            # Also ensure merge back to develop
            ensure_pr_and_merge(src, "develop")
        return


if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print(
            "ERROR: GITHUB_TOKEN not set in env. Provide a personal token as secret if needed."
        )
        sys.exit(1)
    main()
