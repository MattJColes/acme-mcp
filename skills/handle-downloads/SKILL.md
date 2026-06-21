---
name: handle-downloads
description: How to handle a download_url returned by an acme-mcp tool. Use whenever a tool result contains a "download_url" field (for example from export_report) — present it to the user as a link, mention the expiry, and never read the file into context.
---

# Handling file downloads from acme-mcp

Some acme-mcp tools (such as `export_report`) generate a file, upload it to S3,
and return a **short-lived signed download URL** instead of the file's bytes.
The bytes deliberately go around you, not through you.

When a tool result looks like:

```json
{ "download_url": "https://acme-mcp-exports.s3.amazonaws.com/reports/q1.pdf?...", "expires_in": 300 }
```

do this:

1. **Present the `download_url` to the user as a clickable link.** That is the
   deliverable — hand it over directly.
2. **Mention the expiry.** The link is valid for `expires_in` seconds (the
   example uses 300, i.e. five minutes), so tell the user to use it promptly.
3. **Do NOT fetch or read the file into context.** Never download the URL to
   inspect or summarize its contents unless the user explicitly asks. Pulling a
   large file into the conversation defeats the whole point of returning a link:
   it blows up context and costs money.
4. **Do not log, echo, or share the URL beyond the requesting user.** A signed
   URL is a bearer credential to that one object for its short lifetime.

If the link has likely expired (the user comes back later), call the tool again
to mint a fresh one rather than reusing the old URL.

This skill supplies the *direction*; the MCP server supplies the file *safely*.
Together they keep large files out of the model while still getting them to the
person who asked.
