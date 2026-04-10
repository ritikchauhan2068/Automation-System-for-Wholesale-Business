"""
Quick test to verify the parser works without any external dependencies.
Run: python test_parser.py
"""
import sys
sys.path.insert(0, ".")

from app.models.schemas import OrderRequest
from app.services.parser import parse_order, parse_with_regex

# ── Test cases ────────────────────────────────────────────────

SAMPLE_ORDERS = [
    # Clean structured input
    """
    Sugar 5 kg @40
    Basmati Rice 10 kg 55
    Cooking Oil 3 litre 120
    """,
    # Messy WhatsApp-style input
    """
    Bhai ye order dena
    - dal chana 25kg rate 65
    - atta 50 kg @32
    - namak 10kg
    maheena end pe payment
    """,
    # Mixed format
    """
    Order from Ram Stores 9876543210
    1. Soap (Lux) - 5 box - 480rs
    2. Shampoo sachets 10 pkt @12
    3. Biscuits 20 pcs 8
    """,
]


def run_tests():
    print("\n" + "="*60)
    print("  WHOLESALE ORDER PARSER — TEST RESULTS")
    print("="*60)

    for i, order_text in enumerate(SAMPLE_ORDERS, 1):
        print(f"\n📋 TEST {i}:")
        print("-" * 40)
        print("INPUT:")
        print(order_text.strip())
        print("\nPARSED ITEMS:")

        items, warnings = parse_with_regex(order_text)

        if items:
            for item in items:
                price_str = f"₹{item.price_per_unit}" if item.price_per_unit else "price missing"
                unit_str = item.unit or ""
                print(f"  ✅ {item.item_name:<20} | {item.quantity} {unit_str:<6} | {price_str}")
        else:
            print("  ❌ No items parsed")

        if warnings:
            print("\nWARNINGS:")
            for w in warnings:
                print(f"  ⚠️  {w}")

    print("\n" + "="*60)
    print("  TESTS COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_tests()
