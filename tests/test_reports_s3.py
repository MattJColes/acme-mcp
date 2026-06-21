"""Tests for file delivery via S3 presigned URLs.

This covers the blog post's "getting files to people" pattern: a tool that
produces a file must NOT return the bytes through the model's context. Instead
it uploads to S3 and returns a short-lived presigned download URL -- the bytes
go *around* the model, not through it.

S3 is faked with moto so no network/credentials are needed. moto 5's
``mock_aws`` is used as a context manager inside each (async) test body, which
wraps reliably regardless of pytest-asyncio's event loop handling.
"""

from __future__ import annotations

import boto3
from fastmcp import Client
from moto import mock_aws

from acme_mcp import storage
from acme_mcp.domains import reports

BUCKET = "acme-mcp-exports"


# --- storage.presigned_url (unit) -------------------------------------------

def test_presigned_url_contains_key():
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        url = storage.presigned_url("reports/q1.pdf", client=s3)
    assert isinstance(url, str)
    assert "reports/q1.pdf" in url
    assert BUCKET in url


def test_presigned_url_has_signature_and_expiry():
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        url = storage.presigned_url("reports/q1.pdf", client=s3, expires_in=300)
    # A presigned URL carries a signature and an expiry, whether SigV4
    # (X-Amz-Signature / X-Amz-Expires) or the older SigV2 (Signature / Expires).
    assert "Signature=" in url
    assert ("X-Amz-Expires=300" in url) or ("Expires=" in url)


def test_upload_bytes_round_trips():
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        storage.upload_bytes("reports/r.pdf", b"hello-pdf", client=s3)
        obj = s3.get_object(Bucket=BUCKET, Key="reports/r.pdf")
        assert obj["Body"].read() == b"hello-pdf"


# --- reports.export_report (tool, in-memory client) ------------------------

async def test_export_report_returns_url_not_bytes():
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        reports.set_s3_client(s3)
        try:
            async with Client(reports.reports_server) as client:
                result = await client.call_tool("export_report", {"report_id": "q1"})
        finally:
            reports.set_s3_client(None)

    data = result.data
    assert "download_url" in data
    assert isinstance(data["download_url"], str)
    assert "reports/q1.pdf" in data["download_url"]
    assert data["expires_in"] == 300

    # CRITICAL: the bytes must NOT travel through the model's context.
    assert "bytes" not in data
    assert "content" not in data
    assert "data" not in data
    # No value in the returned dict should be raw bytes.
    assert not any(isinstance(v, (bytes, bytearray)) for v in data.values())


async def test_export_report_actually_uploads_object():
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        reports.set_s3_client(s3)
        try:
            async with Client(reports.reports_server) as client:
                await client.call_tool("export_report", {"report_id": "q1"})
            # get_object succeeds only if the upload really happened.
            obj = s3.get_object(Bucket=BUCKET, Key="reports/q1.pdf")
            body = obj["Body"].read()
            assert len(body) > 0
        finally:
            reports.set_s3_client(None)


def _tags(tool) -> set:
    """Tags as carried on the client-side tool representation (under meta)."""
    return set((tool.meta or {}).get("fastmcp", {}).get("tags", []))


async def test_export_report_tool_is_tagged_reports():
    async with Client(reports.reports_server) as client:
        tools = {t.name: t for t in await client.list_tools()}
    assert "export_report" in tools
    assert "reports" in _tags(tools["export_report"])
