from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GitHubRepoSnapshot:
    """Normalized repository fields used by the GitHub opencode crawler."""

    github_repo_id: int
    full_name: str
    owner: str
    repo_name: str
    html_url: str
    description: str | None
    language: str | None
    stargazers_count: int
    forks_count: int
    open_issues_count: int
    pushed_at: str | None
    updated_at: str | None
    created_at: str | None

    @classmethod
    def from_api_item(cls, item: dict) -> GitHubRepoSnapshot:
        owner = item.get("owner") or {}
        return cls(
            github_repo_id=int(item["id"]),
            full_name=str(item["full_name"]),
            owner=str(owner.get("login") or "").strip(),
            repo_name=str(item["name"]),
            html_url=str(item["html_url"]),
            description=item.get("description"),
            language=item.get("language"),
            stargazers_count=int(item.get("stargazers_count") or 0),
            forks_count=int(item.get("forks_count") or 0),
            open_issues_count=int(item.get("open_issues_count") or 0),
            pushed_at=item.get("pushed_at"),
            updated_at=item.get("updated_at"),
            created_at=item.get("created_at"),
        )

    def repository_row(self) -> dict:
        return {
            "github_repo_id": self.github_repo_id,
            "full_name": self.full_name,
            "owner": self.owner,
            "repo_name": self.repo_name,
            "html_url": self.html_url,
            "description": self.description,
            "language": self.language,
            "stargazers_count": self.stargazers_count,
            "forks_count": self.forks_count,
            "open_issues_count": self.open_issues_count,
            "pushed_at": self.pushed_at,
            "updated_at": self.updated_at,
            "created_at": self.created_at,
        }
