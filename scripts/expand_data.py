"""
PRT563 Assessment 4 - Sydney Group 04
Expands the Assessment 2 sample data so the graph algorithms have enough
signal to work with. Every Assessment 2 row is kept unchanged; new rows are
added for September 2026 only, so the August results from Assessment 2 still
reproduce exactly. Fixed random seed -> the output is identical on every run.

Usage: python expand_data.py base.db retail_inventory_v2.db
"""
import random, shutil, sqlite3, sys
from datetime import date, timedelta

SRC, DST = sys.argv[1], sys.argv[2]
shutil.copy(SRC, DST)
db = sqlite3.connect(DST)
db.execute("PRAGMA foreign_keys = ON")
rnd = random.Random(563)

# ---------------------------------------------------------------- products
# (sku, name, description, uom, category_id, retail_price)
NEW_PRODUCTS = [
    ("GRO-1005", "Spaghetti 500g", "Durum wheat spaghetti", "EACH", 4, 1.60),
    ("GRO-1006", "Pasta Sauce 500g", "Tomato and basil sauce", "JAR", 4, 2.90),
    ("GRO-1007", "Plain Flour 2kg", "All-purpose plain flour", "BAG", 4, 3.20),
    ("GRO-1008", "White Sugar 2kg", "Granulated white sugar", "BAG", 4, 3.50),
    ("GRO-1009", "Red Lentils 1kg", "Split red lentils", "BAG", 4, 4.20),
    ("GRO-1010", "Basmati Rice 2kg", "Aged basmati rice", "BAG", 4, 7.90),
    ("GRO-1011", "Chickpeas 400g", "Chickpeas in brine", "CAN", 4, 1.10),
    ("GRO-1012", "Coconut Milk 400ml", "Full-cream coconut milk", "CAN", 4, 1.80),
    ("SNK-2003", "Cola 1.25L", "Cola soft drink", "BOTTLE", 5, 2.20),
    ("SNK-2004", "Milk Chocolate Bar 180g", "Block of milk chocolate", "EACH", 5, 4.50),
    ("SNK-2005", "Microwave Popcorn 3pk", "Butter flavour popcorn", "PACK", 5, 3.00),
    ("SNK-2006", "Corn Chips 200g", "Lightly salted corn chips", "EACH", 5, 3.10),
    ("SNK-2007", "Salsa Dip 300g", "Medium tomato salsa", "JAR", 5, 3.60),
    ("CLN-3003", "Dishwashing Liquid 1L", "Lemon dishwashing liquid", "BOTTLE", 6, 3.30),
    ("CLN-3004", "Paper Towel 4pk", "Two-ply paper towel", "PACK", 6, 5.50),
    ("CLN-3005", "Bin Liners 50pk", "Kitchen tidy bin liners", "PACK", 6, 4.00),
    ("CLN-3006", "Bleach 2L", "Regular household bleach", "BOTTLE", 6, 3.80),
    ("CLN-3007", "Scrub Sponges 6pk", "Non-scratch scrub sponges", "PACK", 6, 2.60),
    ("KIT-4003", "Aluminium Foil 30m", "Heavy duty foil roll", "ROLL", 7, 4.40),
    ("KIT-4004", "Cling Wrap 60m", "Food wrap film", "ROLL", 7, 3.20),
    ("KIT-4005", "Baking Paper 20m", "Non-stick baking paper", "ROLL", 7, 3.70),
    ("KIT-4006", "Mixing Bowl Set 3pc", "Stainless steel bowls", "SET", 7, 14.90),
    ("HAI-5003", "Body Wash 1L", "Moisturising body wash", "BOTTLE", 8, 6.50),
    ("HAI-5004", "Toothpaste 110g", "Fluoride toothpaste", "EACH", 8, 2.80),
    ("HAI-5005", "Deodorant 150ml", "48h antiperspirant spray", "EACH", 8, 4.90),
    ("HAI-5006", "Hair Gel 150ml", "Strong hold hair gel", "EACH", 8, 4.20),
    ("HAI-5007", "Toothbrush 2pk", "Medium bristle toothbrush", "PACK", 8, 3.40),
    ("HAI-5008", "Hand Soap 500ml", "Antibacterial hand wash", "BOTTLE", 8, 3.90),
]
for i, p in enumerate(NEW_PRODUCTS, start=13):
    db.execute("INSERT INTO PRODUCT VALUES (?,?,?,?,?,?,?,1)", (i, *p))
pid = {r[0]: r[1] for r in db.execute("SELECT sku, product_id FROM PRODUCT")}
price = {r[0]: r[1] for r in db.execute("SELECT product_id, retail_price FROM PRODUCT")}

# --------------------------------------------- 5th supplier (competing terms)
db.execute("INSERT INTO SUPPLY_SOURCE VALUES (6,'SUPPLIER')")
db.execute("""INSERT INTO SUPPLIER VALUES (5,6,'Metro Grocery Distributors','83222444666',
           'trade@metrogrocery.example','71 Hume Highway','Chullora','NSW','2190',21)""")
db.execute("INSERT INTO SUPPLIER_PHONE VALUES (5,'02 9642 8800','OFFICE')")

