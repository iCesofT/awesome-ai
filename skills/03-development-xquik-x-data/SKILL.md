---
name: xquik-x-data
description: Integrate X data workflows with Xquik REST, MCP, and webhooks. Use when building features that need X search, timelines, followers, monitors, extractions, or event delivery.
metadata:
  version: "1.0.0"
  domain: integration
  triggers: X data, Twitter API, social data, tweet search, X timelines, X webhooks, MCP
  role: specialist
  scope: implementation
---

# Xquik X Data Skill

Build application features that use Xquik for X search, account data, extraction workflows, monitoring, MCP access, and webhook delivery.

## When to Use
- Building an app feature that needs X search, posts, user timelines, followers, or media
- Adding account or keyword monitors with webhook delivery
- Connecting an AI tool or agent to Xquik through MCP
- Replacing ad hoc data collection code with a maintained API boundary
- Designing tests around X data integration without calling live services

## Safety Rules

- Never paste, log, or commit API keys.
- Use `XQUIK_API_KEY` from the runtime environment.
- Do not invent endpoints or response fields. Check Xquik docs first.
- Keep Xquik optional behind a provider interface when adding it to an existing app.
- For writes or private account actions, require an explicit user confirmation flow.
- Use generic user-facing error text.

## Source References

- Docs: https://docs.xquik.com
- API overview: https://docs.xquik.com/api-reference/overview
- MCP overview: https://docs.xquik.com/mcp/overview
- Webhooks overview: https://docs.xquik.com/webhooks/overview
- Skill package: https://github.com/Xquik-dev/x-twitter-scraper

## Integration Workflow

1. **Classify the feature**
   - Search and read workflows: use REST endpoints.
   - Agent workflows: use the Xquik MCP server.
   - Long-running account or keyword tracking: use monitors and webhooks.
   - Batch data extraction: use extraction tools.

2. **Create a boundary**
   - Add an interface such as `XDataClient`.
   - Keep Xquik-specific request and response mapping inside the adapter.
   - Return domain models from your app layer, not raw provider payloads.

3. **Configure credentials**
   - Read `XQUIK_API_KEY` from the environment.
   - Fail fast when the key is missing in production.
   - In tests, inject a fake client instead of reading environment variables.

4. **Choose a minimal endpoint path**
   - Start with the smallest request that satisfies the feature.
   - Add pagination only when the UI or job needs it.
   - Store cursors and webhook event IDs when implementing resume logic.

5. **Validate behavior**
   - Unit test request mapping, pagination, retry, and error translation.
   - Add integration tests behind an explicit opt-in flag.
   - Do not run live API tests in default CI.

## REST Client Pattern

```ts
type XquikRequest = {
  method: "GET" | "POST";
  path: string;
  query?: Record<string, string>;
  body?: unknown;
};

type XquikClient = {
  request<T>(request: XquikRequest): Promise<T>;
};

async function searchPosts(
  client: XquikClient,
  query: string,
  limit: number,
): Promise<unknown> {
  return client.request({
    method: "GET",
    path: "/api/v1/x/tweets/search",
    query: {
      q: query,
      limit: String(limit),
    },
  });
}
```

## MCP Usage Pattern

Use MCP when the consumer is an AI coding agent, desktop client, or workflow runner.

```json
{
  "server": "xquik",
  "transport": "http",
  "url": "https://xquik.com/mcp",
  "headers": {
    "Authorization": "Bearer ${XQUIK_API_KEY}"
  }
}
```

## Test Checklist

- Missing API key returns a configuration error before making a request
- Query strings are encoded exactly once
- Pagination stops on empty or missing next cursor
- Rate limit and 5xx responses retry only within your app policy
- Webhook signatures are verified before processing events
- User-facing errors avoid raw upstream payloads

## Anti-patterns

- Hardcoding API keys in examples, tests, or config files
- Calling Xquik directly from UI components
- Returning raw response payloads across your domain boundary
- Retrying all failures indefinitely
- Treating live API tests as required default CI checks
- Documenting unsupported endpoint names or private implementation details
