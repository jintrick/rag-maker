---
source_url: https://github.com/kagisearch/kagi-docs/blob/3fb47e284426fbd356307197717b5f167d3e868c/docs/kagi/api/search.md
original_title: search
fetched_at: 2026-06-21T02:50:46.179753+00:00
---

# Search API

The Search API gives programmable access to Kagi's premium search results.

## API Reference

The full Search API reference is available at **[kagi.com/api/docs](https://kagi.com/api/docs)**.

## Example

```shell
curl -H "Authorization: Bot $TOKEN" \
  "https://kagi.com/api/v1/search?q=kagi+search"
```

## Additional Settings

The Search API inherits settings from your account. For example:

- Block or promote websites ([results personalization](https://help.kagi.com/kagi/getting-started/index.html))
- Select longer or shorter search snippets ([Settings → Search](https://help.kagi.com/kagi/settings/search.html))

## Legacy API

The previous v0 Search API is documented in [Search API (Legacy)](search-legacy.md).
