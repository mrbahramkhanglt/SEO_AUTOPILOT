# WordPress integration

## Auth
- WordPress 5.6+ **Application Passwords** (Users → Profile)
- HTTPS required (except localhost)
- Never use the main login password

## API (Autopilot backend)

| Endpoint | Purpose |
|----------|---------|
| `POST /api/integrations/wordpress/test` | Verify credentials + detect SEO surface |
| `POST /api/integrations/wordpress/list` | List pages or posts (`context=edit`) |
| `POST /api/integrations/wordpress/meta` | Dry-run (default) or apply SEO meta |
| `POST /api/integrations/wordpress/graphql-seo` | Optional WPGraphQL Yoast-style read |

### Meta body example
```json
{
  "site_url": "https://example.com",
  "username": "editor",
  "app_password": "xxxx xxxx xxxx xxxx xxxx xxxx",
  "content_type": "pages",
  "item_id": 42,
  "title": "Optimized title | Brand",
  "description": "Benefit-led meta under 155 chars.",
  "dry_run": true,
  "force_overwrite": false
}
```

Conflicts (existing non-empty meta ≠ proposed) **block apply** unless `force_overwrite: true`.

## Required for writes
Install `docs/wordpress-meta-bridge.php` as a must-use plugin so Yoast/Rank Math keys have `show_in_rest`.

Without it, REST may accept the request but **silently drop** SEO keys.

## GraphQL
Optional richer **reads** if WPGraphQL + Yoast/Rank Math GraphQL addons are installed. Writes still go through REST + bridge.

## Safety
- dry_run default true
- conflict detection
- no ranking guarantees in copy
