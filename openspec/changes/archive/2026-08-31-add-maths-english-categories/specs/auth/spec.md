## MODIFIED Requirements

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
