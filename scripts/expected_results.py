"""Cross-check: computes the expected output of every Cypher query and GDS
algorithm directly from the SQLite copy (SQL + networkx), so the Neo4j
results can be verified independently."""
import sqlite3, itertools, collections, math, sys
import networkx as nx
db = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else 'retail_inventory_v2.db')
q = lambda s, *a: db.execute(s, a).fetchall()
pname = dict(q("select product_id, product_name from PRODUCT"))
psku = dict(q("select product_id, sku from PRODUCT"))
cname = {r[0]: f"{r[1]} {r[2]}" for r in q("select customer_id, first_name, last_name from CUSTOMER")}

def show(title, rows):
    print(f"\n=== {title} ({len(rows)} rows)")
    for r in rows: print("  ", r)

show("Q1 Liverpool low stock", q("""select p.sku, p.product_name, si.bin_code, qty_on_hand, qty_reserved,
 qty_on_hand-qty_reserved, reorder_level, reorder_level-qty_on_hand sf
 from STOCK_ITEM si join PRODUCT p using(product_id)
 where location_id=3 and qty_on_hand<=reorder_level and bin_code is not null order by sf desc, p.sku"""))

show("Q2 Sept revenue by store and department", q("""select l.location_name, coalesce(pp.category_name, pc.category_name),
 count(distinct s.sale_id), sum(qty_sold), round(sum(qty_sold*unit_price*(1-discount_pct)),2) rev
 from SALE s join SALE_LINE sl using(sale_id) join PRODUCT p using(product_id)
 join PRODUCT_CATEGORY pc on pc.category_id=p.category_id
 left join PRODUCT_CATEGORY pp on pp.category_id=pc.parent_category_id
 join LOCATION l on l.location_id=s.store_id
 where sale_datetime>='2026-09-01' and sale_datetime<'2026-10-01' group by 1,2 order by 1, rev desc"""))

low = collections.defaultdict(list); need = collections.Counter()
for code, p, oh, rl, rq in q("""select l.location_code, product_id, qty_on_hand, reorder_level, reorder_qty
 from STOCK_ITEM si join LOCATION l using(location_id) where l.location_type='STORE' and qty_on_hand<=reorder_level
 order by l.location_code"""):
    low[p].append(f"{code} ({oh}/{rl})"); need[p] += rq
rows = []
for p in low:
    sup, lt = q("""select s.supplier_name, a.lead_time_days from SUPPLY_AGREEMENT a join SUPPLIER s using(supplier_id)
      where product_id=? and is_preferred=1""", p)[0]
    inb, pos = q("""select coalesce(sum(qty_ordered-qty_received),0), group_concat(distinct po_number)
      from PURCHASE_ORDER_LINE join PURCHASE_ORDER using(po_id) join SUPPLY_AGREEMENT a using(agreement_id)
      where a.product_id=? and po_status in ('OPEN','PARTIAL')""", p)[0]
    dc, dcl = q("select qty_on_hand-qty_reserved, reorder_level from STOCK_ITEM where location_id=1 and product_id=?", p)[0]
    if dc >= need[p] and dc - need[p] >= dcl: act = 'TRANSFER FROM DC'
    elif dc >= need[p]: act = 'TRANSFER - DC PO ALREADY OPEN' if inb > 0 else 'TRANSFER AND RAISE DC PO'
    else: act = 'WAIT FOR OPEN PO' if inb > 0 else 'RAISE PO NOW'
    rows.append((psku[p], pname[p], len(low[p]), low[p], need[p], dc, dcl, inb, pos, sup, lt, act))
rows.sort(key=lambda r: (-r[2], r[0]))
show("Q3 replenishment routing", rows)

bask = collections.defaultdict(set)
for s, p in q("select sale_id, product_id from SALE_LINE"): bask[s].add(p)
N = len(bask); pc = collections.Counter(); pair = collections.Counter()
for b in bask.values():
    pc.update(b)
    for a, c in itertools.combinations(sorted(b), 2): pair[(a, c)] += 1
r4 = [(pname[a], pname[c], n, round(100.0*n/N, 2), round(n/pc[a], 3), round(n/pc[c], 3), round(n*N/(pc[a]*pc[c]), 2))
      for (a, c), n in pair.items() if n >= 15]
show("Q4 basket pairs (together>=15) top 10 by lift", sorted(r4, key=lambda r: -r[6])[:10])

