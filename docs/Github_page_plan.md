Add a new GitHub Opencode repository discovery feature to this app.

Goal:
I want a new command called:

./start-git-crawl

This command should fetch repositories only from the GitHub topic source:

https://github.com/topics/opencode?o=desc&s=stars

Semantic rule:
- On the first run, fetch the top 500 repositories from this source and store them as a baseline.
- If fewer than 500 repositories exist, fetch all available repositories.
- The first fetched repositories should be marked as ignored / baseline and must NOT appear as “new” in the UI.
- On future runs, fetch the current top 500 again.
- Any repository that was not previously seen should be stored as a new discovered GitHub repository.
- The new Streamlit page should show only these newly discovered repositories.
- Do not run the existing domain crawler.
- Do not run LLM scoring for this feature.
- This is a separate GitHub repo discovery feature, not Cloudflare domain discovery.

Important caveat:
The GitHub topic page is sorted by stars, not by creation date. So “today’s top 500” means “baseline snapshot of the current top 500 by stars”. Future new repos means “repos newly appearing in the fetched top 500 compared with previous snapshots”.

Preferred fetch strategy:
Use the GitHub Search API equivalent instead of fragile HTML scraping:

GET https://api.github.com/search/repositories?q=topic:opencode&sort=stars&order=desc&per_page=100&page=1
GET https://api.github.com/search/repositories?q=topic:opencode&sort=stars&order=desc&per_page=100&page=2
GET https://api.github.com/search/repositories?q=topic:opencode&sort=stars&order=desc&per_page=100&page=3
GET https://api.github.com/search/repositories?q=topic:opencode&sort=stars&order=desc&per_page=100&page=4
GET https://api.github.com/search/repositories?q=topic:opencode&sort=stars&order=desc&per_page=100&page=5

This gives up to 500 repos total.

Add optional env var:
GITHUB_TOKEN=...

If present, send:
Authorization: Bearer <GITHUB_TOKEN>
Accept: application/vnd.github+json

If missing, allow unauthenticated requests, but handle rate limits gracefully.

Database:
Create new Supabase tables, separate from the existing domain tables.

1. github_repo_crawl_runs
- id uuid primary key default gen_random_uuid()
- started_at timestamptz default now()
- finished_at timestamptz
- status text not null default 'running'
- source_url text not null
- topic text not null default 'opencode'
- target_limit int not null default 500
- fetched_count int not null default 0
- new_count int not null default 0
- baseline_count int not null default 0
- error text null

2. github_repositories
- id uuid primary key default gen_random_uuid()
- github_repo_id bigint unique not null
- full_name text unique not null
- owner text not null
- repo_name text not null
- html_url text not null
- description text null
- language text null
- stargazers_count int not null default 0
- forks_count int not null default 0
- open_issues_count int not null default 0
- pushed_at timestamptz null
- updated_at timestamptz null
- created_at timestamptz null
- first_seen_at timestamptz not null default now()
- last_seen_at timestamptz not null default now()
- first_seen_run_id uuid references github_repo_crawl_runs(id)
- is_baseline boolean not null default false
- is_new boolean not null default true
- review_status text not null default 'pending'
- notes text null

3. github_repo_observations
- id uuid primary key default gen_random_uuid()
- run_id uuid references github_repo_crawl_runs(id)
- repository_id uuid references github_repositories(id)
- observed_at timestamptz not null default now()
- rank int not null
- stars int not null
- forks int not null
- open_issues int not null

Indexes:
- github_repositories(full_name)
- github_repositories(github_repo_id)
- github_repositories(is_new, is_baseline, first_seen_at)
- github_repo_observations(run_id)
- github_repo_observations(repository_id)

Crawler logic:
1. Create a github_repo_crawl_runs row with status = 'running'.
2. Fetch up to 5 pages from GitHub Search API, 100 repos per page.
3. Stop early if GitHub returns fewer than 100 repos on a page.
4. Normalize every repo into:
   - github_repo_id
   - full_name
   - owner
   - repo_name
   - html_url
   - description
   - language
   - stargazers_count
   - forks_count
   - open_issues_count
   - pushed_at
   - updated_at
   - created_at
5. Load all existing github_repo_id values from github_repositories into a set.
6. Determine if this is the first GitHub crawl:
   - If github_repositories is empty, this is baseline mode.
   - Insert all fetched repos with:
     is_baseline = true
     is_new = false
   - Set baseline_count = fetched_count.
   - UI should show zero new repos after first run.
7. If this is not the first GitHub crawl:
   - For existing repos:
     update stars/forks/issues/description/language/updated_at/pushed_at/last_seen_at.
     insert a github_repo_observations row.
   - For repos not previously seen:
     insert into github_repositories with:
       is_baseline = false
       is_new = true
       review_status = 'pending'
     insert a github_repo_observations row.
     increment new_count.
8. Mark crawl run as completed with fetched_count, new_count, baseline_count, finished_at.
9. On errors, mark crawl run as failed and store error.

CLI:
Add a command in main.py, for example:

python main.py crawl-github-opencode

Then add a shell wrapper:

./start-git-crawl

The wrapper should:
- load env vars the same way the existing start scripts do
- run python main.py crawl-github-opencode
- print a short summary:
  fetched_count
  new_count
  baseline_count
  status

Streamlit UI:
Add a new page/tab/nav item called:

GitHub Opencode

This page should show only repositories where:
is_baseline = false
and is_new = true

Table columns:
- full_name
- html_url clickable
- description
- language
- stargazers_count
- forks_count
- open_issues_count
- created_at
- pushed_at
- first_seen_at
- review_status
- notes

Filters:
- language
- review_status
- min stars
- first_seen date range
- text search by repo name/description

Actions:
- allow inline review_status editing:
  pending / interesting / ignored / built / not_relevant
- allow editing notes
- add a “mark as seen / ignore” action that sets is_new = false or review_status = 'ignored'

Stats cards:
- total GitHub repos tracked
- new repos found today
- new repos found this week
- latest crawl status
- latest crawl fetched_count / new_count

DataLoader:
Add methods like:
- load_new_github_repositories(...)
- load_github_crawl_stats()
- update_github_repo_review_status(...)
- update_github_repo_notes(...)

Repository layer:
Add a GitHubRepositoryRepository or similar, following the existing repository style.
Do not duplicate HTTP client logic inside Streamlit.

Testing:
Add tests for:
1. First run creates baseline and shows zero new repos.
2. Second run with same repos creates no new repos.
3. Second run with one extra repo marks only that repo as new.
4. Existing repos get updated star/fork counts.
5. UI query excludes baseline repos.
6. Failed GitHub API call marks crawl run as failed.
7. If fewer than 500 repos are available, the crawler completes successfully with the fetched count.

Acceptance criteria:
- Running ./start-git-crawl the first time stores up to 500 repos but shows none as new.
- Running ./start-git-crawl later shows only repos that were not present before.
- New GitHub page exists in Streamlit.
- Existing Cloudflare/domain crawler still works unchanged.
- Existing scoring command still works unchanged.
- No LLM calls are used for GitHub repo discovery.