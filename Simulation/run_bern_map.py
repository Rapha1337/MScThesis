from bern_map import BernMap

bern_map = BernMap(dist_km=8.0)

node_a, lat_a, lon_a = bern_map.sample_random_node()
node_b, lat_b, lon_b = bern_map.sample_random_node()

print("Node A:", node_a, lat_a, lon_a)
print("Node B:", node_b, lat_b, lon_b)

dist_m = bern_map.shortest_path_length_m(node_a, node_b)
time_min = bern_map.travel_time_minutes(node_a, node_b, speed_kmh=4.8)

print("Distanz (m):", dist_m)
print("Gehzeit (min):", time_min)