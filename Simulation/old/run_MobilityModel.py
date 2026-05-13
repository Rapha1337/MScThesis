from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from bern_map import BernMap
from MobilityModel import MobilityModel

bern_map = BernMap(dist_km=8.0)
mobility = MobilityModel(bern_map)

home_node, _, _ = bern_map.sample_random_node()
gym_node, _, _ = bern_map.sample_random_node()
pool_node, _, _ = bern_map.sample_random_node()
park_node, _, _ = bern_map.sample_random_node()

mobility.set_home(home_node)
mobility.add_poi("gym", gym_node, "fitness")
mobility.add_poi("pool", pool_node, "swimming")
mobility.add_poi("park", park_node, "outdoor")

print("home_node:", mobility.home_node)
print("current_node:", mobility.current_node)
print("is_at_home:", mobility.is_at_home())
print("home_position:", mobility.get_home_position())
print("current_position:", mobility.get_current_position())

features = mobility.get_state_features()
print("state_features:")
for key, value in features.items():
    print(f"  {key}: {value:.2f}")