"""Product catalog and inventory generation for The Sanctuary."""
from __future__ import annotations
import random
from typing import List, Optional

from marketplace.models import Product

DEVICE_CATALOG = {
    "laptop": [
        {"brand": "Apple", "model": "MacBook Air M2", "storage_gb": 256, "ram_gb": 8, "base_value": 950},
        {"brand": "Apple", "model": "MacBook Air M2", "storage_gb": 512, "ram_gb": 16, "base_value": 1200},
        {"brand": "Apple", "model": "MacBook Pro M3", "storage_gb": 512, "ram_gb": 18, "base_value": 1600},
        {"brand": "Lenovo", "model": "ThinkPad X1 Carbon", "storage_gb": 256, "ram_gb": 16, "base_value": 850},
        {"brand": "Lenovo", "model": "ThinkPad X1 Carbon", "storage_gb": 512, "ram_gb": 16, "base_value": 950},
        {"brand": "Dell", "model": "XPS 15", "storage_gb": 512, "ram_gb": 16, "base_value": 900},
        {"brand": "Dell", "model": "XPS 13", "storage_gb": 256, "ram_gb": 8, "base_value": 650},
        {"brand": "HP", "model": "Spectre x360", "storage_gb": 512, "ram_gb": 16, "base_value": 780},
        {"brand": "Microsoft", "model": "Surface Pro 9", "storage_gb": 256, "ram_gb": 8, "base_value": 720},
        {"brand": "ASUS", "model": "ZenBook Pro Duo", "storage_gb": 512, "ram_gb": 16, "base_value": 820},
    ],
    "phone": [
        {"brand": "Apple", "model": "iPhone 15 Pro", "storage_gb": 256, "base_value": 900},
        {"brand": "Apple", "model": "iPhone 14 Pro", "storage_gb": 256, "base_value": 720},
        {"brand": "Apple", "model": "iPhone 14", "storage_gb": 128, "base_value": 550},
        {"brand": "Apple", "model": "iPhone 13", "storage_gb": 128, "base_value": 420},
        {"brand": "Samsung", "model": "Galaxy S23 Ultra", "storage_gb": 256, "base_value": 780},
        {"brand": "Samsung", "model": "Galaxy S23", "storage_gb": 128, "base_value": 520},
        {"brand": "Google", "model": "Pixel 8 Pro", "storage_gb": 256, "base_value": 650},
        {"brand": "Google", "model": "Pixel 7", "storage_gb": 128, "base_value": 400},
        {"brand": "OnePlus", "model": "12", "storage_gb": 256, "base_value": 480},
        {"brand": "Samsung", "model": "Galaxy A54", "storage_gb": 128, "base_value": 280},
    ],
    "tablet": [
        {"brand": "Apple", "model": "iPad Air M2", "storage_gb": 256, "base_value": 680},
        {"brand": "Apple", "model": "iPad Pro M4", "storage_gb": 256, "base_value": 950},
        {"brand": "Apple", "model": "iPad (10th gen)", "storage_gb": 64, "base_value": 380},
        {"brand": "Samsung", "model": "Galaxy Tab S9 Ultra", "storage_gb": 256, "base_value": 780},
        {"brand": "Samsung", "model": "Galaxy Tab S9", "storage_gb": 128, "base_value": 520},
        {"brand": "Microsoft", "model": "Surface Pro 9", "storage_gb": 256, "base_value": 750},
        {"brand": "Lenovo", "model": "Tab P12 Pro", "storage_gb": 256, "base_value": 420},
        {"brand": "Amazon", "model": "Fire HD 10 Plus", "storage_gb": 32, "base_value": 120},
        {"brand": "Google", "model": "Pixel Tablet", "storage_gb": 128, "base_value": 380},
        {"brand": "Xiaomi", "model": "Pad 6 Pro", "storage_gb": 256, "base_value": 380},
    ],
}

COSMETIC_MULTIPLIER = {"mint": 1.00, "good": 0.83, "fair": 0.65, "poor": 0.45}
FUNCTIONAL_MULTIPLIER = {"perfect": 1.00, "minor_issues": 0.88, "significant_issues": 0.68}
COSMETIC_CONDITIONS = ["mint", "good", "fair", "poor"]
FUNCTIONAL_CONDITIONS = ["perfect", "minor_issues", "significant_issues"]
COSMETIC_WEIGHTS = [0.15, 0.45, 0.30, 0.10]
FUNCTIONAL_WEIGHTS = [0.55, 0.30, 0.15]

DEFECTS_BY_TYPE = {
    "laptop": ["keyboard has sticky key", "screen has minor scratch", "battery drains faster than spec", "trackpad occasionally unresponsive", "one USB port loose", "fan louder than normal"],
    "phone": ["screen has minor crack at corner", "camera lens scratched", "Face ID slower than normal", "charging port slightly loose", "speaker occasionally crackles", "back glass cracked"],
    "tablet": ["screen has scratch", "home button stiff", "charging port bent pin", "speaker grille dented", "pencil port not working", "screen has minor dead pixel"],
}


def generate_product(seller_id: str, device_type: str, rng: random.Random, specialty: str = "") -> Product:
    catalog = DEVICE_CATALOG[device_type]
    # Sellers know their specialty items better — weighted toward specialty
    spec = rng.choice(catalog)

    true_cosmetic = rng.choices(COSMETIC_CONDITIONS, COSMETIC_WEIGHTS)[0]
    true_functional = rng.choices(FUNCTIONAL_CONDITIONS, FUNCTIONAL_WEIGHTS)[0]
    true_battery = rng.randint(55, 98)
    includes_charger = rng.random() > 0.25
    includes_box = rng.random() > 0.65
    has_defect = rng.random() < 0.3
    true_defects = rng.choice(DEFECTS_BY_TYPE.get(device_type, [""])) if has_defect else ""

    base = spec["base_value"]
    cosm_mult = COSMETIC_MULTIPLIER[true_cosmetic]
    func_mult = FUNCTIONAL_MULTIPLIER[true_functional]
    batt_mult = 1.0 if true_battery >= 80 else (0.93 if true_battery >= 65 else 0.84)
    charger_adj = 15 if includes_charger else 0
    fair_market_value = base * cosm_mult * func_mult * batt_mult + charger_adj
    fair_market_value = round(fair_market_value, 2)

    # Wholesale cost: 55-72% of fair market value (seller margin opportunity)
    wholesale_frac = rng.uniform(0.55, 0.72)
    wholesale_cost = round(fair_market_value * wholesale_frac, 2)

    p = Product(
        seller_id=seller_id,
        device_type=device_type,
        brand=spec["brand"],
        model=spec["model"],
        storage_gb=spec.get("storage_gb", 0),
        ram_gb=spec.get("ram_gb"),
        true_cosmetic=true_cosmetic,
        true_functional=true_functional,
        true_battery_health=true_battery,
        includes_charger=includes_charger,
        includes_box=includes_box,
        true_defects=true_defects,
        wholesale_cost=wholesale_cost,
        fair_market_value=fair_market_value,
    )
    return p


def generate_initial_inventory(seller_id: str, specialty: str, counts: dict, rng: random.Random) -> List[Product]:
    """Generate a seller's complete fixed inventory at simulation start.

    counts: {"laptop": N, "phone": N, "tablet": N}
    """
    inventory = []
    for device_type, count in counts.items():
        for _ in range(count):
            p = generate_product(seller_id, device_type, rng, specialty=specialty)
            inventory.append(p)
    rng.shuffle(inventory)
    return inventory