home_supplier = {4: 1, 5: 1, 6: 2, 7: 3, 8: 4}
agr = 13
for i, (sku, _, _, _, cat, rp) in enumerate(NEW_PRODUCTS, start=13):
    agr += 1
    db.execute("INSERT INTO SUPPLY_AGREEMENT VALUES (?,?,?,?,?,?,1)",
               (agr, home_supplier[cat], i, round(rp * 0.6, 2), rnd.choice([5, 6, 7, 8]),
                rnd.choice([48, 60, 96, 120])))
# Metro competes (non-preferred) on grocery and snack lines
for p in [1, 2, 4, 12, 13, 14, 21, 23, 24]:
    agr += 1
    db.execute("INSERT INTO SUPPLY_AGREEMENT VALUES (?,5,?,?,3,?,0)",
               (agr, p, round(price[p] * 0.66, 2), rnd.choice([24, 36, 48])))

# ------------------------------------------------------------- stock items
bins = {2: "S1", 3: "S2", 4: "S3"}
for i in range(13, 41):
    db.execute("INSERT INTO STOCK_ITEM VALUES (1,?,?,?,?,?,?,?)",
               (i, rnd.randint(40, 420), rnd.choice([0, 12, 24]), 80, 240,
                f"C-{i:02d}-1", "2026-09-28"))
    for loc in (2, 3, 4):
        lvl = rnd.choice([10, 12, 14, 16])
        on_hand = rnd.randint(lvl - 4, lvl + 30)
        db.execute("INSERT INTO STOCK_ITEM VALUES (?,?,?,?,?,?,?,?)",
                   (loc, i, max(on_hand, 0), 0, lvl, lvl * 3,
                    f"{bins[loc]}-E{i:02d}", "2026-09-28"))

# ------------------------------------------------- September purchase orders
po_lines = {
    6: (1, 1, 1, "2026-09-22", "2026-09-29", "OPEN", [13, 14, 19, 20]),
    7: (2, 1, 1, "2026-09-23", "2026-09-30", "OPEN", [26, 27, 29]),
    8: (4, 3, 7, "2026-09-24", "2026-10-02", "OPEN", [35, 36, 37]),
    9: (3, 1, 1, "2026-09-10", "2026-09-24", "RECEIVED", [31, 32]),
}
for po, (sup, loc, emp, od, ed, st, prods) in po_lines.items():
    db.execute("INSERT INTO PURCHASE_ORDER VALUES (?,?,?,?,?,?,?,?)",
               (po, f"PO-2026-01{po:02d}", sup, loc, emp, od, ed, st))
    for ln, p in enumerate(prods, 1):
        a_id, a_price, moq = db.execute(
            "SELECT agreement_id, supply_price, min_order_qty FROM SUPPLY_AGREEMENT "
            "WHERE supplier_id=? AND product_id=?", (sup, p)).fetchone()
        rec = moq if st == "RECEIVED" else 0
        db.execute("INSERT INTO PURCHASE_ORDER_LINE VALUES (?,?,?,?,?,?)",
                   (po, ln, a_id, moq, rec, a_price))
db.execute("INSERT INTO INBOUND_DELIVERY VALUES (10,'DN-90001',4,1,9,'2026-09-24',3)")
db.execute("INSERT INTO DELIVERY_LINE VALUES (10,1,31,120,0)")
db.execute("INSERT INTO DELIVERY_LINE VALUES (10,2,32,120,1)")

# --------------------------------------------------------------- customers
FIRST = ["Aisha","Ben","Chen","Daniela","Ethan","Fatima","George","Hana","Ivan","Jasmine",
         "Kai","Layla","Marco","Nadia","Oliver","Priya","Quinn","Rahul","Sofia","Tariq",
         "Uma","Victor","Wei","Ximena","Yusuf","Zara","Amir","Bella","Connor","Dina"]
LAST = ["Nguyen","Smith","Rahman","Garcia","Wong","Khan","Brown","Haddad","Patel","Tran",
        "Kelly","Hossain","Lopez","Ali","Jones","Le","Singh","Murphy","Costa","Islam"]
tiers = ["BRONZE"] * 6 + ["SILVER"] * 3 + ["GOLD"]
for cid in range(9, 151):
    fn, ln = rnd.choice(FIRST), rnd.choice(LAST)
    joined = date(2021, 1, 1) + timedelta(days=rnd.randint(0, 2000))
    home = rnd.choice([2, 2, 3, 3, 4, 4, None])
    db.execute("INSERT INTO CUSTOMER VALUES (?,?,?,?,?,?,?,?)",
               (cid, fn, ln, f"{fn.lower()}.{ln.lower()}{cid}@example.com",
                f"04{rnd.randint(10,99)} {rnd.randint(100,999)} {rnd.randint(100,999)}",
                joined.isoformat(), rnd.choice(tiers), home))

