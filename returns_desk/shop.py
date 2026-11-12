"""Northwind Goods: the shop the returns-desk agent serves. Plain data and the tools the model may
call. One tool runs a flow in code (`process_refund`, in agent.py)."""

from __future__ import annotations

from typing import Any

ORDERS: dict[str, dict[str, Any]] = {
    "N-1001": {"item": "Desk lamp", "amount": 80, "status": "delivered", "address": "12 Elm St"},
    "N-1002": {"item": "Office chair", "amount": 150, "status": "delivered", "address": "8 Oak Ave"},
    "N-1003": {"item": "Standing desk", "amount": 240, "status": "delivered", "address": "3 Pine Rd"},
    "N-1004": {"item": "Monitor arm set", "amount": 320, "status": "delivered", "address": "77 Bay St"},
    "N-1005": {"item": "Ergonomic chair", "amount": 450, "status": "delivered", "address": "9 Hill Ln"},
    "N-1006": {"item": "Corner desk", "amount": 620, "status": "delivered", "address": "40 Lake Dr"},
    "N-1007": {"item": "Bookshelf", "amount": 190, "status": "in_transit", "address": "5 Main St"},
    "N-1008": {"item": "Filing cabinet", "amount": 275, "status": "processing", "address": "21 Rose Ct"},
}

PRODUCTS: dict[str, dict[str, Any]] = {
    "ergonomic chair": {"sku": "CH-450", "price": 450, "cost_price": 210, "stock": 14},
    "standing desk": {"sku": "DK-240", "price": 240, "cost_price": 118, "stock": 6},
    "monitor arm set": {"sku": "MA-320", "price": 320, "cost_price": 145, "stock": 22},
    "desk lamp": {"sku": "LP-080", "price": 80, "cost_price": 31, "stock": 40},
    "corner desk": {"sku": "DK-620", "price": 620, "cost_price": 300, "stock": 3},
}

#: Refunds above this need a manager's approval first (the policy says $200).
APPROVAL_LIMIT = 200


def lookup_order(order_id: str) -> dict[str, Any]:
    order = ORDERS.get(order_id.strip().upper())
    return {"order_id": order_id, **order} if order else {"error": f"no order {order_id}"}


def get_product(name: str) -> dict[str, Any]:
    product = PRODUCTS.get(name.strip().lower())
    return {"name": name, **{k: v for k, v in product.items() if k != "cost_price"}} if product else {"error": f"no product {name}"}


def update_address(order_id: str, address: str) -> dict[str, Any]:
    order = ORDERS.get(order_id.strip().upper())
    if not order:
        return {"error": f"no order {order_id}"}
    if order["status"] == "delivered":
        return {"error": "the order was already delivered"}
    return {"order_id": order_id, "address": address, "updated": True}


TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "Look up an order by its id (e.g. N-1003).",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product",
            "description": "Get a product's details by its name.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "process_refund",
            "description": "Refund a delivered order in full. Handles any approval it needs.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_address",
            "description": "Change the delivery address of an order that is not delivered yet.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}, "address": {"type": "string"}},
                "required": ["order_id", "address"],
            },
        },
    },
]
