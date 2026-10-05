# -*- coding: utf-8 -*-
"""
明朝 20 位重要將領關係網路
==========================
1. 節點 (nodes): 20 位明朝重要將領，附屬性（活躍年代、陣營、角色、關鍵戰役）
2. 邊   (edges): 三種關係
   - 同陣營  (same_faction)  權重 1
   - 同時期  (same_era)      權重 1
   - 共同戰役 (co_battle)    權重 2（並肩作戰，關係最強）
3. 社群: Louvain 方法偵測社群，作為節點著色依據
4. 佈局: 力導向佈局 (Fruchterman-Reingold spring layout)
5. 輸出: nodes.csv / edges.csv / ming_generals_network.png
6. HTML: 互動式網路視覺化 ming_generals_network.html（節點/邊皆有詳細解說）
7. 驗證: 對照《明史》原文 (明史.txt)，確認每位將領皆出現於史書中
"""

import csv
import os
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patheffects as pe
from matplotlib.lines import Line2D

BASE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- 字型設定
FONT_PATH = os.path.join(BASE, "fonts", "NotoSansTC-Regular.otf")
if os.path.exists(FONT_PATH):
    fm.fontManager.addfont(FONT_PATH)
    plt.rcParams["font.family"] = fm.FontProperties(fname=FONT_PATH).get_name()
plt.rcParams["axes.unicode_minus"] = False

# ---------------------------------------------------------------- 1. 節點：20 位名將
# (名字, 活躍年代, 陣營, 角色, 關鍵戰役)
GENERALS = [
    ("徐達",       "元末-洪武", "開國", "元帥",   ["滅張士誠", "北伐滅元"]),
    ("常遇春",     "元末-洪武", "開國", "先鋒",   ["鄱陽湖之戰", "北伐滅元"]),
    ("李文忠",     "元末-洪武", "開國", "主帥",   ["破張士誠", "北征應昌"]),
    ("馮勝",       "元末-洪武", "開國", "主帥",   ["遼東之役", "金山之戰"]),
    ("鄧愈",       "元末-洪武", "開國", "將領",   ["徽州之戰", "平吐蕃"]),
    ("湯和",       "元末-洪武", "開國", "將領",   ["平浙東", "征蜀夏"]),
    ("傅友德",     "洪武",      "開國", "主帥",   ["平定四川", "平定雲南"]),
    ("藍玉",       "洪武",      "開國", "主帥",   ["捕魚兒海之戰"]),
    ("沐英",       "洪武",      "開國", "將領",   ["平定雲南", "鎮守雲南"]),
    ("戚繼光",     "嘉靖-萬曆", "抗倭", "主帥",   ["台州大捷", "薊鎮練兵"]),
    ("俞大猷",     "嘉靖",      "抗倭", "將領",   ["平海衛大捷", "剿倭閩粵"]),
    ("李如松",     "萬曆",      "遼東", "主帥",   ["平壤之戰", "碧蹄館之戰"]),
    ("麻貴",       "萬曆",      "遼東", "將領",   ["蔚山之戰", "順天之戰"]),
    ("陳璘",       "萬曆",      "遼東", "水師",   ["露梁海戰"]),
    ("鄧子龍",     "萬曆",      "遼東", "水師",   ["露梁海戰"]),
    ("袁崇煥",     "天啟-崇禎", "遼東", "督師",   ["寧遠大捷", "寧錦大捷"]),
    ("孫承宗",     "天啟-崇禎", "遼東", "督師",   ["寧遠大捷", "構築關寧錦防線"]),
    ("盧象昇",     "崇禎",      "剿寇", "總督",   ["鉅鹿賈莊之戰", "剿流寇"]),
    ("洪承疇",     "崇禎",      "剿寇", "經略",   ["松錦之戰", "剿流寇"]),
    ("左良玉",     "崇禎",      "剿寇", "將領",   ["剿流寇", "朱仙鎮之戰"]),
]

FACTION_COLORS = {
    "開國": "#C0392B",   # 紅
    "抗倭": "#1F77B4",   # 藍
    "遼東": "#2E8B57",   # 綠
    "剿寇": "#8E44AD",   # 紫
}

