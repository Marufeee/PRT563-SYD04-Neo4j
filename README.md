# PRT563 Assessment 4 — Neo4j migration (Sydney Group 04)

Migration of the Assessment 2 retail inventory database (SQLite, 22 relations) to a Neo4j graph database. It includes the Cypher import, four query use cases, and Graph Data Science centrality and similarity analytics.

## Contents

| Path | What it is | Brief requirement |
|---|---|---|
| `import.txt` | Constraints, indexes, `LOAD CSV` node and relationship creation, verification queries | Task 2 (required) |
| `csv/*.csv` | One CSV per relational table (22 files) | Task 2 (required) |
| `queries.txt` | Four query use cases | Task 3 (required) |
| `gds_analytics.txt` | Centrality (Task 4) and similarity (Task 5) scripts | Supplementary |
| `model/graph_model.png` / `.svg` / `.dot` | Graph data model diagram | Task 1 |
| `expected_results.txt` | Results of every query and algorithm computed independently with SQL and networkx | Supplementary (cross-check) |
| `scripts/expand_data.py` | Deterministic sample-data expansion (seed 563) | Supplementary |
| `scripts/expected_results.py` | Generates `expected_results.txt` | Supplementary |
| `scripts/retail_inventory_a2.db` | The Assessment 2 database, unchanged | Supplementary |
| `scripts/retail_inventory_v2.db` | The expanded database the CSVs were exported from | Supplementary |

## How to run

1. In Neo4j Desktop, create a local DBMS (Neo4j 5.x) and install the **Graph Data Science** plugin (2.4 or later).
2. Copy all 22 files from `csv/` into the DBMS `import` folder. They must sit directly in `import`, not in a subfolder.
3. Open Neo4j Browser and run `import.txt` top to bottom. Multi-statement mode is on by default. Each block ends with `;`.
4. Check the counts from step 6 against the tables below.
5. Run `queries.txt`, then `gds_analytics.txt`.

To rebuild the CSVs from scratch:
`python scripts/expand_data.py scripts/retail_inventory_a2.db scripts/retail_inventory_v2.db`, then export each table.

## Changes from the Assessment 2 design (justify in report)

| Relational construct | Graph representation | Why |
|---|---|---|
| Strong entities (PRODUCT, SUPPLIER, SALE, …) | Node labels; primary key → uniqueness constraint | Direct mapping. |
| 1:N foreign keys | Relationships (`IN_CATEGORY`, `SOLD_AT`, `WORKS_AT`, …) | Joins become stored pointers, so traversal cost no longer grows with table size. |
| Optional FKs (customer, home store, PO on delivery) | Relationship simply absent | Graphs have no NULL foreign keys. A walk-in sale has no `MADE` edge. |
| Recursive FKs (category parent, supervisor) | `SUBCATEGORY_OF`, `REPORTS_TO` | Variable-length paths (`*0..`) answer hierarchy questions at any depth. |
| Weak line entities (SALE_LINE, PURCHASE_ORDER_LINE, DELIVERY_LINE) | Relationships with properties (`CONTAINS`, `ORDERS`, `DELIVERED`), keyed by `lineNo` | A line is the connection between a document and what it is for. Removing the line table removes a hop from every query. |
| STOCK_ITEM (associative weak entity) | `(:Location)-[:STOCKS {…}]->(:Product)` | A stock position is a fact about a location–product pair, so it belongs on the edge between them. |
| STOCK_ADJUSTMENT → composite FK to STOCK_ITEM | Node linked to Location, Product and Employee | Relationships cannot point at relationships. Integrity is re-checked by query 6.3 in `import.txt`. |
| Specialisation (LOCATION, EMPLOYEE) | Extra labels on one node (`:Location:Store`, `:Employee:SalesAssistant`) | Multi-label nodes replace superclass + subclass tables, so no join is needed to read subclass attributes. `SERVED_BY` only matches `:SalesAssistant` (BR19). |
| Category / union type (SUPPLY_SOURCE) | Shared `:SupplySource` label on Supplier and Warehouse nodes | The surrogate table disappears. `SENT_FROM` targets the label, so one relationship type covers both kinds of source. |
| Aggregation (SUPPLY_AGREEMENT) | `:SupplyAgreement` node between Supplier and Product | Purchase-order lines must reference the agreement itself (BR9). A relationship cannot be the target of another relationship, so the agreement is reified as a node. |
| Multivalued attribute (SUPPLIER_PHONE) | List properties `phoneNumbers`, `phoneTypes` | Neo4j supports list properties, so the 1NF split is unnecessary. |
| Derived attributes | Still computed at read time | Same reasoning as Assessment 2 (BR12, BR23). |

### Sample data expansion

The Assessment 2 data had 24 sales, 8 customers and 12 products. Centrality and similarity results on a graph that small are not meaningful: almost every product co-occurs with every other, and customers have one or two baskets each.

