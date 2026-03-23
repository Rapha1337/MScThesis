from pathlib import Path
import random

import matplotlib.pyplot as plt
import osmnx as ox

from bern_map import BernMap

SAVE_DIR = Path("plots")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

SEED = random.randint(0, 999999)
random.seed(SEED)

print(f"Seed: {SEED}")

m = BernMap()

# ------------------------------------------------------------
# 1) Spawn als plausibler Punkt in der Bounding Box
# ------------------------------------------------------------
spawn_lat, spawn_lon = m.sample_valid_spawn(max_dist_m=50.0)
nearest_node_id, node_lat, node_lon = m.nearest_node(spawn_lat, spawn_lon)
dist_to_node = m.haversine_m(spawn_lat, spawn_lon, node_lat, node_lon)

print("\n=== Spawn über plausiblen Punkt ===")
print(f"Spawnpunkt: lat={spawn_lat:.6f}, lon={spawn_lon:.6f}")
print(f"Nächster Node: {nearest_node_id}")
print(f"Node-Koordinate: lat={node_lat:.6f}, lon={node_lon:.6f}")
print(f"Distanz Spawn -> nächster Node: {dist_to_node:.2f} m")
print(f"Plausibel: {m.is_plausible_spawn(spawn_lat, spawn_lon)}")

# ------------------------------------------------------------
# 2) Spawn direkt auf gültigem OSM-Node
# ------------------------------------------------------------
random_node_id, random_node_lat, random_node_lon = m.sample_random_node()

print("\n=== Spawn direkt auf OSM-Node ===")
print(f"Node-ID: {random_node_id}")
print(f"Node-Koordinate: lat={random_node_lat:.6f}, lon={random_node_lon:.6f}")

# ------------------------------------------------------------
# 3) Visualisierung
# ------------------------------------------------------------
fig, ax = ox.plot_graph(
    m.graph,
    show=False,
    close=False,
    node_size=0,
    edge_linewidth=0.4,
    bgcolor="white",
)

# plausibler Spawnpunkt
ax.scatter(
    spawn_lon,
    spawn_lat,
    s=60,
    c="red",
    label="Plausibler Spawnpunkt",
    zorder=5,
)

# nächster Node dazu
ax.scatter(
    node_lon,
    node_lat,
    s=35,
    c="orange",
    label="Nächster OSM-Node",
    zorder=6,
)

# direkter Node-Spawn
ax.scatter(
    random_node_lon,
    random_node_lat,
    s=45,
    c="blue",
    label="Direkter Node-Spawn",
    zorder=7,
)

# Verbindung plausibler Punkt -> nächster Node
ax.plot(
    [spawn_lon, node_lon],
    [spawn_lat, node_lat],
    linestyle="--",
    linewidth=1.2,
    color="gray",
    zorder=4,
)

ax.set_title("BernMap: Spawnpunkte im begehbaren OSM-Netz")
ax.legend(loc="upper right")

outfile = SAVE_DIR / "bern_map_spawn_demo.png"
plt.savefig(outfile, dpi=200, bbox_inches="tight")
plt.close()

print(f"\nPlot gespeichert unter: {outfile}")