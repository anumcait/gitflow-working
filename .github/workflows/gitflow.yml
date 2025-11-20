name: GitFlow Auto Release

on:
  push:
    branches:
      - 'feature/**'

permissions:
  contents: write
  pull-requests: write

jobs:
  feature_to_dev:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install deps
        run: pip install requests

      - name: Run Tests (Dummy)
        run: |
          echo "Running tests..."
          sleep 3
          echo "Tests PASSED"

      - name: Auto-merge Feature → Dev
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
          FEATURE_BRANCH: ${{ github.ref_name }}
        run: |
          python3 << 'EOF'
          import os, requests

          token = os.environ["GITHUB_TOKEN"]
          repo  = os.environ["REPO"]
          branch = os.environ["FEATURE_BRANCH"]

          headers = {
              "Authorization": f"Bearer {token}",
              "Accept": "application/vnd.github+json"
          }

          # Create PR feature → dev
          pr_data = {
              "title": f"Auto Merge Feature {branch} → dev",
              "head": branch,
              "base": "dev",
              "body": "Automated by GitHub Actions."
          }

          r = requests.post(f"https://api.github.com/repos/{repo}/pulls",
                            json=pr_data, headers=headers)
          print("PR Response:", r.text)
          EOF

      - name: Auto-Create Release Branch & MR
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
        run: |
          python3 << 'EOF'
          import requests, os, datetime

          token = os.environ["GITHUB_TOKEN"]
          repo = os.environ["REPO"]

          headers = {
              "Authorization": f"Bearer {token}",
              "Accept": "application/vnd.github+json"
          }

          # release branch version
          version = datetime.datetime.utcnow().strftime("release-%Y%m%d-%H%M")

          # 1️⃣ Create release branch from latest dev
          dev_ref = requests.get(
              f"https://api.github.com/repos/{repo}/git/ref/heads/dev",
              headers=headers,
          ).json()
          sha = dev_ref["object"]["sha"]

          create_branch = requests.post(
              f"https://api.github.com/repos/{repo}/git/refs",
              headers=headers,
              json={"ref": f"refs/heads/{version}", "sha": sha},
          )

          print("Release branch created:", create_branch.text)

          # 2️⃣ Create PR Release → Dev
          pr_data = {
              "title": f"Release {version} → dev",
              "head": version,
              "base": "dev",
              "body": "Automated release branch creation.",
          }

          pr = requests.post(
              f"https://api.github.com/repos/{repo}/pulls",
              headers=headers,
              json=pr_data
          )
          print("Release PR:", pr.text)

          EOF
