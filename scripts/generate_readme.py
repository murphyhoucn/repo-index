#!/usr/bin/env python3
"""
Generate README.md with a table index of all repositories in the GitHub account.

Reads GITHUB_TOKEN and GITHUB_USERNAME from environment variables.
"""

import os
import sys
import requests
from datetime import datetime, timezone


def fetch_repos(username: str, token: str | None = None) -> list[dict]:
    """Fetch all repositories for a given GitHub username."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    repos: list[dict] = []
    page = 1
    while True:
        if token:
            # Use the authenticated /user/repos endpoint when a token is
            # available.  This returns all repositories (public, private, and
            # internal) owned by the authenticated user, provided the token has
            # the `repo` (or `read:repo`) scope.
            url = "https://api.github.com/user/repos"
            params = {
                "per_page": 100,
                "page": page,
                "sort": "updated",
                "direction": "desc",
                "type": "owner",
            }
        else:
            # Fall back to the public endpoint when no token is provided.
            # This only returns public repositories.
            url = f"https://api.github.com/users/{username}/repos"
            params = {
                "per_page": 100,
                "page": page,
                "sort": "updated",
                "direction": "desc",
                "type": "owner",
            }
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
        except requests.exceptions.ConnectionError as exc:
            print(f"ERROR: Network connection failed: {exc}", file=sys.stderr)
            sys.exit(1)
        except requests.exceptions.Timeout:
            print("ERROR: Request to GitHub API timed out.", file=sys.stderr)
            sys.exit(1)
        except requests.exceptions.RequestException as exc:
            print(f"ERROR: Unexpected request error: {exc}", file=sys.stderr)
            sys.exit(1)

        if response.status_code == 401:
            print("ERROR: GitHub token is invalid or missing required permissions.", file=sys.stderr)
            sys.exit(1)
        if response.status_code == 403:
            print("ERROR: Access forbidden. Check that the token has sufficient permissions.", file=sys.stderr)
            sys.exit(1)
        response.raise_for_status()

        data = response.json()
        if not data:
            break
        repos.extend(data)
        page += 1

    return repos


def format_topics(topics: list[str]) -> str:
    """Format topics as Markdown inline code spans."""
    return " ".join(f"`{t}`" for t in topics) if topics else "-"


def generate_readme(repos: list[dict], username: str) -> str:
    """Build the full README.md content."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = len(repos)

    lines = [
        f"# {username}'s Repository Index",
        "",
        f"> Auto-generated index of all repositories owned by **{username}**.",
        f"> Last updated: **{now}** &nbsp;|&nbsp; Total: **{total}** repositories",
        "",
        "## Repository List",
        "",
        "| Repository | Topics / Tags | Last Updated |",
        "|:-----------|:--------------|:------------:|",
    ]

    for repo in repos:
        name = repo.get("name", "")
        url = repo.get("html_url", "")
        topics: list[str] = repo.get("topics") or []
        updated_raw: str = repo.get("updated_at") or ""
        updated_at = updated_raw[:10] if updated_raw else "-"

        tags_str = format_topics(topics)

        lines.append(
            f"| [{name}]({url}) | {tags_str} | {updated_at} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "*This file is automatically maintained by "
        "[GitHub Actions](../../actions/workflows/update-readme.yml). "
        "Do not edit manually.*"
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    username = os.environ.get("GITHUB_USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER")

    if not username:
        print("ERROR: GITHUB_USERNAME or GITHUB_REPOSITORY_OWNER must be set.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching repositories for user: {username}")
    repos = fetch_repos(username, token)
    print(f"Found {len(repos)} repositories.")

    readme_content = generate_readme(repos, username)

    readme_path = os.path.join(os.path.dirname(__file__), "..", "README.md")
    readme_path = os.path.normpath(readme_path)

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"README.md written to {readme_path}")


if __name__ == "__main__":
    main()
