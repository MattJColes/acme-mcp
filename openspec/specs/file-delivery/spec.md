# File Delivery Specification

## Purpose

Deliver files as short-lived S3 signed links, never as bytes through the
MCP channel. Report ids are allowlist-validated so they cannot escape the
`reports/` key prefix, and storage failures surface as one opaque error so
AWS detail never reaches the caller or the model.

## Requirements

### Requirement: Export returns a link, never bytes

<!-- anchor: reports.export-report --> `export_report` SHALL be a `reports`-tagged tool that builds the report
server-side, uploads it to the export bucket under `reports/<id>.pdf`, and
returns ONLY `{download_url, expires_in}`. It SHALL validate `report_id`
(non-blank, max 128 chars, full match of `[A-Za-z0-9._-]+`) before any
storage call, and SHALL mask storage failures as the opaque `ToolError`
"report export failed".

#### Scenario: Result carries a URL, not content
- **WHEN** `export_report` succeeds
- **THEN** the result has `download_url` and `expires_in` and no bytes/
  content/data fields

#### Scenario: Traversal-shaped ids rejected before upload
- **WHEN** called with ids like `../secret`, `a/b`, whitespace, NUL, or
  over-length input
- **THEN** a `ToolError` is raised and nothing is written to storage

#### Scenario: Storage errors are opaque
- **GIVEN** the S3 client raises during upload or signing
- **WHEN** the tool fails
- **THEN** the caller sees only "report export failed" — no bucket, AWS
  error code, or operation name

### Requirement: Short-lived presigned GET URLs

<!-- anchor: storage.presigned-url --> `presigned_url` SHALL generate a presigned `get_object` URL for a key,
expiring after `DEFAULT_EXPIRES_IN` (300 seconds) unless overridden, and
SHALL return only the URL string.

#### Scenario: URL is signed and expiring
- **WHEN** a URL is generated for an uploaded key
- **THEN** it references the bucket and key and carries signature and
  expiry parameters

### Requirement: Uploads stay server-side

<!-- anchor: storage.upload-bytes --> `upload_bytes` SHALL put report bytes into the bucket via the injected (or
lazily-created) S3 client and return `None` — bytes go up, never back out.

#### Scenario: Upload round-trips in storage only
- **WHEN** bytes are uploaded to a key
- **THEN** fetching that key from storage returns them, and the function
  itself returns nothing