# --------------------------------------------- shopping missions (baskets)
# Each mission is a set of SKUs that tend to be bought together. A few
# "bridge" products sit in two missions on purpose, which is what the
# centrality analysis is expected to surface.
MISSIONS = {
    "pantry":   ["GRO-1001","GRO-1003","GRO-1004","GRO-1005","GRO-1006","GRO-1011","GRO-1012","GRO-1009","GRO-1010"],
    "baking":   ["GRO-1007","GRO-1008","KIT-4005","KIT-4006","GRO-1003"],
    "snacks":   ["SNK-2001","SNK-2002","SNK-2003","SNK-2004","SNK-2005","SNK-2006","SNK-2007","GRO-1002"],
    "clean":    ["CLN-3001","CLN-3002","CLN-3003","CLN-3004","CLN-3005","CLN-3006","CLN-3007"],
    "kitchen":  ["KIT-4001","KIT-4002","KIT-4003","KIT-4004","CLN-3004","CLN-3003"],
    "personal": ["HAI-5001","HAI-5002","HAI-5003","HAI-5004","HAI-5005","HAI-5006","HAI-5007","HAI-5008"],
    "quick":    ["GRO-1002","GRO-1004","SNK-2003","GRO-1005","HAI-5008"],
}
# Strong pairs inside missions (bought together far more often than chance)
PAIRS = [("GRO-1005","GRO-1006"), ("HAI-5001","HAI-5002"), ("SNK-2006","SNK-2007"),
         ("GRO-1007","GRO-1008"), ("HAI-5004","HAI-5007"), ("KIT-4003","KIT-4004")]
mission_names = list(MISSIONS)

cust_profile = {}
for cid in range(1, 151):
    a, b = rnd.sample(mission_names, 2)
    cust_profile[cid] = (a, b)
cust_home = {r[0]: r[1] for r in db.execute("SELECT customer_id, home_store_id FROM CUSTOMER")}
assistants = {2: [5, 6], 3: [8, 9], 4: [11, 12]}
store_code = {2: ("BKT", 1009), 3: ("LVP", 2008), 4: ("PAR", 3007)}
counter = {s: n for s, (_, n) in store_code.items()}
store_weight = {2: 1.0, 3: 1.15, 4: 0.9}

def basket(primary, secondary):
    items = set()
    n_lines = rnd.choices([1, 2, 3, 4, 5, 6], [8, 22, 28, 22, 13, 7])[0]
    for _ in range(n_lines):
        r = rnd.random()
        pool = MISSIONS[primary] if r < 0.65 else MISSIONS[secondary] if r < 0.9 else list(pid)
        sku = rnd.choice(pool)
        items.add(sku)
        for x, y in PAIRS:
            if sku == x and rnd.random() < 0.6: items.add(y)
            if sku == y and rnd.random() < 0.6: items.add(x)
    return list(items)

sale_id = db.execute("SELECT MAX(sale_id) FROM SALE").fetchone()[0]
promo = {"SNK-2001", "GRO-1006", "CLN-3002"}          # September promotions
for day in range(1, 31):
    d = date(2026, 9, day)
    weekend = d.weekday() >= 5
    for store in (2, 3, 4):
        n = int(rnd.gauss(10 if not weekend else 13, 2) * store_weight[store])
        for _ in range(max(n, 4)):
            sale_id += 1
            counter[store] += 1
            if rnd.random() < 0.62:
                cands = [c for c, h in cust_home.items() if h == store] or list(cust_home)
                cid = rnd.choice(cands) if rnd.random() < 0.85 else rnd.choice(list(cust_home))
                prim, sec = cust_profile[cid]
            else:
                cid = None
                prim, sec = rnd.sample(mission_names, 2)
            t = f"{d.isoformat()} {rnd.randint(9,17):02d}:{rnd.randint(0,59):02d}"
            pay = rnd.choices(["EFTPOS","CREDIT_CARD","CASH","GIFT_CARD"], [50, 25, 20, 5])[0]
            db.execute("INSERT INTO SALE VALUES (?,?,?,?,?,?,?)",
                       (sale_id, f"R-{store_code[store][0]}-{counter[store]}", store,
                        rnd.choice(assistants[store]), cid, t, pay))
            for ln, sku in enumerate(basket(prim, sec), 1):
                p = pid[sku]
                qty = rnd.choices([1, 2, 3, 4], [60, 25, 10, 5])[0]
                disc = 0.10 if sku in promo else 0.0
                db.execute("INSERT INTO SALE_LINE VALUES (?,?,?,?,?,?)",
                           (sale_id, ln, p, qty, price[p], disc))

# ---------------------------------------- a few September stock adjustments
adj = [(2, 14, "2026-09-05", "DAMAGE", -2, 5, "Cracked jars"),
       (3, 21, "2026-09-12", "THEFT", -3, 7, "Shrinkage at front counter"),
       (4, 29, "2026-09-18", "EXPIRY", -4, 10, "Past use-by date"),
       (1, 26, "2026-09-26", "STOCKTAKE", 6, 2, "Recount of overflow bay")]
for i, a in enumerate(adj, start=10):
    db.execute("INSERT INTO STOCK_ADJUSTMENT VALUES (?,?,?,?,?,?,?,?)", (i, *a))

db.commit()
bad = db.execute("PRAGMA foreign_key_check").fetchall()
assert not bad, bad
for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    print(f"{t:22s}{db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>6}")
