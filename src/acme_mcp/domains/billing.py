"""Billing domain: read-only invoice lookups.

This sub-server exposes the finance-facing invoice tools. The ``BillingBackend``
stands in for the real invoice store -- a DynamoDB ``invoices`` table or an
internal billing API. It's an in-memory dict so tests need no AWS; a real
deployment would give ``_backend`` something with the same ``get`` shape.
"""

from __future__ import annotations

from fastmcp import FastMCP

billing_server = FastMCP("billing")


class BillingBackend:
    """In-memory stand-in for the invoice data store.

    Mirrors a DynamoDB ``get_item`` shape: ``get(invoice_id)`` returns the
    stored item or ``None`` when there's no such key.
    """

    def __init__(self) -> None:
        # In production this would be a DynamoDB table keyed by invoice_id.
        self._invoices: dict[str, dict] = {
            "INV-1": {"invoice_id": "INV-1", "amount": 42.0, "status": "paid"},
            "INV-2": {"invoice_id": "INV-2", "amount": 17.5, "status": "open"},
        }

    def get(self, invoice_id: str) -> dict | None:
        return self._invoices.get(invoice_id)


# Module-level default backend; tests may replace or pre-seed this.
_backend = BillingBackend()


@billing_server.tool(tags={"billing"})
def get_invoice(invoice_id: str) -> dict:
    """Look up an invoice by its id.

    Returns the invoice id, amount, and status; status is ``"not_found"`` when
    no invoice with that id exists.
    """
    item = _backend.get(invoice_id)
    if item is None:
        return {"invoice_id": invoice_id, "amount": 0.0, "status": "not_found"}
    return {
        "invoice_id": item["invoice_id"],
        "amount": item["amount"],
        "status": item["status"],
    }
