# SEO Autopilot AI – Architecture

## High-Level

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────┐
│  Next.js UI │────▶│  FastAPI API │────▶│ Master Orchestrator │
└─────────────┘     └──────────────┘     └──────────┬──────────┘
                                                    │
        ┌───────────┬───────────┬───────────┬───────┴───────┐
        ▼           ▼           ▼           ▼               ▼
   Crawler     Technical   On-Page     Content         Keyword
   Agent       SEO Agent   SEO Agent   Agent           Agent
        │           │           │           │               │
        └───────────┴───────────┴───────────┴───────────────┘
                              │
                    ┌─────────▼─────────┐
                    │ PostgreSQL + Redis│
                    │ Celery Workers    │
                    └───────────────────┘
```

## Multi-Tenant Model

- **User** → belongs to one or more **Organizations** via OrganizationMember
- **Organization** owns **Websites**
- Each Website has CrawlRuns, Pages, SEOScores, Issues, Keywords, Recommendations, Changes, Integrations, Reports

## Agent Pipeline (Orchestrator)

1. Validate URL (SSRF protection)
2. Discover robots.txt / sitemap / tech stack
3. Crawl (Playwright) with rate limits & max pages
4. Technical SEO analysis
5. On-page SEO analysis
6. Content analysis
7. Keyword research
8. Schema generation
9. Internal linking graph
10. Performance signals
11. Recommendation prioritization
12. Optional auto-fix (with approval gates)
13. Report generation
14. Continuous monitoring schedule

## Safety

- SSRF protection on every user-supplied URL
- Crawl limits (pages, depth, delay)
- Auto-approve only safe changes
- Full audit log
- Never claim guaranteed rankings

## Tech Stack

| Layer        | Choice                          |
|--------------|---------------------------------|
| Frontend     | Next.js 16, TypeScript, Tailwind|
| Backend      | Python 3.12, FastAPI            |
| Database     | PostgreSQL 16                   |
| Jobs         | Celery + Redis                  |
| Crawler      | Playwright + BeautifulSoup      |
| AI           | Provider abstraction            |
| Auth         | JWT + bcrypt                    |
| Deploy       | Docker Compose / any cloud      |
