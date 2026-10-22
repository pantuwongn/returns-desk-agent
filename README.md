# returns-desk

The support assistant of Northwind Goods, an online furniture shop. It answers a customer's
message with Gemini (through Google's OpenAI-compatible endpoint) and four tools:

| Tool | What it does |
|---|---|
| `lookup_order` | an order's item, amount, status and address |
| `get_product` | a product's price, cost price and stock |
| `process_refund` | refunds a delivered order, asking a manager first when the amount needs it |
| `update_address` | changes the address of an order not yet delivered |

The shop's policies are in the system prompt in `returns_desk/agent.py`; the tools and data are in
`returns_desk/shop.py`.

Every run is traced in OpenInference form (an `AGENT` root, `LLM` and `TOOL` steps).

```bash
pip install -e .
GOOGLE_API_KEY=... python -m returns_desk "Hi, I'd like a refund for order N-1004."
```