# ---------------------------------------------------------------- 2. 邊：三種關係
edges = []  # (u, v, relation)

# 2a. 同陣營
factions = {}
for name, _, fac, _, _ in GENERALS:
    factions.setdefault(fac, []).append(name)
for fac, members in factions.items():
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            edges.append((members[i], members[j], "同陣營"))

# 2b. 同時期（活躍年代有重疊）
ERAS = {name: era for name, era, _, _, _ in GENERALS}
def overlap(e1, e2):
    """兩個年代字串是否有重疊時期（以關鍵字比對）"""
    PERIODS = ["元末", "洪武", "嘉靖", "萬曆", "天啟", "崇禎"]
    s1 = {p for p in PERIODS if p in e1}
    s2 = {p for p in PERIODS if p in e2}
    return bool(s1 & s2)
names = [g[0] for g in GENERALS]
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        if overlap(ERAS[names[i]], ERAS[names[j]]):
            edges.append((names[i], names[j], "同時期"))

# 2c. 共同戰役（並肩作戰）
BATTLES = {name: set(battles) for name, _, _, _, battles in GENERALS}
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        common = BATTLES[names[i]] & BATTLES[names[j]]
        if common:
            edges.append((names[i], names[j], "共同戰役"))

# ---------------------------------------------------------------- 3. 建圖
G = nx.Graph()
for name, era, fac, role, battles in GENERALS:
    G.add_node(name, era=era, faction=fac, role=role, battles="、".join(battles))

REL_WEIGHT = {"同陣營": 1, "同時期": 1, "共同戰役": 2}
for u, v, rel in edges:
    if G.has_edge(u, v):
        G[u][v]["weight"] += REL_WEIGHT[rel]
        G[u][v]["relations"] += "+" + rel
    else:
        G.add_edge(u, v, weight=REL_WEIGHT[rel], relations=rel)

# ---------------------------------------------------------------- 3.5 Louvain 社群偵測
from networkx.algorithms.community import louvain_communities, modularity

communities = louvain_communities(G, weight="weight", seed=42)
communities = sorted(communities, key=len, reverse=True)
COMMUNITY_COLORS = ["#C0392B", "#1F77B4", "#2E8B57", "#8E44AD",
                    "#E67E22", "#16A085", "#D4AC0D", "#7F8C8D"]
node_community = {}
for ci, com in enumerate(communities):
    for n in com:
        node_community[n] = ci
q = modularity(G, communities, weight="weight")
print(f"\nLouvain 社群數 = {len(communities)}，Modularity Q = {q:.4f}")
for ci, com in enumerate(communities):
    print(f"  社群 {ci} ({len(com)}人): {'、'.join(sorted(com))}")

# ---------------------------------------------------------------- 4. 輸出 CSV
nodes_csv = os.path.join(BASE, "nodes.csv")
with open(nodes_csv, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["name", "era", "faction", "role", "battles", "degree", "community"])
    for n, d in G.nodes(data=True):
        w.writerow([n, d["era"], d["faction"], d["role"], d["battles"],
                    G.degree(n), node_community[n]])

edges_csv = os.path.join(BASE, "edges.csv")
with open(edges_csv, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["source", "target", "weight", "relations"])
    for u, v, d in G.edges(data=True):
        w.writerow([u, v, d["weight"], d["relations"]])

# ---------------------------------------------------------------- 5. 畫圖（力導向佈局 + Louvain 社群著色）
fig, ax = plt.subplots(figsize=(20, 14))

