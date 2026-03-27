from __future__ import annotations

import random

import osmnx as ox


class BernMap:
    """
    Map-Klasse für einen Ausschnitt um Bern mit zwei Routing-Netzen:

    - walk_graph: begehbares OSM-Netz
    - drive_graph: fahrbares OSM-Netz

    Zuständigkeiten:
    - lädt beide OSM-Netze
    - kann zufällige gültige OSM-Nodes samplen
    - liefert Node-Positionen
    - berechnet kürzeste Pfade und Weglängen je nach Modus
    - berechnet Reisezeiten entlang des passenden Graphen
    """

    def __init__(
        self,
        center_lat: float = 46.9480,
        center_lon: float = 7.4474,
        dist_km: float = 8.0,
    ):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.dist_m = dist_km * 1000.0

        print("Lade OSM-Walk-Daten für Bern...")
        self.walk_graph = ox.graph_from_point(
            (self.center_lat, self.center_lon),
            dist=self.dist_m,
            network_type="walk",
        )

        print("Lade OSM-Drive-Daten für Bern...")
        self.drive_graph = ox.graph_from_point(
            (self.center_lat, self.center_lon),
            dist=self.dist_m,
            network_type="drive",
        )

        # Für Bounding Box und Visualisierung nehmen wir den walk_graph
        self.nodes, self.edges = ox.graph_to_gdfs(self.walk_graph)

        self.walk_node_ids = list(self.walk_graph.nodes)
        self.drive_node_ids = list(self.drive_graph.nodes)

        self.node_lats = self.nodes["y"].to_numpy()
        self.node_lons = self.nodes["x"].to_numpy()

        self.lat_min = float(self.node_lats.min())
        self.lat_max = float(self.node_lats.max())
        self.lon_min = float(self.node_lons.min())
        self.lon_max = float(self.node_lons.max())

        print(f"Walk-Graph geladen: {len(self.walk_node_ids)} Knoten")
        print(f"Drive-Graph geladen: {len(self.drive_node_ids)} Knoten")

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
    # INTERNAL HELPERS
    # ============================================================

    def _get_graph_for_mode(self, mode: str):
        """
        Wählt den passenden Graphen für einen Bewegungsmodus.
        """
        if mode in ("walk", "bike"):
            return self.walk_graph
        if mode == "drive":
            return self.drive_graph

        raise ValueError(f"Unsupported mode: {mode}")

    def _get_node_ids_for_mode(self, mode: str) -> list[int]:
        """
        Liefert die Node-Liste des passenden Graphen.
        """
        if mode in ("walk", "bike"):
            return self.walk_node_ids
        if mode == "drive":
            return self.drive_node_ids

        raise ValueError(f"Unsupported mode: {mode}")

    # ============================================================
    # NODES
    # ============================================================

    def sample_random_node(
        self,
        mode: str = "walk",
    ) -> tuple[int, float, float]:
        """
        Sampelt direkt einen gültigen OSM-Node aus dem passenden Graphen.
        """
        graph = self._get_graph_for_mode(mode)
        node_ids = self._get_node_ids_for_mode(mode)

        node_id = random.choice(node_ids)
        node = graph.nodes[node_id]
        lat = float(node["y"])
        lon = float(node["x"])
        return int(node_id), lat, lon

    def nearest_node(
        self,
        lat: float,
        lon: float,
        mode: str = "walk",
    ) -> tuple[int, float, float]:
        """
        Gibt den nächsten OSM-Node im passenden Graphen zu einem Punkt zurück.
        """
        graph = self._get_graph_for_mode(mode)
        node_id = ox.distance.nearest_nodes(graph, lon, lat)
        node_lat, node_lon = self.get_node_position(node_id, mode=mode)
        return int(node_id), node_lat, node_lon

    def get_node_position(
        self,
        node_id: int,
        mode: str = "walk",
    ) -> tuple[float, float]:
        """
        Gibt die Position eines OSM-Nodes als (lat, lon) zurück.
        """
        graph = self._get_graph_for_mode(mode)
        node = graph.nodes[node_id]
        lat = float(node["y"])
        lon = float(node["x"])
        return lat, lon

    # ============================================================
    # ROUTING
    # ============================================================

    def shortest_path_nodes(
        self,
        source_node: int,
        target_node: int,
        mode: str = "walk",
    ) -> list[int]:
        """
        Kürzester Pfad auf dem passenden Graphen als Liste von Node-IDs.
        Verwendet Kantenlänge ('length') in Metern als Gewicht.
        """
        graph = self._get_graph_for_mode(mode)

        route = ox.routing.shortest_path(
            graph,
            source_node,
            target_node,
            weight="length",
        )

        if route is None:
            raise ValueError(
                f"Kein Pfad gefunden zwischen {source_node} und {target_node} für mode='{mode}'."
            )

        return list(route)

    def shortest_path_length_m(
        self,
        source_node: int,
        target_node: int,
        mode: str = "walk",
    ) -> float:
        """
        Länge des kürzesten Pfads auf dem passenden Graphen in Metern.
        """
        graph = self._get_graph_for_mode(mode)
        route = self.shortest_path_nodes(source_node, target_node, mode=mode)

        if len(route) < 2:
            return 0.0

        total_length_m = 0.0

        for u, v in zip(route[:-1], route[1:]):
            edge_data = graph.get_edge_data(u, v)

            if edge_data is None:
                raise ValueError(
                    f"Keine Kantendaten gefunden für Edge {u} -> {v} im mode='{mode}'."
                )

            edge_lengths = []
            for _, attrs in edge_data.items():
                if "length" in attrs:
                    edge_lengths.append(float(attrs["length"]))

            if len(edge_lengths) == 0:
                raise ValueError(
                    f"Keine 'length'-Information gefunden für Edge {u} -> {v} im mode='{mode}'."
                )

            total_length_m += min(edge_lengths)

        return float(total_length_m)

    def travel_time_minutes(
        self,
        source_node: int,
        target_node: int,
        speed_kmh: float,
        mode: str = "walk",
    ) -> float:
        """
        Reisezeit in Minuten entlang des passenden Graphen bei gegebener mittlerer Geschwindigkeit.
        """
        if speed_kmh <= 0:
            raise ValueError("speed_kmh must be > 0")

        distance_m = self.shortest_path_length_m(
            source_node,
            target_node,
            mode=mode,
        )
        speed_m_per_min = speed_kmh * 1000.0 / 60.0
        return float(distance_m / speed_m_per_min)

    # ============================================================
    # POSITION-BASED ROUTING
    # ============================================================

    def shortest_path_nodes_from_positions(
        self,
        source_lat: float,
        source_lon: float,
        target_lat: float,
        target_lon: float,
        mode: str = "walk",
    ) -> list[int]:
        """
        Kürzester Pfad zwischen zwei Weltkoordinaten.
        Die Koordinaten werden zuerst auf den passenden Graphen gemappt.
        """
        source_node, _, _ = self.nearest_node(source_lat, source_lon, mode=mode)
        target_node, _, _ = self.nearest_node(target_lat, target_lon, mode=mode)
        return self.shortest_path_nodes(source_node, target_node, mode=mode)

    def travel_time_minutes_from_positions(
        self,
        source_lat: float,
        source_lon: float,
        target_lat: float,
        target_lon: float,
        speed_kmh: float,
        mode: str = "walk",
    ) -> float:
        """
        Reisezeit zwischen zwei Weltkoordinaten auf dem passenden Graphen.
        """
        source_node, _, _ = self.nearest_node(source_lat, source_lon, mode=mode)
        target_node, _, _ = self.nearest_node(target_lat, target_lon, mode=mode)
        return self.travel_time_minutes(
            source_node=source_node,
            target_node=target_node,
            speed_kmh=speed_kmh,
            mode=mode,
        )
