from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import matplotlib.pyplot as plt
import numpy as np

from env_time_weather import TimeWeatherEnv


CATEGORY_COLORS = {
    "gym": "red",
    "pool": "deepskyblue",
    "park": "green",
}


def get_all_poi_positions(env: TimeWeatherEnv) -> dict[str, list[tuple[str, int, float, float]]]:
    """
    Liefert alle POIs gruppiert nach Kategorie.

    Rückgabeformat:
        {
            "gym": [("Gym 1", node_id, lat, lon), ...],
            "pool": [...],
            ...
        }
    """
    result: dict[str, list[tuple[str, int, float, float]]] = {}

    for category in env.mobility.get_categories():
        result[category] = []
        pois = env.mobility.get_pois_in_category(category)
        for poi in pois:
            lat, lon = env.map.get_node_position(poi.node_id, mode="walk")
            result[category].append((poi.name, poi.node_id, lat, lon))

    return result


def plot_map_state(
    env: TimeWeatherEnv,
    title: str,
    route_nodes: list[int] | None = None,
    route_mode: str = "walk",
    save_path: str | None = None,
) -> None:
    """
    Plottet:
    - OSM-Graph (walk graph als Hintergrund)
    - home
    - current location
    - alle POIs
    - optionale Route
    """
    fig, ax = plt.subplots(figsize=(10, 10))

    # ------------------------------------------------------------
    # 1) gesamten Walk-Graph dezent plotten
    # ------------------------------------------------------------
    node_x = env.map.nodes["x"].to_numpy()
    node_y = env.map.nodes["y"].to_numpy()
    ax.scatter(node_x, node_y, s=1, alpha=0.15, label="_walk_graph")

    # ------------------------------------------------------------
    # 2) optionale Route plotten
    # ------------------------------------------------------------
    if route_nodes is not None and len(route_nodes) >= 2:
        route_lons = []
        route_lats = []
        for node_id in route_nodes:
            lat, lon = env.map.get_node_position(node_id, mode=route_mode)
            route_lats.append(lat)
            route_lons.append(lon)

        ax.plot(
            route_lons,
            route_lats,
            linewidth=2.5,
            alpha=0.9,
            label=f"route ({route_mode})",
        )

    # ------------------------------------------------------------
    # 3) Home plotten
    # ------------------------------------------------------------
    home_lat, home_lon = env.mobility.get_home_position()
    ax.scatter(
        [home_lon],
        [home_lat],
        s=160,
        marker="^",
        label="home",
    )

    # ------------------------------------------------------------
    # 4) Current location plotten
    # ------------------------------------------------------------
    current_lat, current_lon = env.mobility.get_current_position()
    ax.scatter(
        [current_lon],
        [current_lat],
        s=120,
        marker="o",
        label="current position",
    )

    # ------------------------------------------------------------
    # 5) POIs plotten
    # ------------------------------------------------------------
    poi_positions = get_all_poi_positions(env)

    for category, entries in poi_positions.items():
        color = CATEGORY_COLORS.get(category, "gray")

        lons = [entry[3] for entry in entries]
        lats = [entry[2] for entry in entries]

        ax.scatter(
            lons,
            lats,
            s=90,
            marker="s",
            color=color,
            alpha=0.9,
            label=category,
        )

        for name, _, lat, lon in entries:
            ax.annotate(
                name,
                xy=(lon, lat),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=8,
                alpha=0.9,
            )

    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend()
    ax.set_aspect("equal", adjustable="box")
    plt.tight_layout()

    if save_path is not None:
        plt.savefig(save_path, dpi=200, bbox_inches="tight")

    plt.show()


def plot_travel_times(env: TimeWeatherEnv, save_path: str | None = None) -> None:
    """
    Balkendiagramm für Travel Times zu den nächstgelegenen POIs.
    """
    categories = env.mobility.get_categories()

    walk_times = [
        env.mobility.get_travel_time_to_nearest_minutes(category, mode="walk")
        for category in categories
    ]
    bike_times = [
        env.mobility.get_travel_time_to_nearest_minutes(category, mode="bike")
        for category in categories
    ]
    drive_times = [
        env.mobility.get_travel_time_to_nearest_minutes(category, mode="drive")
        for category in categories
    ]

    x = np.arange(len(categories))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width, walk_times, width, label="walk")
    ax.bar(x, bike_times, width, label="bike")
    ax.bar(x + width, drive_times, width, label="drive")

    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.set_ylabel("Minutes")
    ax.set_title("Travel times to nearest POIs")
    ax.legend()
    plt.tight_layout()

    if save_path is not None:
        plt.savefig(save_path, dpi=200, bbox_inches="tight")

    plt.show()


