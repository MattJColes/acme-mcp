# Auth Specification

## Purpose

Authenticate every caller and translate their identity-provider groups into
the set of domain tags they may use. Verification is environment-aware
(static dev tokens vs JWT in prod) and group handling fails closed: a
malformed token can only lose access, never gain it.

## Requirements

### Requirement: Environment-aware token verification

<!-- anchor: auth.verifier-split --> The server SHALL choose its token verifier from `ACME_MCP_ENV`: `dev` uses a
`StaticTokenVerifier` with fixed dev tokens (`dev-support`, `dev-finance`,
`dev-admin`, each carrying a `groups` claim); any other value uses a
`JWTVerifier` configured from `ACME_MCP_JWKS_URI`, `ACME_MCP_ISSUER`, and
`ACME_MCP_AUDIENCE`. Static tokens are a dev-only convenience and SHALL NOT
be accepted outside `dev`.

#### Scenario: Dev builds a static verifier
- **WHEN** `build_auth` runs with env `dev`
- **THEN** it returns a `StaticTokenVerifier` loaded with the dev tokens

#### Scenario: Prod builds a JWT verifier
- **WHEN** `build_auth` runs with env `prod` (or anything not `dev`)
- **THEN** it returns a `JWTVerifier` using the JWKS/issuer/audience env vars

### Requirement: Group-to-tag clearance map

<!-- anchor: auth.group-tags --> Clearance SHALL be declared in one map, `GROUP_TAGS`: `support` →
`{orders, billing, support, reports, maths, english}`; `finance` →
`{billing, reports, maths, english}`; `admin` → the wildcard `ALL_TAGS`
(`"*"`) rather than an explicit list, so admin stays a true superset that
covers later-composed domains without the map being edited.

#### Scenario: Functional domains available to both groups
- **WHEN** the `support` and `finance` entries of `GROUP_TAGS` are read
- **THEN** both contain `maths` and `english`
- **AND** their pre-existing domain grants remain unchanged

#### Scenario: Admin clearance is the wildcard
- **WHEN** the `admin` entry of `GROUP_TAGS` is read
- **THEN** it contains `ALL_TAGS`, not an enumeration of domain tags

### Requirement: Default-deny tag resolution

<!-- anchor: auth.default-deny --> `allowed_tags` SHALL resolve the caller's tags from the access token in
context: no token yields the empty set (default deny); a token yields the
union of its groups' tags from `GROUP_TAGS` plus `PUBLIC_TAGS`, so every
authenticated caller can use `public`-tagged tools and unknown groups get
only those.

#### Scenario: Unauthenticated caller has no tags
- **GIVEN** no access token in the request context
- **WHEN** `allowed_tags` is called
- **THEN** it returns the empty set

#### Scenario: Unknown group gets public only
- **GIVEN** a token whose groups match nothing in `GROUP_TAGS`
- **WHEN** `allowed_tags` is called
- **THEN** it returns exactly `PUBLIC_TAGS`

### Requirement: Fail-closed groups-claim normalization

<!-- anchor: auth.fail-closed-groups --> The `groups` claim SHALL be normalized before use, and normalization SHALL
fail closed: `None` becomes `[]`, a bare string becomes a one-group list,
list/tuple/set inputs keep only their string members, and any other type
becomes `[]`. A malformed claim never crashes a request and never widens
access.

#### Scenario: Null claim is harmless
- **GIVEN** a token with `groups: null`
- **WHEN** the claim is normalized
- **THEN** the caller has no groups and requests still succeed

#### Scenario: Scalar string claim is one group
- **GIVEN** a token with `groups: "admin"`
- **WHEN** the claim is normalized
- **THEN** the caller is treated as being in the single group `admin`
