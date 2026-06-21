"""Admin domain: privileged writes such as issuing refunds.

This is the sensitive sub-server -- its tools mutate state and are gated to the
``admin`` group by the group-tag filter middleware. The ``AdminBackend`` stands
in for the real write target: a DynamoDB ``put_item`` against a refunds table or
an internal payments API. It's an in-memory list so tests can assert that a
refund was actually recorded; a real deployment would give ``_backend``
something with the same ``record_refund`` shape.
"""

from __future__ import annotations

from fastmcp import FastMCP

admin_server = FastMCP("admin")


class AdminBackend:
    """In-memory stand-in for the privileged write store.

    ``record_refund`` mirrors a DynamoDB ``put_item``: it appends a refund
    record keyed by order id, which ``list_refunds`` can read back.
    """

    def __init__(self) -> None:
        # In production this would be a DynamoDB ``refunds`` table.
        self._refunds: list[dict] = []

    def record_refund(self, order_id: str, amount: float) -> dict:
        record = {"order_id": order_id, "amount": amount}
        self._refunds.append(record)
        return record

    def list_refunds(self, order_id: str | None = None) -> list[dict]:
        if order_id is None:
            return list(self._refunds)
        return [r for r in self._refunds if r["order_id"] == order_id]


# Module-level default backend; tests may replace or pre-seed this.
_backend = AdminBackend()


@admin_server.tool(tags={"admin"})
def issue_refund(order_id: str, amount: float) -> dict:
    """Issue a refund against an order (privileged write).

    Records the refund in the backend and returns a confirmation with the
    refunded amount and a ``"refund_issued"`` status.
    """
    _backend.record_refund(order_id, amount)
    return {"order_id": order_id, "refunded": amount, "status": "refund_issued"}