`expand_data.py` keeps every Assessment 2 row unchanged and adds:

- September 2026 trading: 911 sales and 3,089 sale lines.
- 28 products, 142 customers and a fifth supplier with competing (non-preferred) agreements.
- Stock positions for the new products, 4 purchase orders, 1 delivery and 4 stock adjustments.

Baskets are generated from shopping missions (pantry, baking, snacks, cleaning, kitchen, personal care, quick shop) with a fixed seed, so every run is identical. All data remains fabricated.

Because August is untouched, `import.txt` step 6.4 reproduces Assessment 2 use case 3 exactly (7 rows, Liverpool Pantry 47 units / $107.65). This is the migration parity check.

## Expected verification counts (`import.txt` step 6)

**Nodes** (1,236 distinct). A node with two labels is counted under both:

| Label | Count | Label | Count |
|---|---|---|---|
| Category | 8 | Employee | 12 |
| Product | 40 | Manager | 4 |
| Supplier | 5 | SalesAssistant | 6 |
| SupplySource | 6 | WarehouseOperator | 2 |
| Location | 4 | Customer | 150 |
| Store | 3 | SupplyAgreement | 50 |
| Warehouse | 1 | PurchaseOrder | 9 |
| Sale | 935 | Delivery | 10 |
| StockAdjustment | 13 | | |

**Relationships** (6,238 total):

| Type | Count | Type | Count |
|---|---|---|---|
| CONTAINS | 3146 | OFFERS | 50 |
| SOLD_AT | 935 | FOR_PRODUCT | 50 |
| SERVED_BY | 935 | IN_CATEGORY | 40 |
| MADE | 608 | DELIVERED | 30 |
| STOCKS | 160 | ORDERS | 25 |
| HOME_STORE | 130 | AT_LOCATION / ADJUSTS / MADE_BY | 13 each |
| WORKS_AT | 12 | SENT_FROM / RECEIVED_AT / CHECKED_BY | 10 each |
| REPORTS_TO | 11 | PLACED_WITH / DELIVER_TO / RAISED_BY | 9 each |
| SUBCATEGORY_OF | 5 | FULFILS | 5 |

## Expected results (summary; full detail in `expected_results.txt`)

- **Q1** returns 10 rows. Instant Noodles leads with a shortfall of 6. The 5 Assessment 2 rows are all still present, plus 5 new products.
- **Q2** returns 9 rows (3 stores × 3 departments). Liverpool Household is top at about $4,153.
- **Q3** returns 16 products:
  - Salsa Dip → `RAISE PO NOW`
  - Scrub Sponges and White Sugar → `TRANSFER AND RAISE DC PO`
  - Coconut Milk and Deodorant → `TRANSFER - DC PO ALREADY OPEN`
  - the rest → `TRANSFER FROM DC`
- **Q4** returns 10 pairs. Toothpaste → Toothbrush has the highest lift (≈10.3), then Flour/Sugar, Corn Chips/Salsa, Foil/Cling Wrap, Shampoo/Conditioner and Spaghetti/Pasta Sauce.
- **Centrality** (40 nodes, 128 undirected edges, ≥ 10 shared receipts):
  - PageRank, weighted degree and eigenvector: top are Spaghetti and Pasta Sauce.
  - Betweenness: top is Paper Towel (≈255), then Olive Oil, Spaghetti/Pasta Sauce and Hand Soap. These are the bridges between shopping missions.
  - Olive Oil has only ~5 days of cover at Liverpool and Bankstown even though it is above its reorder level.
- **Similarity** for Anna Kowalski (id 1):

  | Metric | Top peers |
  |---|---|
  | Jaccard | Quinn Islam 0.583, Ethan Ali 0.462, Aisha Nguyen 0.429 |
  | Overlap | Quinn Islam 0.778, then a tie at 0.7 |
  | Cosine | Mei Lin 0.713, Quinn Islam 0.708, Kai Jones 0.637 |
  | KNN | Sofia Ali 0.967 |

  Jaccard-based recommendations: Hand Soap, Spaghetti, Dishwashing Liquid.

Scores come from SQL and networkx, not Neo4j. GDS PageRank, closeness and eigenvector scores use a different scale, so compare **rankings**, not raw values. Betweenness, Jaccard, Overlap and Cosine should match. Tied values may appear in a different order. Revenue sums may differ by ±0.01 from floating-point rounding.

## Compatibility notes

- Tested syntax targets Neo4j 5.x Cypher. Query 4 uses `CALL { WITH a … }`. On Neo4j 5.23+ that raises a deprecation notice, and `CALL (a) { … }` is the newer equivalent.
- `gds.graph.project(...)` used as an aggregation function (Cypher projection) needs GDS 2.4+. On older GDS, use `gds.graph.project.cypher`.
- On GDS releases before closeness reached production tier, the procedure is `gds.beta.closeness.stream`.
