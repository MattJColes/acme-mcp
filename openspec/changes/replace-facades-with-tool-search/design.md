## Context

See `proposal.md` for the motivation. The server currently mounts seven domain servers into one un-namespaced MCP surface. Domain tags drive group-based access checks for tools and companion skills. Two facade tools then hide the maths and English members from `tools/list` and dispatch member calls through an untyped dictionary.

Tool search is a host capability rather than an MCP server capability. Claude and OpenAI both support deferred native tool definitions, but their request formats differ. Their documented searches use tool names, descriptions, and argument schemas; neither provider documents arbitrary FastMCP tags as searchable input.

## Goals / Non-Goals

**Goals:**

- Preserve tags as the single definition of domain membership and the input to server-side access filtering.
- Return every permitted native tool with its original typed schema.
- Explain how tag filtering narrows the catalogue before a capable host performs tool search.
- Give engineers provider-specific configuration examples without coupling the server to either provider.

**Non-Goals:**

- Implement search, ranking, or session-specific tool loading inside the MCP server.
- Rename native tools or add category prefixes solely for one provider's search implementation.
- Claim that providers index FastMCP tags.
- Add OpenAI or Anthropic SDK dependencies or make network calls in tests.

## Decisions

### Expose native tools and remove facade dispatch

`build_server` will stop registering `perform_maths` and `perform_english` and stop installing `HideFacadeMembers`. The maths and English tools will appear directly after the existing tag-based access middleware approves them.

This preserves each tool's concrete input schema and lets a host defer, discover, and call it by its real name. Keeping facades alongside native tools would add definitions without reducing context. Hiding members behind facades would remove them from the host's searchable catalogue.

### Use tags for server-side grouping

Tags will continue to answer two server questions: which domain owns this component, and whether the caller's group grants access to that domain. This creates the first stage of discovery by removing whole unauthorized domains before the host sees the catalogue.

The second stage belongs to the host. Tool search matches the permitted tools using their names, descriptions, and argument schemas. The guide will state this boundary directly. It will show the flow as `identity groups -> allowed domain tags -> permitted native tools -> host tool search -> typed tool call`.

Automatic name prefixes were considered because they can improve text search. They would change every public tool name and duplicate information already carried by tags. The current names and descriptions identify the operations clearly, so this change keeps them stable. Search quality can be measured before adopting a naming migration.

### Keep provider configuration outside the server

The guide will include concise configurations for Claude's MCP toolset deferred loading and OpenAI's deferred MCP tool loading. These settings belong to the application making the model request. The FastMCP server will stay provider-neutral and dependency-free.

The examples will use the same native catalogue and state that access filtering still applies to listing and execution. A client without tool search receives the complete permitted catalogue through normal MCP discovery.

### Keep companion skills as tagged resources

Removing the facades also removes the response that paired a category's tools with skill URIs. Skills will remain standard MCP resources carrying the same domain tags, and the existing access middleware will keep filtering them. The guide will describe tool search and skill discovery as separate host concerns.

## Risks / Trade-offs

- [Existing callers invoke a facade] -> Mark the removal as breaking and document the direct native tool names.
- [Clients without tool search receive more schemas] -> State the catalogue-size trade-off and retain the facade pattern in the guide as an alternative for hosts that cannot defer tools.
- [Engineers assume tags improve provider ranking] -> State which metadata providers document as searchable and show tags as the authorization pre-filter.
- [Provider request formats change] -> Link each example to official documentation and avoid adding executable provider-specific code to the server.
- [Removing facades weakens skill discovery] -> Keep skills as tagged resources and explain that hosts list or retrieve resources separately.

## Migration Plan

1. Remove the facade factory, hiding middleware, and facade-specific tests.
2. Update discovery tests to assert that callers see and call permitted native tools with their original schemas.
3. Rewrite the grouping guide with the tag-filtering and host-search flow, direct-call examples, and provider configuration examples.
4. Remove the obsolete facade spec anchor and verify every remaining anchor resolves once.

Rollback consists of reverting the change, which restores both facade tool names and the previous listing behaviour.
