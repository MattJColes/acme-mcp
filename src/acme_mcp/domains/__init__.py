"""Per-domain sub-servers, mounted into the main server in :mod:`acme_mcp.server`.

Splitting tools across domain sub-servers keeps each domain small and
independently testable, and keeps the surface any one caller sees relevant.
"""
