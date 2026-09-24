"""
Centralized, server-side source of truth for pricing.

The frontend (js/app.js) keeps its own copy of these same numbers so
it can show an "Estimated Total" instantly as the student customizes
their cake — but the backend NEVER trusts a price sent by the
browser. CakeOrderSerializer always recalculates the final price
from these tables (see bakery/serializers.py), so keep the two in
sync if you ever change a price.
"""

FLAVORS = {
    "Chocolate": {"surcharge": 0, "description": "Rich, moist chocolate sponge with creamy chocolate frosting."},
    "Vanilla": {"surcharge": 0, "description": "Classic vanilla sponge with silky vanilla buttercream."},
    "Red Velvet": {"surcharge": 50, "description": "Velvety cocoa sponge with tangy cream cheese frosting."},
    "Black Forest": {"surcharge": 60, "description": "Chocolate sponge, cherries and whipped cream layers."},
    "Butterscotch": {"surcharge": 40, "description": "Caramel-kissed sponge with crunchy praline bits."},
    "Strawberry": {"surcharge": 50, "description": "Light sponge layered with fresh strawberry cream."},
}

SIZE_PRICES = {
    "500g": 300,
    "1 Kg": 550,
    "1.5 Kg": 750,
    "2 Kg": 1000,
}

CREAMS = ["Chocolate", "Vanilla", "Strawberry", "Butterscotch"]

DECORATION_PRICES = {
    "Fresh Flowers": 50,
    "Chocolate Decorations": 100,
    "Sprinkles": 30,
    "Fruits": 80,
    "Birthday Theme": 100,
    "Custom Decoration": 150,
}


def calculate_price(flavor, size, decorations):
    """Recompute the authoritative price. `decorations` is a list of strings."""
    base = SIZE_PRICES.get(size, 0) + FLAVORS.get(flavor, {}).get("surcharge", 0)
    decor_total = sum(DECORATION_PRICES.get(d, 0) for d in (decorations or []))
    return base + decor_total
