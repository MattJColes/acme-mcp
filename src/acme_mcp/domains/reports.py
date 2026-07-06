"""Reports domain: produce a file and hand back a download *link*, not bytes.

This is the worked example of the "getting files to people" pattern. The
``export_report`` tool builds a report file, uploads it to S3, and returns a
short-lived presigned URL plus its expiry -- and *nothing else*. The file bytes
deliberately never appear in the tool's return value, so they never enter the
model's context (which would be slow and expensive). The user downloads the
file straight from S3 via the URL.

Injection seam
--------------
The boto3 s3 client is taken from a module-level slot that tests (or a real
``build_server``) can set via :func:`set_s3_client`. When unset, ``None`` is
passed down to :mod:`acme_mcp.storage`, which lazily builds a default client.
Tests point this at a moto-backed bucket; nothing here touches the network on
its own.
"""

from __future__ import annotations

import logging
import re

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from acme_mcp import storage

log = logging.getLogger("acme_mcp.reports")

reports_server = FastMCP("reports")

EXPORT_BUCKET = "acme-mcp-exports"
EXPORT_EXPIRES_IN = 300  # seconds

# ``report_id`` is interpolated into an S3 key, so it is validated against a
# strict allowlist rather than a denylist of known-bad characters. An allowlist
# is the only safe way to build a key from caller input: it admits exactly the
# characters that produce a predictable ``reports/<id>.pdf`` key and rejects
# everything else -- path separators, whitespace, control bytes (NUL/CR/LF that
# would corrupt an S3 key or a downstream log line), and non-ASCII look-alikes --
# without having to enumerate every dangerous character. Because no separator can
# get through, prefix escape is impossible, so no separate ``..`` guard is needed
# (and legitimate ids with dots, like ``2024.q1``, are no longer false-rejected).
_SAFE_REPORT_ID = re.compile(r"[A-Za-z0-9._-]+")
MAX_REPORT_ID_LEN = 128  # S3 keys cap at 1024 bytes; stay well under with margin.

# Injection seam: the s3 client the tool should use. ``None`` => storage builds
# a default boto3 client lazily. Tests set this to a moto-backed client.
_s3_client = None


def set_s3_client(client) -> None:
    """Set (or clear, with ``None``) the s3 client used by ``export_report``."""
    global _s3_client
    _s3_client = client


def _build_report(report_id: str) -> bytes:
    """Build the report file's bytes.

    Stand-in for real rendering (a PDF/CSV builder). These bytes are exactly
    what we must keep *out* of the model's context -- they go to S3, not back
    through the tool return.
    """
    body = f"ACME report {report_id}\nGenerated for internal use.\n"
    return body.encode("utf-8")


@reports_server.tool(tags={"reports"})
def export_report(report_id: str) -> dict:
    """Export a report and return a short-lived download URL for it.

    The report is uploaded to S3 and the caller receives a presigned
    ``download_url`` plus ``expires_in`` (seconds). The file bytes are NEVER
    returned -- delivering large files through the model's context is slow and
    expensive, so the bytes go around the model via the signed URL.

    ``report_id`` becomes part of the S3 key, so it is validated against a strict
    allowlist: a blank, over-long, or otherwise unsafe id (path separators,
    whitespace, control characters, non-ASCII) is rejected rather than used to
    build a key outside the ``reports/`` prefix the signer is scoped to.
    """
    if not report_id or not report_id.strip():
        raise ToolError("report_id is required")
    if len(report_id) > MAX_REPORT_ID_LEN:
        raise ToolError("report_id is too long")
    if not _SAFE_REPORT_ID.fullmatch(report_id):
        raise ToolError(
            "report_id may only contain letters, digits, '.', '-', and '_'"
        )

    key = f"reports/{report_id}.pdf"
    data = _build_report(report_id)

    try:
        storage.upload_bytes(key, data, bucket=EXPORT_BUCKET, client=_s3_client)
        url = storage.presigned_url(
            key,
            bucket=EXPORT_BUCKET,
            expires_in=EXPORT_EXPIRES_IN,
            client=_s3_client,
        )
    except Exception:
        # Never surface raw storage/AWS errors to the caller (and thus the
        # model): a boto ``ClientError`` carries the bucket name, the operation,
        # and the AWS error code -- internal detail that should stay server-side.
        # Log it for operators, return an opaque failure to the caller. Only the
        # storage calls run in this block, and they raise boto/OS errors, never
        # ``ToolError`` -- the input ``ToolError``s are raised above, before the try.
        log.exception("export_report failed for report_id=%r", report_id)
        raise ToolError("report export failed") from None
    return {"download_url": url, "expires_in": EXPORT_EXPIRES_IN}
