## Why

The category facades reduce the initial `tools/list` response, but they hide the native typed tools that Claude and OpenAI tool search need to discover. Domain tags already provide a single server-side grouping mechanism for access control, so the server can expose the permitted native tools and leave deferred loading to capable hosts.

## What Changes

- **BREAKING** Remove `perform_maths` and `perform_english`; callers use the native maths and English tools directly.
- Remove `HideFacadeMembers` and return every native tool permitted by the caller's tag grants from `tools/list`.
- Keep domain tags as the source of truth for grouping tools, companion skills, and group-based access control.
- Rewrite the grouping guide around the two-stage flow: tags restrict the permitted domains, then a capable host searches the remaining native tool definitions. Explain that current provider searches use names, descriptions, and argument schemas rather than arbitrary MCP tags.
- Add Claude and OpenAI configuration examples without adding either provider SDK to the server.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `category-facades`: Remove the facade discovery and dispatch contract.
- `composition`: Expose mounted domain tools directly and remove facade-specific assembly and middleware.

## Impact

The change affects server assembly, facade middleware, maths and English discovery tests, and `docs/tool-grouping.md`. It removes two public tool names and their broad `operation`/`arguments` interface. Native tools retain their existing names, schemas, domain tags, authorization, audit behaviour, and companion skill resources. No provider SDK or runtime dependency is added because tool search is configured by the MCP host.
