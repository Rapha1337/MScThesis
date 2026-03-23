from __future__ import annotations

import random
from typing import Tuple

import numpy as np
import osmnx as ox


class BernMap:
    """
    Einfache Map-Klasse für einen ca. 10x10 km Ausschnitt um Bern.

    - lädt begehbares OSM-Netz
    - kann zufällige Punkte und zufällige Nodes samplen
    - prüft Spawn-Plausibilität über Distanz zum nächsten Node
    - liefert Bounding Box und Node-Infos für Visualisierung
    """

    def __init__(
        self,
        center_lat: float = 46.9480,
        center_lon: float = 7.4474,
        dist_km: float = 5.0,
    ):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.dist_m = dist_km * 1000.0

        print("Lade OSM-Daten für Bern...")
        self.graph = ox.graph_from_point(
            (self.center_lat, self.center_lon),
            dist=self.dist_m,
            network_type="walk",
        )

        self.nodes, self.edges = ox.graph_to_gdfs(self.graph)

        self.node_ids = list(self.graph.nodes)
        self.node_lats = self.nodes["y"].to_numpy()
        self.node_lons = self.nodes["x"].to_numpy()

        self.lat_min = float(self.node_lats.min())
        self.lat_max = float(self.node_lats.max())
        self.lon_min = float(self.node_lons.min())
        self.lon_max = float(self.node_lons.max())

        print(f"Graph geladen: {len(self.node_ids)} Knoten")

    # ============================================================
    # BOUNDS
    # ============================================================

    def get_bbox(self) -> tuple[float, float, float, float]:
        """
        Gibt Bounding Box zurück als:
        (lat_min, lat_max, lon_min, lon_max)
        """
        return self.lat_min, self.lat_max, self.lon_min, self.lon_max

    # ============================================================
    # RANDOM POINTS
    # ============================================================

    def sample_random_point(self) -> tuple[float, float]:
        """
        Sampelt einen zufälligen Punkt in der Bounding Box.
        """
        lat = random.uniform(self.lat_min, self.lat_max)
        lon = random.uniform(self.lon_min, self.lon_max)
        return float(lat), float(lon)

    def sample_valid_spawn(self, max_tries: int = 100, max_dist_m: float = 50.0) -> tuple[float, float]:
        """
        Sampelt einen plausiblen Spawnpunkt in der Bounding Box.
        Ein Punkt ist plausibel, wenn er nahe genug an einem Node liegt.
        """
        for _ in range(max_tries):
            lat, lon = self.sample_random_point()
            if self.is_plausible_spawn(lat, lon, max_dist_m=max_dist_m):
                return lat, lon

        raise RuntimeError("Kein gültiger Spawnpunkt gefunden.")

    # ============================================================
    # RANDOM NODES
    # ============================================================

    def sample_random_node(self) -> tuple[int, float, float]:
        """
        Sampelt direkt einen gültigen OSM-Node.
        """
        node_id = random.choice(self.node_ids)
        node = self.nodes.loc[node_id]
        lat = float(node["y"])
        lon = float(node["x"])
        return int(node_id), lat, lon

    def nearest_node(self, lat: float, lon: float) -> tuple[int, float, float]:
        """
        Gibt den nächsten OSM-Node zu einem Punkt zurück.
        """
        node_id = ox.distance.nearest_nodes(self.graph, lon, lat)
        node = self.nodes.loc[node_id]
        node_lat = float(node["y"])
        node_lon = float(node["x"])
        return int(node_id), node_lat, node_lon

    # ============================================================
    # PLAUSIBILITY CHECK
    # ============================================================

    def is_plausible_spawn(self, lat: float, lon: float, max_dist_m: float = 50.0) -> bool:
        """
        Prüft, ob ein Punkt plausibel als Spawn ist:
        - innerhalb Bounding Box
        - nahe genug an einem begehbaren OSM-Node
        """
        if not (self.lat_min <= lat <= self.lat_max):
            return False
        if not (self.lon_min <= lon <= self.lon_max):
            return False

        node_id, node_lat, node_lon = self.nearest_node(lat, lon)
        del node_id

        dist_m = self.haversine_m(lat, lon, node_lat, node_lon)
        return dist_m <= max_dist_m

    # ============================================================
    # DISTANCE
    # ============================================================

    @staticmethod
    def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Distanz in Metern zwischen zwei Weltkoordinaten.
        """
        r = 6371000.0

        phi1 = np.radians(lat1)
        phi2 = np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)

        a = (
            np.sin(dphi / 2.0) ** 2
            + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
        )
        c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
        return float(r * c)
    
    def neighbors(self, node_id: int) -> list[int]:
        """
        Gibt alle direkten Nachbar-Nodes eines Knotens zurück.
        """
        return list(self.graph.neighbors(node_id))

    def move_to_random_neighbor(self, node_id: int) -> tuple[int, float, float]:
        """
        Bewegt sich von einem Node zu einem zufälligen Nachbar-Node.
        Falls es keine Nachbarn gibt, bleibt der Agent am aktuellen Node.
        """
        neighbors = self.neighbors(node_id)

        if len(neighbors) == 0:
            node = self.nodes.loc[node_id]
            lat = float(node["y"])
            lon = float(node["x"])
            return int(node_id), lat, lon

        next_node_id = random.choice(neighbors)
        node = self.nodes.loc[next_node_id]
        lat = float(node["y"])
        lon = float(node["x"])
        return int(next_node_id), lat, lon

    def normalize_position(self, lat: float, lon: float) -> tuple[float, float]:
        """
        Normiert eine Position innerhalb der Bounding Box auf [0, 1].

        Rückgabe:
            x_norm: normierte Ost-West-Position
            y_norm: normierte Süd-Nord-Position
        """
        x_norm = (lon - self.lon_min) / (self.lon_max - self.lon_min)
        y_norm = (lat - self.lat_min) / (self.lat_max - self.lat_min)

        x_norm = float(np.clip(x_norm, 0.0, 1.0))
        y_norm = float(np.clip(y_norm, 0.0, 1.0))
        return x_norm, y_norm

    def denormalize_position(self, x_norm: float, y_norm: float) -> tuple[float, float]:
        """
        Wandelt normierte Positionswerte [0, 1] zurück in lat/lon um.
        """
        x_norm = float(np.clip(x_norm, 0.0, 1.0))
        y_norm = float(np.clip(y_norm, 0.0, 1.0))

        lon = self.lon_min + x_norm * (self.lon_max - self.lon_min)
        lat = self.lat_min + y_norm * (self.lat_max - self.lat_min)
        return float(lat), float(lon)