def print_state_summary(env: TimeWeatherEnv, label: str) -> None:
    """
    Konsolenübersicht zum aktuellen Zustand.
    """
    lat, lon = env.mobility.get_current_position()
    print(f"\n--- {label} ---")
    print(f"t = {env._t}")
    print(f"home_node = {env.mobility.home_node}")
    print(f"current_node = {env.mobility.current_node}")
    print(f"current_position = ({lat:.6f}, {lon:.6f})")
    print(f"is_at_home = {env.mobility.is_at_home()}")

    for category in env.mobility.get_categories():
        walk_t = env.mobility.get_travel_time_to_nearest_minutes(category, mode="walk")
        bike_t = env.mobility.get_travel_time_to_nearest_minutes(category, mode="bike")
        drive_t = env.mobility.get_travel_time_to_nearest_minutes(category, mode="drive")

        print(
            f"{category}: "
            f"walk={walk_t:.2f} min, "
            f"bike={bike_t:.2f} min, "
            f"drive={drive_t:.2f} min"
        )


def compute_route_for_last_action(
    env: TimeWeatherEnv,
    old_lat: float,
    old_lon: float,
    mobility_info: dict,
) -> tuple[list[int] | None, str]:
    """
    Berechnet die Route der letzten Aktion passend zum verwendeten Modus.
    """
    target_node = mobility_info["target_node"]
    mode = mobility_info["mode"]

    if target_node is None or mode is None:
        return None, "walk"

    if mode in ("walk", "bike"):
        old_walk_node, _, _ = env.map.nearest_node(old_lat, old_lon, mode="walk")
        route_nodes = env.map.shortest_path_nodes(
            old_walk_node,
            int(target_node),
            mode="walk",
        )
        return route_nodes, "walk"

    if mode == "drive":
        target_lat, target_lon = env.map.get_node_position(int(target_node), mode="walk")
        route_nodes = env.map.shortest_path_nodes_from_positions(
            source_lat=old_lat,
            source_lon=old_lon,
            target_lat=target_lat,
            target_lon=target_lon,
            mode="drive",
        )
        return route_nodes, "drive"

    return None, "walk"


def run_demo(seed: int = 38) -> None:
    """
    Führt eine kleine Demo aus:
    - reset
    - Startzustand visualisieren
    - random activity ausführen
    - Endzustand + Route visualisieren
    """
    env = TimeWeatherEnv()
    obs, info = env.reset(seed=seed)
    del obs, info

    print_state_summary(env, "Initial state")
    plot_map_state(env, title="Initial state: home, current position and POIs")
    plot_travel_times(env)

    old_lat, old_lon = env.mobility.get_current_position()

    obs, reward, terminated, truncated, info = env.step(1)
    del obs, reward, terminated, truncated

    mobility_info = info["mobility"]
    route_nodes, route_mode = compute_route_for_last_action(
        env,
        old_lat=old_lat,
        old_lon=old_lon,
        mobility_info=mobility_info,
    )

    print("\n--- After action=1 ---")
    print(f"action_name = {info['action_name']}")
    print(f"delta_hours = {info['delta_hours']}")
    print(f"mobility_info = {mobility_info}")

    print_state_summary(env, "State after random activity")

    title = (
        f"After action=1 | target={mobility_info['target_category']} | "
        f"mode={mobility_info['mode']} | "
        f"travel_time_min={mobility_info['travel_time_min']:.1f}"
    )
    plot_map_state(
        env,
        title=title,
        route_nodes=route_nodes,
        route_mode=route_mode,
    )
    plot_travel_times(env)


if __name__ == "__main__":
    run_demo(seed=38)