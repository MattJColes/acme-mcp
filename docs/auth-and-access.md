# Authentication and access control

## Summary

Every request passes through two checks. Authentication verifies the bearer token and establishes who is calling. Authorization maps the token's `groups` claim to component tags, which controls what the caller can discover and execute.

The same access function runs during discovery and use:

| Request | Result when access is allowed | Result when access is denied |
| --- | --- | --- |
| `tools/list`, `resources/list`, `prompts/list` | The component appears | The component is removed from the response |
| `tools/call`, `resources/read`, `prompts/get` | The request continues | FastMCP returns an authorization error |

Components include individual tools and category facades such as `perform_maths`. Without a matching tag, FastMCP removes the component from discovery and rejects direct use when someone guesses its name.

## Example

A finance token contains this claim:

```json
{"sub": "finance@acme.dev", "groups": ["finance"]}
```

`tags_for_groups(["finance"])` returns:

```text
billing, english, maths, public, reports
```

The caller can use components carrying any of those tags. The category facades hide their member tools from the top-level listing, so the finance caller currently receives these tool names:

```text
export_report
get_invoice
perform_english
perform_maths
whoami
```

The same caller cannot see or call `issue_refund`, which carries the `admin` tag. Any authenticated caller can call `whoami` because it carries the `public` tag.

With `groups: ["engineering"]`, the listing contains only `whoami`. `perform_maths` and `issue_refund` stay out of the listing, and direct calls to either fail the same access check.

## Technical detail

### Token verification

`build_auth` in `src/acme_mcp/auth.py` selects the verifier from `ACME_MCP_ENV`.

In `dev`, FastMCP's `StaticTokenVerifier` accepts the fixed tokens in `DEV_TOKENS`. These tokens are local test data and have the same security properties as hardcoded passwords. Do not use them with real data.

Every other environment uses `JWTVerifier`. It reads the JSON Web Key Set URI from `ACME_MCP_JWKS_URI`, the expected issuer from `ACME_MCP_ISSUER`, and the expected audience from `ACME_MCP_AUDIENCE`.

Once verification succeeds, the access layer reads the `groups` claim from the verified token. It never reads group data from request parameters or tool arguments.

### Mapping groups to tags

Tools and resources receive domain tags when they are registered. `GROUP_TAGS` maps organisation groups to the domains they can use:

```python
GROUP_TAGS = {
    "support": {"orders", "billing", "support", "reports", "maths", "english"},
    "finance": {"billing", "reports", "maths", "english"},
    "admin": {ALL_TAGS},
}
```

`tags_for_groups` unions the grants for every recognised group and adds `PUBLIC_TAGS`. Unknown groups contribute no domain grants.

`admin` uses the `ALL_TAGS` wildcard. New domains therefore become available to administrators without changing the mapping. Other groups need an explicit grant.

### Normalising the groups claim

Token claims are untrusted input. `_normalize_groups` accepts the common shapes and fails closed for everything else:

| `groups` value | Normalised groups | Effective access |
| --- | --- | --- |
| missing or `null` | `[]` | `public` only |
| `"admin"` | `["admin"]` | all tags and `public` |
| `["admin", 7]` | `["admin"]` | all tags and `public` |
| `42` or `{"team": "admin"}` | `[]` | `public` only |

A scalar string needs special handling because iterating it would produce individual characters. Mixed collections keep their string members and discard the rest. An unexpected type never grants access.

### The access decision

`group_access` in `src/acme_mcp/access.py` is the only authorization rule:

```python
def group_access(ctx: AuthContext) -> bool:
    if ctx.token is None:
        return False

    allowed = tags_for_groups(ctx.token.claims.get("groups"))
    if ALL_TAGS in allowed:
        return True

    component_tags = set(ctx.component.tags)
    if skill_info := getattr(ctx.component, "skill_info", None):
        component_tags.update(skill_info.frontmatter.get("tags", []))
    return bool(component_tags & allowed)
```

An unauthenticated request returns `False`. An authenticated request passes when it has the wildcard or one of its allowed tags matches a component tag.

FastMCP 3.4 stores skill tags in skill frontmatter. Component tags do not include them. The `skill_info` fallback includes the frontmatter tags in the same decision. Remove that fallback when the provider exposes skill tags directly.

### Middleware order and auditing

`build_server` registers middleware in this order:

```python
mcp.add_middleware(AuditLog())
mcp.add_middleware(HideFacadeMembers(facades))
mcp.add_middleware(build_access_middleware())
```

FastMCP executes the access middleware before the facade-hiding middleware processes the returned listing. This means `HideFacadeMembers` only hides members behind a facade that the caller can see.

`AuditLog` wraps the full call, including access failures. A denied tool call therefore produces an audit entry such as:

```text
AUDIT tool=issue_refund user=user@acme.test groups=['engineering'] error=AuthorizationError
```

### Current visibility

The in-memory client tests produce these counts:

| Groups claim | Tools listed | Resources listed |
| --- | ---: | ---: |
| unauthenticated | 0 | 0 |
| `["engineering"]` | 1 | 0 |
| `["finance"]` | 5 | 6 |
| `["support"]` | 8 | 6 |
| `["admin"]` | 9 | 6 |

`engineering` has no entry in `GROUP_TAGS`, so it receives only the public `whoami` tool. Tool grouping explains why finance and support see fewer tool names than their tag grants allow. See [Tool grouping and surfacing](tool-grouping.md).

### Known name-disclosure behaviour

FastMCP's built-in authorization errors reveal whether a denied tool name exists:

```text
tools/call issue_refund
  Authorization failed for tool 'issue_refund': insufficient permissions

tools/call definitely_not_a_tool
  Authorization failed for tool 'definitely_not_a_tool': not found or not authorized
```

The difference exposes component names. It does not expose their data or execute them. `test_denied_call_names_the_tool` records this current behaviour.

Applications whose threat model includes name disclosure need middleware that returns the same error for denied and unknown components. This example stays with FastMCP's built-in middleware, so the distinction remains visible.

`openspec/specs/access-control/spec.md` still requires `Unknown tool: <name>` for every denied call. The implementation no longer meets that requirement. Resolving the mismatch needs a threat-model decision: normalise the errors in middleware or update the requirement after accepting name disclosure.

### Adding a domain or group

Tag a new domain at registration:

```python
@reports_server.tool(tags={"reports"})
def export_report(...): ...
```

Grant an existing tag to a new group in `GROUP_TAGS`:

```python
GROUP_TAGS["engineering"] = {"orders", "reports"}
```

Administrators receive the new domain through `ALL_TAGS`. Every other group remains restricted until its mapping includes the new tag.

### Verification

Run the access tests with the project virtual environment:

```bash
.venv/bin/python -m pytest -q tests/test_auth.py tests/test_access.py tests/test_audit.py tests/test_facades.py
```

Run the complete suite before changing the group mapping or middleware order:

```bash
.venv/bin/python -m pytest -q
```
