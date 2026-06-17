"""Orders domain: read-only lookups about a customer's orders.

This sub-server exposes the support-facing, non-privileged order tools. The
``OrdersBackend`` here stands in for whatever the real deployment reads from --
a DynamoDB ``orders`` table or an internal order-management API. We keep it an
in-memory dict so tests need no AWS; swapping in a real client later means
giving ``_backend`` something with the same ``get`` shape.
"""

from __future__ import annotations

from fastmcp import FastMCP

orders_server = FastMCP("orders")


class OrdersBackend:
    """In-memory stand-in for the orders data store.

    Mirrors a DynamoDB ``get_item`` shape: ``get(order_id)`` returns the stored
    item or ``None`` when there's no such key.
    """

    def __init__(self) -> None:
        # In production this would be a DynamoDB table keyed by order_id.
        self._orders: dict[str, dict] = {
            "A1": {"order_id": "A1", "status": "shipped"},
            "A2": {"order_id": "A2", "status": "processing"},
        }

    def get(self, order_id: str) -> dict | None:
        return self._orders.get(order_id)


# Module-level default backend; tests may replace or pre-seed this.
_backend = OrdersBackend()


@orders_server.tool(tags={"orders"})
def order_status(order_id: str) -> dict:
    """Look up the current status of an order by its id.

    Returns the order id and its status; status is ``"not_found"`` when no
    order with that id exists.
    """
    item = _backend.get(order_id)
    if item is None:
        return {"order_id": order_id, "status": "not_found"}
    return {"order_id": item["order_id"], "status": item["status"]}