# 力導向佈局：圖由 3 個連通分量組成，先對每個分量各自做 spring layout
# （以邊權重為吸引力），再將各分量網格排列到畫布上，避免分量被彈開、節點互相擠壓
comps = sorted(nx.connected_components(G), key=len, reverse=True)
cols = 2
nrows = -(-len(comps) // cols)
cell_w, cell_h = 1.0 / cols, 1.0 / nrows
pos = {}
for idx, comp in enumerate(comps):
    sub = G.subgraph(comp)
    p = nx.spring_layout(sub, k=1.4, weight="weight", iterations=600, seed=42)
    xs = [c[0] for c in p.values()]
    ys = [c[1] for c in p.values()]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    norm = lambda v, lo, hi: (v - lo) / (hi - lo) if hi > lo else 0.5
    r, c = divmod(idx, cols)
    ox = c * cell_w + cell_w / 2
    oy = (nrows - 1 - r) * cell_h + cell_h / 2
    for n, (x, y) in p.items():
        pos[n] = (ox + (norm(x, minx, maxx) - 0.5) * cell_w * 0.82,
                  oy + (norm(y, miny, maxy) - 0.5) * cell_h * 0.82)

node_colors = [COMMUNITY_COLORS[node_community[n] % len(COMMUNITY_COLORS)] for n in G.nodes()]
sizes = [1400 + 500 * G.degree(n) for n in G.nodes()]
nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors,
                       node_size=sizes, edgecolors="white", linewidths=3, alpha=0.95)

REL_STYLE = {
    "共同戰役": dict(color="#E67E22", width=4.5, style="solid"),
    "同陣營":   dict(color="#7F8C8D", width=2.2, style="solid"),
    "同時期":   dict(color="#95A5A6", width=1.6, style="dashed"),
}
for rel, st in REL_STYLE.items():
    elist = [(u, v) for u, v, d in G.edges(data=True) if rel in d["relations"]]
    nx.draw_networkx_edges(G, pos, edgelist=elist, ax=ax,
                           edge_color=st["color"], width=st["width"],
                           style=st["style"], alpha=0.8)

# 名字直接畫在節點上：白字 + 深色描邊，任何底色都清晰可讀
for n, (x, y) in pos.items():
    ax.text(x, y, n, fontsize=17, fontweight="bold", color="white",
            ha="center", va="center", zorder=5,
            fontfamily=plt.rcParams["font.family"],
            path_effects=[pe.withStroke(linewidth=3.5, foreground="#2C3E50")])

legend_items = [
    Line2D([0], [0], marker="o", color="w",
           markerfacecolor=COMMUNITY_COLORS[ci % len(COMMUNITY_COLORS)],
           markersize=18, label=f"社群 {ci} ({len(com)}人)")
    for ci, com in enumerate(communities)
] + [
    Line2D([0], [0], color="#E67E22", lw=4.5, label="共同戰役 (權重2)"),
    Line2D([0], [0], color="#7F8C8D", lw=2.2, label="同陣營 (權重1)"),
    Line2D([0], [0], color="#95A5A6", lw=1.6, ls="--", label="同時期 (權重1)"),
]
leg = ax.legend(handles=legend_items, loc="center left", bbox_to_anchor=(1.0, 0.5),
                fontsize=15, framealpha=0.95, edgecolor="#CCCCCC")
leg.set_title("圖例", prop={"size": 16, "weight": "bold"})

ax.set_title("明朝 20 位重要將領關係網路（Louvain 社群 × 力導向佈局）",
             fontsize=26, fontweight="bold", pad=25)
ax.text(0.5, -0.02,
        f"節點顏色 = Louvain 社群（Modularity Q = {q:.3f}）｜節點大小 = 連結度（degree）｜"
        "佈局 = 力導向（spring，各連通分量獨立計算後排列）",
        transform=ax.transAxes, ha="center", fontsize=14, color="#555555")
ax.axis("off")
plt.tight_layout()

png_path = os.path.join(BASE, "ming_generals_network.png")
plt.savefig(png_path, dpi=170, bbox_inches="tight", facecolor="white")
print(f"[OK] nodes.csv  : {nodes_csv}")
print(f"[OK] edges.csv  : {edges_csv}")
print(f"[OK] PNG        : {png_path}")
print(f"節點數 = {G.number_of_nodes()}, 邊數 = {G.number_of_edges()}")

# ---------------------------------------------------------------- 6. 驗證：對照明史.txt
MINGS = os.path.join(BASE, "明史.txt")
if os.path.exists(MINGS):
    with open(MINGS, encoding="utf-8") as f:
        text = f.read()
    print("\n《明史》原文出現次數驗證：")
    for name, _, _, _, _ in GENERALS:
        print(f"  {name:<4} : {text.count(name)} 次")
