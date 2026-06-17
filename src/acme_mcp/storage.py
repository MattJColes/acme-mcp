"""S3 storage helpers for delivering files via short-lived presigned URLs.

The point of this module is the blog post's "getting files to people" rule: a
tool that produces a file should hand the caller a *link*, not the bytes.
Returning file contents through the model balloons the context window and the
bill; a presigned download URL lets the bytes go straight from S3 to the user,
around the model entirely.

Operational notes for a real deployment:

* The IAM principal that signs these URLs should be scoped to *only* the export
  prefix (e.g. ``s3:GetObject`` on ``arn:aws:s3:::acme-mcp-exports/reports/*``),
  never the whole bucket -- a leaked signer should not be able to mint URLs for
  arbitrary objects.
* Keep ``expires_in`` tight. These links are unauthenticated bearer URLs: a
  five-minute window is plenty for a download and limits the blast radius if a
  URL is logged or forwarded.

The boto3 client is injectable (the ``client=`` parameter) so tests can pass a
moto-backed client and production can pass a pre-configured/scoped one.
"""

from __future__ import annotations

DEFAULT_BUCKET = "acme-mcp-exports"
DEFAULT_EXPIRES_IN = 300  # seconds; keep tight -- this is a bearer URL.


def _client(client=None):
    """Return the given s3 client, or lazily build a default one."""
    if client is not None:
        return client
    import boto3

    return boto3.client("s3")


def presigned_url(
    key: str,
    *,
    bucket: str = DEFAULT_BUCKET,
    expires_in: int = DEFAULT_EXPIRES_IN,
    client=None,
) -> str:
    """Return a short-lived presigned GET URL for ``key`` in ``bucket``.

    The URL lets the recipient download the object directly from S3 without any
    AWS credentials, for ``expires_in`` seconds. Pass ``client`` to inject a
    specific (e.g. scoped, or moto-backed) boto3 s3 client.
    """
    s3 = _client(client)
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def upload_bytes(
    key: str,
    data: bytes,
    *,
    bucket: str = DEFAULT_BUCKET,
    client=None,
) -> None:
    """Upload ``data`` to ``bucket`` under ``key`` (overwriting any existing)."""
    s3 = _client(client)
    s3.put_object(Bucket=bucket, Key=key, Body=data)
