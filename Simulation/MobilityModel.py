# Legacy OSM/BernMap mobility model. Keep this file in place for existing
# environment imports and tests; use accessibility_model.py for lightweight
# survey-distance accessibility values in LLM context generation.
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from bern_map import BernMap


@dataclass
class POI:
    """
    Point of Interest.
    """
    name: str
    node_id: int
    category: str


class MobilityModel:
    """
    Einfache Mobilitätslogik für einen Agenten auf Basis von BernMap.

    Version 3:
    - Home-Standort
    - aktueller Standort
    - mehrere POIs pro Kategorie
    - Reisezeiten zum nächstgelegenen POI
    - Modi: walk, bike, drive
    - drive nutzt den drive_graph über positionsbasiertes Routing
    - State-Features für das Environment
    """

    def __init__(
        self,
        bern_map: BernMap,
        walk_speed_kmh: float = 4.8,
        bike_speed_kmh: float = 15.0,
        drive_speed_kmh: float = 30.0,
    ):
        self.map = bern_map

        self.walk_speed_kmh = walk_speed_kmh
        self.bike_speed_kmh = bike_speed_kmh
        self.drive_speed_kmh = drive_speed_kmh

        # Home und Current bleiben als walk-nodes gespeichert
        self.home_node: Optional[int] = None
        self.current_node: Optional[int] = None

        self.pois_by_category: dict[str, list[POI]] = {}

    # ============================================================
    # SETUP
    # ============================================================

    def set_home(self, node_id: int) -> None:
        """
        Setzt den Home-Standort des Agenten.
        Beim ersten Setzen wird current_node ebenfalls auf home gesetzt.
        """
        self.home_node = int(node_id)

        if self.current_node is None:
            self.current_node = int(node_id)

    def reset_to_home(self) -> None:
        """
        Setzt den aktuellen Standort zurück auf home.
        """
        if self.home_node is None:
            raise ValueError("home_node is not set")

        self.current_node = int(self.home_node)

    def set_current_node(self, node_id: int) -> None:
        """
        Setzt den aktuellen Standort explizit.
        """
        self.current_node = int(node_id)

    def add_poi(self, category: str, node_id: int, name: Optional[str] = None) -> None:
        """
        Fügt einen Point of Interest zu einer Kategorie hinzu.

        Beispiel:
            add_poi("gym", 12345, name="Gym West")
        """
        category = str(category)

        if category not in self.pois_by_category:
            self.pois_by_category[category] = []

        if name is None:
            name = f"{category}_{len(self.pois_by_category[category]) + 1}"

        poi = POI(
            name=name,
            node_id=int(node_id),
            category=category,
        )
        self.pois_by_category[category].append(poi)

    def clear_pois(self) -> None:
        """
        Entfernt alle aktuell gespeicherten POIs.
        """
        self.pois_by_category.clear()

    def clear_category(self, category: str) -> None:
        """
        Entfernt alle POIs einer Kategorie.
        """
        self.pois_by_category.pop(category, None)

    # ============================================================
    # GETTERS
    # ============================================================

    def get_home_position(self) -> tuple[float, float]:
        """
        Gibt die Position von home als (lat, lon) zurück.
        """
        if self.home_node is None:
            raise ValueError("home_node is not set")

        return self.map.get_node_position(self.home_node, mode="walk")

    def get_current_position(self) -> tuple[float, float]:
        """
        Gibt die aktuelle Position als (lat, lon) zurück.
        """
        if self.current_node is None:
            raise ValueError("current_node is not set")

        return self.map.get_node_position(self.current_node, mode="walk")

    def is_at_home(self) -> bool:
        """
        Prüft, ob sich der Agent aktuell zuhause befindet.
        """
        if self.home_node is None or self.current_node is None:
            return False

        return self.current_node == self.home_node

    def get_categories(self) -> list[str]:
        """
        Gibt alle aktuell vorhandenen POI-Kategorien zurück.
        """
        return list(self.pois_by_category.keys())

    def get_pois_in_category(self, category: str) -> list[POI]:
        """
        Gibt alle POIs einer Kategorie zurück.
        """
        if category not in self.pois_by_category:
            return []

        return self.pois_by_category[category]

    # ============================================================
    # INTERNAL HELPERS
    # ============================================================

    def _get_speed_kmh(self, mode: str) -> float:
        """
        Liefert die Geschwindigkeit für einen Bewegungsmodus.
        """
        if mode == "walk":
            return self.walk_speed_kmh
        if mode == "bike":
            return self.bike_speed_kmh
        if mode == "drive":
            return self.drive_speed_kmh

        raise ValueError(f"Unsupported mode: {mode}")

    def _require_current_node(self) -> int:
        """
        Stellt sicher, dass current_node gesetzt ist.
        """
        if self.current_node is None:
            raise ValueError("current_node is not set")

        return self.current_node

    def _require_category(self, category: str) -> list[POI]:
        """
        Stellt sicher, dass eine Kategorie existiert und POIs enthält.
        """
        if category not in self.pois_by_category:
            raise KeyError(f"Unknown POI category: {category}")

        pois = self.pois_by_category[category]
        if len(pois) == 0:
            raise ValueError(f"No POIs stored for category: {category}")

        return pois

    def _get_poi_position(self, poi: POI) -> tuple[float, float]:
        """
        Position eines POI als (lat, lon).
        POIs sind als walk-node gespeichert.
        """
        return self.map.get_node_position(poi.node_id, mode="walk")

    # ============================================================
    # DISTANCES / TIMES TO NEAREST POI
    # ============================================================

    def get_distance_to_nearest_m(self, category: str, mode: str = "walk") -> float:
        """
        Distanz entlang des passenden Graphen zum naechstgelegenen erreichbaren POI
        einer Kategorie.

        Robust gegen unreachable routes:
        - Unerreichbare POIs werden uebersprungen
        - Nur wenn kein POI erreichbar ist, wird ein Fehler geworfen
        """
        current_node = self._require_current_node()
        pois = self._require_category(category)

        if mode in ("walk", "bike"):
            distances = []
            for poi in pois:
                try:
                    d = self.map.shortest_path_length_m(
                        current_node,
                        poi.node_id,
                        mode="walk",
                    )
                    distances.append(float(d))
                except ValueError:
                    continue

            if len(distances) == 0:
                raise ValueError(
                    f"No reachable POIs found for category='{category}' and mode='{mode}'."
                )

            return float(min(distances))

        if mode == "drive":
            current_lat, current_lon = self.get_current_position()

            distances = []
            for poi in pois:
                try:
                    poi_lat, poi_lon = self._get_poi_position(poi)

                    source_drive_node, _, _ = self.map.nearest_node(
                        current_lat,
                        current_lon,
                        mode="drive",
                    )
                    target_drive_node, _, _ = self.map.nearest_node(
                        poi_lat,
                        poi_lon,
                        mode="drive",
                    )

                    distance_m = self.map.shortest_path_length_m(
                        source_drive_node,
                        target_drive_node,
                        mode="drive",
                    )
                    distances.append(float(distance_m))
                except ValueError:
                    continue

            if len(distances) == 0:
                raise ValueError(
                    f"No reachable POIs found for category='{category}' and mode='drive'."
                )

            return float(min(distances))

        raise ValueError(f"Unsupported mode: {mode}")

    def get_travel_time_to_nearest_minutes(self, category: str, mode: str = "walk") -> float:
        """
        Reisezeit zum naechstgelegenen erreichbaren POI einer Kategorie.

        Robust gegen unreachable routes:
        - Unerreichbare POIs werden uebersprungen
        - Nur wenn kein POI erreichbar ist, wird ein Fehler geworfen
        """
        current_node = self._require_current_node()
        pois = self._require_category(category)
        speed_kmh = self._get_speed_kmh(mode)

        if mode in ("walk", "bike"):
            travel_times = []
            for poi in pois:
                try:
                    t = self.map.travel_time_minutes(
                        source_node=current_node,
                        target_node=poi.node_id,
                        speed_kmh=speed_kmh,
                        mode="walk",
                    )
                    travel_times.append(float(t))
                except ValueError:
                    continue

            if len(travel_times) == 0:
                raise ValueError(
                    f"No reachable POIs found for category='{category}' and mode='{mode}'."
                )

            return float(min(travel_times))

        if mode == "drive":
            current_lat, current_lon = self.get_current_position()

            travel_times = []
            for poi in pois:
                try:
                    poi_lat, poi_lon = self._get_poi_position(poi)

                    travel_time_min = self.map.travel_time_minutes_from_positions(
                        source_lat=current_lat,
                        source_lon=current_lon,
                        target_lat=poi_lat,
                        target_lon=poi_lon,
                        speed_kmh=speed_kmh,
                        mode="drive",
                    )
                    travel_times.append(float(travel_time_min))
                except ValueError:
                    continue

            if len(travel_times) == 0:
                raise ValueError(
                    f"No reachable POIs found for category='{category}' and mode='drive'."
                )

            return float(min(travel_times))

        raise ValueError(f"Unsupported mode: {mode}")

    def get_nearest_poi(self, category: str, mode: str = "walk") -> POI:
        """
        Gibt den naechstgelegenen erreichbaren POI einer Kategorie fuer den gewaehlten Modus zurueck.

        Robust gegen unreachable routes:
        - Unerreichbare POIs werden uebersprungen
        - Nur wenn kein POI erreichbar ist, wird ein Fehler geworfen
        """
        current_node = self._require_current_node()
        pois = self._require_category(category)

        if mode in ("walk", "bike"):
            candidates: list[tuple[POI, float]] = []

            for poi in pois:
                try:
                    dist = self.map.shortest_path_length_m(
                        current_node,
                        poi.node_id,
                        mode="walk",
                    )
                    candidates.append((poi, float(dist)))
                except ValueError:
                    continue

            if len(candidates) == 0:
                raise ValueError(
                    f"No reachable POIs found for category='{category}' and mode='{mode}'."
                )

            nearest_poi, _ = min(candidates, key=lambda x: x[1])
            return nearest_poi

        if mode == "drive":
            current_lat, current_lon = self.get_current_position()

            candidates: list[tuple[POI, float]] = []

            for poi in pois:
                try:
                    poi_lat, poi_lon = self._get_poi_position(poi)

                    travel_time_min = self.map.travel_time_minutes_from_positions(
                        source_lat=current_lat,
                        source_lon=current_lon,
                        target_lat=poi_lat,
                        target_lon=poi_lon,
                        speed_kmh=self.drive_speed_kmh,
                        mode="drive",
                    )
                    candidates.append((poi, float(travel_time_min)))
                except ValueError:
                    continue

            if len(candidates) == 0:
                raise ValueError(
                    f"No reachable POIs found for category='{category}' and mode='drive'."
                )

            nearest_poi, _ = min(candidates, key=lambda x: x[1])
            return nearest_poi

        raise ValueError(f"Unsupported mode: {mode}")

    # ============================================================
    # MOVEMENT
    # ============================================================

    def go_to_nearest(self, category: str, mode: str = "walk") -> dict[str, float | str | int]:
        """
        Bewegt den Agenten direkt zum nächstgelegenen POI einer Kategorie.

        Rückgabe:
            Infos über Ziel, Distanz und Reisezeit.
        """
        self._require_current_node()
        nearest_poi = self.get_nearest_poi(category, mode=mode)

        distance_m = self.get_distance_to_nearest_m(category, mode=mode)
        travel_time_min = self.get_travel_time_to_nearest_minutes(category, mode=mode)

        # Aktuellen Standort weiter als walk-node speichern:
        # wir "landen" beim POI selbst (der als walk-node gespeichert ist)
        self.current_node = int(nearest_poi.node_id)

        return {
            "target_category": nearest_poi.category,
            "target_name": nearest_poi.name,
            "target_node": nearest_poi.node_id,
            "mode": mode,
            "distance_m": float(distance_m),
            "travel_time_min": float(travel_time_min),
        }

    def go_home(self, mode: str = "walk") -> dict[str, float | str | int]:
        """
        Bewegt den Agenten direkt zurück nach Hause.
        """
        if self.home_node is None:
            raise ValueError("home_node is not set")

        current_node = self._require_current_node()
        speed_kmh = self._get_speed_kmh(mode)

        if mode in ("walk", "bike"):
            distance_m = self.map.shortest_path_length_m(
                current_node,
                self.home_node,
                mode="walk",
            )
            travel_time_min = self.map.travel_time_minutes(
                source_node=current_node,
                target_node=self.home_node,
                speed_kmh=speed_kmh,
                mode="walk",
            )
        elif mode == "drive":
            current_lat, current_lon = self.get_current_position()
            home_lat, home_lon = self.get_home_position()

            source_drive_node, _, _ = self.map.nearest_node(
                current_lat,
                current_lon,
                mode="drive",
            )
            target_drive_node, _, _ = self.map.nearest_node(
                home_lat,
                home_lon,
                mode="drive",
            )

            distance_m = self.map.shortest_path_length_m(
                source_drive_node,
                target_drive_node,
                mode="drive",
            )
            travel_time_min = self.map.travel_time_minutes(
                source_node=source_drive_node,
                target_node=target_drive_node,
                speed_kmh=speed_kmh,
                mode="drive",
            )
        else:
            raise ValueError(f"Unsupported mode: {mode}")

        self.current_node = int(self.home_node)

        return {
            "target_category": "home",
            "target_name": "home",
            "target_node": self.home_node,
            "mode": mode,
            "distance_m": float(distance_m),
            "travel_time_min": float(travel_time_min),
        }

    # ============================================================
    # STATE FEATURES
    # ============================================================

    def get_state_features(
        self,
        include_walk: bool = True,
        include_bike: bool = True,
        include_drive: bool = False,
    ) -> dict[str, float]:
        """
        Liefert verhaltensrelevante räumliche Features für das Environment.

        Standard:
        - is_at_home
        - Gehzeiten zu nächstgelegenen POIs
        - Fahrradzeiten zu nächstgelegenen POIs

        Autofahrzeiten sind optional, damit der State nicht unnötig groß wird.
        """
        self._require_current_node()

        features: dict[str, float] = {
            "is_at_home": float(self.is_at_home()),
        }

        for category in self.get_categories():
            if include_walk:
                features[f"minutes_to_nearest_{category}_walk"] = (
                    self.get_travel_time_to_nearest_minutes(category, mode="walk")
                )

            if include_bike:
                features[f"minutes_to_nearest_{category}_bike"] = (
                    self.get_travel_time_to_nearest_minutes(category, mode="bike")
                )

            if include_drive:
                features[f"minutes_to_nearest_{category}_drive"] = (
                    self.get_travel_time_to_nearest_minutes(category, mode="drive")
                )

        return features
    