# ---------------- centrality on co-purchase graph (together >= 10) -----------
G = nx.Graph(); G.add_nodes_from(pname)
for (a, c), n in pair.items():
    if n >= 10: G.add_edge(a, c, weight=n)
print(f"\n=== Centrality graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, "
      f"{nx.number_connected_components(G)} component(s)")
deg = dict(G.degree()); wdeg = dict(G.degree(weight='weight'))
pr = nx.pagerank(G, weight='weight'); btw = nx.betweenness_centrality(G, normalized=False)
clo = nx.closeness_centrality(G); eig = nx.eigenvector_centrality(G, weight='weight', max_iter=500)
table = sorted(pname, key=lambda k: -btw[k])
print("   product | degree | wDegree | pagerank-rank | betweenness | closeness | eigen-rank")
prk = {k: i+1 for i, k in enumerate(sorted(pname, key=lambda k: -pr[k]))}
eik = {k: i+1 for i, k in enumerate(sorted(pname, key=lambda k: -eig[k]))}
for k in table[:12]:
    print(f"   {pname[k]:28s} {deg[k]:3d} {wdeg[k]:5d}  PR#{prk[k]:<3d} {btw[k]:8.2f} {clo[k]:.3f} EV#{eik[k]}")
for lab, d in [("PageRank", pr), ("Weighted degree", wdeg), ("Eigenvector", eig), ("Closeness", clo)]:
    print(f"   top5 {lab}:", [pname[k] for k in sorted(d, key=lambda k: -d[k])[:5]])

# ---------------- similarity: customers x products ---------------------------
buys = collections.defaultdict(collections.Counter)
for c, p, n in q("select s.customer_id, sl.product_id, sl.qty_sold from SALE s join SALE_LINE sl using(sale_id) where s.customer_id is not null"):
    buys[c][p] += n
elig = [c for c in buys if len(buys[c]) >= 5]           # degreeCutoff: 5
print(f"\n=== Similarity: {len(buys)} customers with purchases, {len(elig)} pass degreeCutoff 5")
def jaccard(a, b): return len(set(buys[a]) & set(buys[b])) / len(set(buys[a]) | set(buys[b]))
def overlap(a, b): return len(set(buys[a]) & set(buys[b])) / min(len(buys[a]), len(buys[b]))
def cosine(a, b):
    A, B = buys[a], buys[b]
    return sum(A[k]*B[k] for k in A) / math.sqrt(sum(v*v for v in A.values()) * sum(v*v for v in B.values()))
for f in (jaccard, overlap, cosine):
    top = sorted(((round(f(a, b), 3), cname[a], cname[b], len(buys[a]), len(buys[b])) for a, b in itertools.combinations(elig, 2)), reverse=True)[:5]
    print("   top pairs", f.__name__, top)
T = 1
print(f"   {cname[T]} bought:", sorted(pname[p] for p in buys[T]))
for f in (jaccard, overlap, cosine):
    nb = sorted(((round(f(T, b), 3), b) for b in elig if b != T), key=lambda x: (-x[0], x[1]))[:3]
    rec = collections.Counter()
    for s, b in nb:
        for p in buys[b]:
            if p not in buys[T]: rec[p] += s
    print(f"   {f.__name__} neighbours:", [(s, cname[b]) for s, b in nb])
    print(f"      recommendations:", [(pname[p], round(v, 3)) for p, v in rec.most_common(5)])
# KNN on category spend mix (cosine)
cats = ['Pantry', 'Snacks', 'Cleaning', 'Kitchenware', 'Haircare']
spend = collections.defaultdict(lambda: [0.0]*5)
for c, cat, v in q("""select s.customer_id, pc.category_name, sum(qty_sold*unit_price*(1-discount_pct))
 from SALE s join SALE_LINE sl using(sale_id) join PRODUCT p using(product_id) join PRODUCT_CATEGORY pc using(category_id)
 where s.customer_id is not null group by 1,2"""):
    spend[c][cats.index(cat)] = v
mix = {c: [x/sum(v) for x in v] for c, v in spend.items()}
cs = lambda a, b: sum(x*y for x, y in zip(a, b)) / math.sqrt(sum(x*x for x in a)*sum(y*y for y in b))
print(f"   {cname[T]} category mix:", [round(x, 3) for x in mix[T]])
nb = sorted(((round(cs(mix[T], mix[b]), 4), cname[b], [round(x, 2) for x in mix[b]]) for b in mix if b != T), reverse=True)[:3]
print("   KNN cosine neighbours:", nb)
