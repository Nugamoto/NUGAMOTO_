"""Seed script for the NUGAMOTO SQLite database."""
# Ausführen:  python -m app.db.seed_db

from __future__ import annotations

import hashlib
from datetime import datetime, date, timedelta, UTC
from pathlib import Path
from random import sample

from sqlalchemy import create_engine, MetaData, insert, select


def seed_database(db_path: str | Path = Path("nugamoto.sqlite")) -> None:
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    meta = MetaData()
    meta.reflect(bind=engine)

    # ---- table refs ----
    users = meta.tables["users"]
    kitchens = meta.tables["kitchens"]
    user_kitchens = meta.tables["user_kitchens"]
    units = meta.tables["units"]
    unit_conversions = meta.tables["unit_conversions"]
    food_items = meta.tables["food_items"]
    food_item_unit_conversions = meta.tables["food_item_unit_conversions"]
    storage_locations = meta.tables["storage_locations"]
    device_types = meta.tables["device_types"]
    appliances = meta.tables["appliances"]
    kitchen_tools = meta.tables["kitchen_tools"]
    inventory_items = meta.tables["inventory_items"]
    shopping_lists = meta.tables["shopping_lists"]
    shopping_products = meta.tables["shopping_products"]
    shopping_product_assignments = meta.tables["shopping_product_assignments"]
    user_credentials = meta.tables["user_credentials"]
    user_health_profiles = meta.tables["user_health_profiles"]

    now = datetime.now(UTC)

    with engine.begin() as conn:
        # ---------- units ----------
        base_units = {
            "g": ("weight", 1),
            "ml": ("volume", 1),
        }

        extra_units = {
            "kg": ("weight", 1000),
            "lb": ("weight", 453.592),
            "oz": ("weight", 28.3495),
            "l": ("volume", 1000),
            "tsp": ("measure", 5),
            "tbsp": ("measure", 15),
            "cup": ("measure", 240),
            "slice": ("count", 1),
            "clove": ("count", 1),
            "piece": ("count", 1),
            "head": ("count", 1),  # z.B. für "head of lettuce"
        }

        package_units = {
            "tetra_pak": ("package", 1),
            "dose": ("package", 1),
            "bottle": ("package", 1),
            "bag": ("package", 1),
            "box": ("package", 1),
            "tube": ("package", 1),
            "jar": ("package", 1),
            "can": ("package", 1),  # neu
            "pack": ("package", 1),  # neu
            "cup": ("package", 1),  # neu
            "block": ("package", 1),  # neu
            "package": ("package", 1),
            "bulk": ("package", 1),
        }

        all_units = {**base_units, **extra_units, **package_units}
        conn.execute(insert(units), [
            {"name": name, "type": unit_type, "to_base_factor": factor, "created_at": now}
            for name, (unit_type, factor) in all_units.items()
        ])

        unit_id_map = {r.name: r.id for r in conn.execute(select(units.c.name, units.c.id))}
        unit_factor = {r.id: r.to_base_factor for r in conn.execute(select(units.c.id, units.c.to_base_factor))}

        # ---------- conversions ----------
        conn.execute(insert(unit_conversions), [
            {"from_unit_id": unit_id_map[frm], "to_unit_id": unit_id_map[to], "factor": fac}
            for frm, to, fac in [
                ("kg", "g", 1000), ("lb", "g", 453.592), ("oz", "g", 28.3495),
                ("l", "ml", 1000), ("cup", "ml", 240), ("tbsp", "ml", 15),
                ("tsp", "ml", 5), ("tbsp", "tsp", 3)
            ]
        ])

        # ---------- users ----------
        users_raw = [
            ("Demo Omnivore", "demo@example.com", "omnivore", "", ""),
            ("Vegan Alice", "alice@example.com", "vegan", "peanuts,walnuts", ""),
            ("Veggie Bob", "bob@example.com", "vegetarian", "", "high-protein"),
            ("Flexi Charlie", "charlie@example.com", "flexitarian", "lactose", "low-carb"),
        ]
        conn.execute(insert(users), [
            {"name": n, "email": e, "diet_type": d, "allergies": a,
             "preferences": p, "created_at": now, "updated_at": now}
            for n, e, d, a, p in users_raw
        ])
        user_id_map = {r.email: r.id for r in conn.execute(select(users.c.email, users.c.id))}

        # ---------- user credentials ----------
        sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
        credentials = [
            {
                "user_id": user_id_map["demo@example.com"],
                "password_hash": sha("demo123"),
                "first_name": "Daniel",
                "last_name": "Omni",
                "address": "Hauptstraße 1",
                "city": "Berlin",
                "postal_code": "10115",
                "country": "Germany",
                "phone": "+49 151 00000000",
                "created_at": now,
                "updated_at": now
            },
            {
                "user_id": user_id_map["alice@example.com"],
                "password_hash": sha("alice123"),
                "first_name": "Alice",
                "last_name": "Vegan",
                "address": "Lindenweg 5",
                "city": "Hamburg",
                "postal_code": "20095",
                "country": "Germany",
                "phone": "+49 151 11111111",
                "created_at": now,
                "updated_at": now
            },
            {
                "user_id": user_id_map["bob@example.com"],
                "password_hash": sha("bob123"),
                "first_name": "Bob",
                "last_name": "Green",
                "address": "Wiesenweg 8",
                "city": "München",
                "postal_code": "80331",
                "country": "Germany",
                "phone": "+49 151 22222222",
                "created_at": now,
                "updated_at": now
            },
            {
                "user_id": user_id_map["charlie@example.com"],
                "password_hash": sha("charlie123"),
                "first_name": "Charlie",
                "last_name": "Flex",
                "address": "Gartenstraße 12",
                "city": "Köln",
                "postal_code": "50667",
                "country": "Germany",
                "phone": "+49 151 33333333",
                "created_at": now,
                "updated_at": now
            },
        ]
        conn.execute(insert(user_credentials), credentials)

        # ---------- user health profiles ----------
        health_profiles = [
            {
                "user_id": user_id_map["demo@example.com"],
                "age": 35,
                "gender": "male",
                "height_cm": 178,
                "weight_kg": 78,
                "activity_level": "moderately active",
                "health_conditions": "",
                "goal": "maintain weight",
                "created_at": now,
                "updated_at": now,
            },
            {
                "user_id": user_id_map["alice@example.com"],
                "age": 29,
                "gender": "female",
                "height_cm": 165,
                "weight_kg": 60,
                "activity_level": "lightly active",
                "health_conditions": "peanuts, walnuts",
                "goal": "lose weight",
                "created_at": now,
                "updated_at": now,
            },
            {
                "user_id": user_id_map["bob@example.com"],
                "age": 42,
                "gender": "male",
                "height_cm": 172,
                "weight_kg": 85,
                "activity_level": "sedentary",
                "health_conditions": "hypertension",
                "goal": "lower blood pressure",
                "created_at": now,
                "updated_at": now,
            },
            {
                "user_id": user_id_map["charlie@example.com"],
                "age": 33,
                "gender": "male",
                "height_cm": 180,
                "weight_kg": 82,
                "activity_level": "lightly active",
                "health_conditions": "lactose intolerance",
                "goal": "gain muscle",
                "created_at": now,
                "updated_at": now,
            },
        ]
        conn.execute(insert(user_health_profiles), health_profiles)

        # ---------- kitchen & storage ----------
        kitchen_id = conn.execute(insert(kitchens).values(name="Demo Kitchen")).inserted_primary_key[0]
        sl_names = ["Refrigerator (Kühlschrank)", "Freezer (Gefrierschrank)",
                    "Pantry Cabinet (Apothekerschrank)", "Larder (Speisekammer)",
                    "Drawer Unit (Schubladenschrank)"]
        conn.execute(insert(storage_locations), [
            {"kitchen_id": kitchen_id, "name": n, "created_at": now, "updated_at": now} for n in sl_names
        ])
        sl_id_map = {r.name: r.id for r in conn.execute(select(storage_locations.c.name, storage_locations.c.id))}

        conn.execute(insert(user_kitchens), [
            {"user_id": uid, "kitchen_id": kitchen_id, "role": role,
             "created_at": now, "updated_at": now}
            for uid, role in [
                (user_id_map["demo@example.com"], "owner"),
                (user_id_map["alice@example.com"], "member"),
                (user_id_map["bob@example.com"], "member"),
                (user_id_map["charlie@example.com"], "member"),
            ]
        ])

        # ---------- device types ----------
        device_types_raw = [
            #  name (en + de)                 category     default_smart
            ("Oven (Backofen)", "APPLIANCE", False),
            ("Air Fryer (Heißluftfritteuse)", "APPLIANCE", False),
            ("Blender (Mixer)", "APPLIANCE", False),
            ("Cookware (Kochbesteck)", "TOOL", False),
            ("Baking Utensils (Backwerkzeug)", "TOOL", False),
        ]
        conn.execute(insert(device_types), [
            {"name": n, "category": cat, "default_smart": dsmart, "created_at": now}
            for n, cat, dsmart in device_types_raw
        ])
        dt_id_map = {r.name: r.id for r in conn.execute(select(device_types.c.name, device_types.c.id))}

        # ---------- kitchen tools ----------
        tool_specs = [
            # (device_type_key, name, size/detail, material, quantity, available, notes)
            ("Cookware (Kochbesteck)", "Chef's Knife (Kochmesser)", "20 cm", "stainless steel", 1, True, ""),
            ("Cookware (Kochbesteck)", "Cutting Board (Schneidebrett)", "30×20 cm", "bamboo", 2, True, ""),
            ("Cookware (Kochbesteck)", "Frying Pan (Pfanne)", "28 cm", "cast iron", 1, True, "well seasoned"),
            ("Cookware (Kochbesteck)", "Sauce Pot (Topf)", "3 L", "stainless steel", 1, True, ""),
            ("Baking Utensils (Backwerkzeug)", "Whisk (Schneebesen)", "", "stainless steel", 1, True, ""),
            ("Baking Utensils (Backwerkzeug)", "Rolling Pin (Nudelholz)", "", "beech wood", 1, True, ""),
            ("Cookware (Kochbesteck)", "Tongs (Zange)", "30 cm", "steel/silicone", 1, True, ""),
            ("Cookware (Kochbesteck)", "Peeler (Sparschäler)", "", "stainless steel", 1, True, ""),
        ]
        conn.execute(insert(kitchen_tools), [
            {
                "kitchen_id": kitchen_id,
                "device_type_id": dt_id_map[dt_key],
                "name": name,
                "size_or_detail": size,
                "material": material,
                "quantity": qty,
                "available": avail,
                "notes": notes,
                "created_at": now,
                "updated_at": now,
            }
            for dt_key, name, size, material, qty, avail, notes in tool_specs
        ])

        # ---------- appliances ----------
        appliance_specs = [
            # (device_type_key, name, brand, model, smart, capacity_l, power_w, year, available, notes)
            ("Oven (Backofen)", "Bosch Oven HBG675", "Bosch", "HBG675", False, 71, 3650, 2022, True, ""),
            ("Air Fryer (Heißluftfritteuse)", "Philips Air Fryer XXL", "Philips", "HD9650", False, 7, 2225, 2023, True,
             ""),
            ("Blender (Mixer)", "Vitamix E310", "Vitamix", "E310", False, 2, 1380, 2021, True, ""),
        ]
        conn.execute(insert(appliances), [
            {
                "kitchen_id": kitchen_id,
                "device_type_id": dt_id_map[dt_key],
                "name": name,
                "brand": brand,
                "model": model,
                "smart": smart,
                "capacity_liters": cap,
                "power_watts": pwr,
                "power_kw": round(pwr / 1000, 2),
                "year_purchased": year,
                "available": avail,
                "notes": notes,
                "created_at": now,
                "updated_at": now,
            }
            for dt_key, name, brand, model, smart, cap, pwr, year, avail, notes in appliance_specs
        ])

        # ---------- food items ----------
        food_items_raw = [
            # (name_en (de),            category,       base_unit_key)
            ("Tomato (Tomate)", "vegetable", "g"),
            ("Potato (Kartoffel)", "vegetable", "g"),
            ("Carrot (Karotte)", "vegetable", "g"),
            ("Onion (Zwiebel)", "vegetable", "g"),
            ("Garlic (Knoblauch)", "vegetable", "g"),
            ("Bell Pepper (Paprika)", "vegetable", "g"),
            ("Broccoli (Brokkoli)", "vegetable", "g"),
            ("Cucumber (Gurke)", "vegetable", "g"),
            ("Zucchini (Zucchini)", "vegetable", "g"),
            ("Lettuce (Kopfsalat)", "vegetable", "g"),

            ("Apple (Apfel)", "fruit", "g"),
            ("Banana (Banane)", "fruit", "g"),
            ("Orange (Orange)", "fruit", "g"),
            ("Lemon (Zitrone)", "fruit", "g"),
            ("Strawberry (Erdbeere)", "fruit", "g"),

            ("Rice (Reis)", "grain", "g"),
            ("Spaghetti (Spaghetti)", "grain", "g"),
            ("Flour (Mehl)", "grain", "g"),
            ("Oats (Haferflocken)", "grain", "g"),
            ("Bread Slice (Brotscheibe)", "grain", "slice"),

            ("Lentils (Linsen)", "legume", "g"),
            ("Chickpeas (Kichererbsen)", "legume", "g"),
            ("Black Beans (Schwarze Bohnen)", "legume", "g"),
            ("Almonds (Mandeln)", "legume", "g"),

            ("Milk (Milch)", "dairy", "ml"),
            ("Butter (Butter)", "dairy", "g"),
            ("Cheese (Käse)", "dairy", "g"),
            ("Yogurt (Joghurt)", "dairy", "ml"),
            ("Egg (Ei)", "dairy", "piece"),

            ("Chicken Breast (Hähnchenbrust)", "meat", "g"),
            ("Ground Beef (Hackfleisch)", "meat", "g"),
            ("Pork Chop (Schweinekotelett)", "meat", "g"),
            ("Salmon Fillet (Lachsfilet)", "meat", "g"),

            ("Olive Oil (Olivenöl)", "condiment", "ml"),
            ("Sugar (Zucker)", "condiment", "g"),
            ("Salt (Salz)", "condiment", "g"),
            ("Black Pepper (Pfeffer)", "condiment", "g"),
            ("Ketchup (Ketchup)", "condiment", "ml"),
            ("Soy Sauce (Sojasauce)", "condiment", "ml"),
            ("Vinegar (Essig)", "condiment", "ml"),
            ("Honey (Honig)", "condiment", "g"),

            ("Cinnamon (Zimt)", "spice", "g"),
            ("Paprika Powder (Paprikapulver)", "spice", "g"),
            ("Curry Powder (Currypulver)", "spice", "g"),
            ("Oregano (Oregano)", "spice", "g"),

            ("Frozen Peas (Erbsen, gefr.)", "frozen", "g"),
            ("Frozen Berries (Beeren, gefr.)", "frozen", "g"),

            ("Tofu (Tofu)", "plant protein", "g"),
            ("Coconut Milk (Kokosmilch)", "condiment", "ml"),
        ]  # = 50 Stück

        conn.execute(insert(food_items), [
            {"name": n, "category": cat, "base_unit_id": unit_id_map[unit],
             "created_at": now, "updated_at": now}
            for n, cat, unit in food_items_raw
        ])
        food_id_map = {r.name: r.id for r in conn.execute(select(food_items.c.name, food_items.c.id))}

        # ---------- food item aliases ----------
        aliases = [
            ("Frozen Berries (Beeren, gefr.)", ["Heidelbeeren", "Blaubeeren"]),
            ("Black Beans (Schwarze Bohnen)", ["Kidneybohnen"]),
            ("Paprika Powder (Paprikapulver)", ["Paprikagewürz"]),
            ("Curry Powder (Currypulver)", ["Currypaste"]),
            ("Soy Sauce (Sojasauce)", ["Soja Sauce"]),
            ("Salt (Salz)", ["Speisesalz"]),
            ("Bread Slice (Brotscheibe)", ["Brötchenscheibe"]),
            ("Apple (Apfel)", ["Apfelscheibe"]),
            ("Garlic (Knoblauch)", ["Knolle Knoblauch"]),
            ("Chicken Breast (Hähnchenbrust)", ["Hähnchenfilet"]),
            ("Salmon Fillet (Lachsfilet)", ["Lachs"]),
            ("Coconut Milk (Kokosmilch)", ["Kokosmilch Dose"]),
            ("Olive Oil (Olivenöl)", ["Pflanzenöl"]),
            ("Yogurt (Joghurt)", ["Joghurtbecher"]),
        ]

        alias_rows = []
        for fname, alias_list in aliases:
            fid = food_id_map.get(fname)
            if fid:
                for alias in alias_list:
                    alias_rows.append({
                        "food_item_id": fid,
                        "alias": alias,
                        "user_id": None,
                        "created_at": now,
                    })

        if alias_rows:
            conn.execute(insert(meta.tables["food_item_alias"]), alias_rows)

        # ---------- food-item spezifische Konversionen ----------
        fiuc_data = [
            # (food_name, from_unit, factor → base_unit)

            # Vegetables
            ("Tomato (Tomate)", "tetra_pak", 500),
            ("Potato (Kartoffel)", "bag", 2000),
            ("Carrot (Karotte)", "bag", 1000),
            ("Onion (Zwiebel)", "bag", 1000),
            ("Garlic (Knoblauch)", "clove", 5),
            ("Bell Pepper (Paprika)", "piece", 150),
            ("Broccoli (Brokkoli)", "piece", 300),
            ("Cucumber (Gurke)", "piece", 400),
            ("Zucchini (Zucchini)", "piece", 250),
            ("Lettuce (Kopfsalat)", "head", 250),

            # Fruits
            ("Apple (Apfel)", "piece", 180),
            ("Banana (Banane)", "piece", 120),
            ("Orange (Orange)", "piece", 200),
            ("Lemon (Zitrone)", "piece", 100),
            ("Strawberry (Erdbeere)", "box", 500),

            # Grains
            ("Rice (Reis)", "bag", 1000),
            ("Spaghetti (Spaghetti)", "pack", 500),
            ("Flour (Mehl)", "bag", 1000),
            ("Oats (Haferflocken)", "bag", 750),
            ("Bread Slice (Brotscheibe)", "slice", 40),

            # Legumes
            ("Lentils (Linsen)", "pack", 500),
            ("Chickpeas (Kichererbsen)", "can", 400),
            ("Black Beans (Schwarze Bohnen)", "can", 400),
            ("Almonds (Mandeln)", "pack", 200),

            # Dairy & Eggs
            ("Milk (Milch)", "bottle", 1000),
            ("Butter (Butter)", "pack", 250),
            ("Cheese (Käse)", "block", 400),
            ("Yogurt (Joghurt)", "cup", 150),
            ("Egg (Ei)", "piece", 60),

            # Meat & Fish
            ("Chicken Breast (Hähnchenbrust)", "pack", 500),
            ("Ground Beef (Hackfleisch)", "pack", 400),
            ("Pork Chop (Schweinekotelett)", "pack", 600),
            ("Salmon Fillet (Lachsfilet)", "pack", 300),

            # Condiments
            ("Olive Oil (Olivenöl)", "bottle", 750),
            ("Sugar (Zucker)", "bag", 1000),
            ("Salt (Salz)", "jar", 500),
            ("Black Pepper (Pfeffer)", "jar", 100),
            ("Ketchup (Ketchup)", "bottle", 500),
            ("Soy Sauce (Sojasauce)", "bottle", 250),
            ("Vinegar (Essig)", "bottle", 500),
            ("Honey (Honig)", "jar", 250),

            # Spices
            ("Cinnamon (Zimt)", "jar", 50),
            ("Paprika Powder (Paprikapulver)", "jar", 60),
            ("Curry Powder (Currypulver)", "jar", 60),
            ("Oregano (Oregano)", "jar", 30),

            # Frozen
            ("Frozen Peas (Erbsen, gefr.)", "bag", 750),
            ("Frozen Berries (Beeren, gefr.)", "bag", 500),

            # Plant protein
            ("Tofu (Tofu)", "pack", 400),
            ("Coconut Milk (Kokosmilch)", "can", 400),
        ]

        conn.execute(insert(food_item_unit_conversions), [
            {
                "food_item_id": food_id_map[f],
                "from_unit_id": unit_id_map[frm],
                "to_unit_id": unit_id_map[food_items_raw[[n for n, _, _ in food_items_raw].index(f)][2]],
                "factor": fac,
                "created_at": now,
                "updated_at": now,
            }
            for f, frm, fac in fiuc_data
        ])

        # ---------- inventory items ----------
        perishables = {"vegetable", "fruit", "dairy", "meat", "plant protein"}
        fridge_id = sl_id_map["Refrigerator (Kühlschrank)"]
        pantry_id = sl_id_map["Pantry Cabinet (Apothekerschrank)"]
        freezer_id = sl_id_map["Freezer (Gefrierschrank)"]

        inv_rows = []
        for name, cat, unit_key in food_items_raw:
            fid = food_id_map[name]

            # simple default quantities
            qty = 1000 if unit_key in {"g", "ml"} else 12
            if cat in {"spice", "condiment"}:
                qty = 200
            if unit_key == "piece":
                qty = 12

            min_q = qty * 0.1

            # choose storage
            if cat in {"frozen"}:
                sl_id = freezer_id
            elif cat in perishables:
                sl_id = fridge_id
            else:
                sl_id = pantry_id

            # expiration
            if cat in perishables:
                exp = date.today() + timedelta(days=7)
            elif cat == "frozen":
                exp = date.today() + timedelta(days=180)
            else:
                exp = date.today() + timedelta(days=365)

            inv_rows.append({
                "kitchen_id": kitchen_id,
                "food_item_id": fid,
                "storage_location_id": sl_id,
                "quantity": qty,
                "min_quantity": min_q,
                "expiration_date": exp,
                "created_at": now,
                "updated_at": now,
            })

        conn.execute(insert(inventory_items), inv_rows)

        # ---------- shopping list ----------
        shopping_list_id = conn.execute(insert(shopping_lists).values(
            kitchen_id=kitchen_id, name="Wocheneinkauf", type="supermarket",
            created_at=now
        )).inserted_primary_key[0]

        # ---- Hilfsmaps für Umrechnung ----
        base_unit_of_food = {r.id: r.base_unit_id for r in
                             conn.execute(select(food_items.c.id, food_items.c.base_unit_id))}
        fiuc_map = {(r.food_item_id, r.from_unit_id): r.factor
                    for r in conn.execute(select(food_item_unit_conversions.c.food_item_id,
                                                 food_item_unit_conversions.c.from_unit_id,
                                                 food_item_unit_conversions.c.factor))}

        # ---------- shopping products ----------
        shopping_products_rows = []
        default_package_types = {
            "bag": "bag",
            "bottle": "bottle",
            "can": "can",
            "jar": "jar",
            "pack": "package",
            "tetra_pak": "tetra_pak",
            "piece": "box",
            "slice": "package",
            "block": "package",
            "cup": "cup",
            "head": "package",
            "clove": "package",
        }

        default_prices_per_unit = {
            "g": 0.004,  # 4€/kg
            "ml": 0.0015,  # 1.5€/l
            "piece": 0.25,
            "slice": 0.1,
        }

        for f_name, category, base_unit_key in food_items_raw:
            food_id = food_id_map[f_name]

            # Suche passende FIUC
            fiuc_match = [
                (r.from_unit_id, r.factor)
                for r in conn.execute(select(
                    food_item_unit_conversions.c.from_unit_id,
                    food_item_unit_conversions.c.factor
                ).where(food_item_unit_conversions.c.food_item_id == food_id))
            ]

            if not fiuc_match:
                continue  # kein passendes Package gefunden

            from_unit_id, factor = fiuc_match[0]
            from_unit_name = [k for k, v in unit_id_map.items() if v == from_unit_id][0]

            package_quantity = 1
            quantity_in_base_unit = factor
            est_price_per_unit = default_prices_per_unit.get(base_unit_key, 0.005)
            est_price = round(quantity_in_base_unit * est_price_per_unit, 2)

            shopping_products_rows.append({
                "food_item_id": food_id,
                "package_unit_id": from_unit_id,
                "package_quantity": package_quantity,
                "quantity_in_base_unit": quantity_in_base_unit,
                "package_type": default_package_types.get(from_unit_name, "package"),
                "estimated_price": est_price,
                "created_at": now,
                "updated_at": now,
            })

        conn.execute(insert(shopping_products), shopping_products_rows)

        # ---------- shopping product assignments ----------

        shopping_product_ids = [r.id for r in conn.execute(select(shopping_products.c.id))]
        assignment_ids = sample(shopping_product_ids, min(10, len(shopping_product_ids)))

        conn.execute(insert(shopping_product_assignments), [
            {
                "shopping_product_id": pid,
                "shopping_list_id": shopping_list_id,
                "added_by_user_id": user_id_map["demo@example.com"],
                "is_auto_added": False,
                "note": "Seeded example product",
                "created_at": now,
                "updated_at": now,
            }
            for pid in assignment_ids
        ])


if __name__ == "__main__":
    print("Starting seeding process …")
    seed_database()
    print("✅ Seeding complete")
