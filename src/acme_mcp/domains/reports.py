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

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from acme_mcp import storage

reports_server = FastMCP("reports")

EXPORT_BUCKET = "acme-mcp-exports"
EXPORT_EXPIRES_IN = 300  # seconds

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

    ``report_id`` becomes part of the S3 key, so it is validated: a blank id or
    one carrying path separators is rejected rather than used to build a key
    outside the ``reports/`` prefix the signer is scoped to.
    """
    if not report_id or not report_id.strip():
        raise ToolError("report_id is required")
    if "/" in report_id or "\\" in report_id or ".." in report_id:
        raise ToolError("report_id must not contain path separators")

    key = f"reports/{report_id}.pdf"
    data = _build_report(report_id)

    storage.upload_bytes(key, data, bucket=EXPORT_BUCKET, client=_s3_client)
    url = storage.presigned_url(
        key,
        bucket=EXPORT_BUCKET,
        expires_in=EXPORT_EXPIRES_IN,
        client=_s3_client,
    )
    return {"download_url": url, "expires_in": EXPORT_EXPIRES_IN}
