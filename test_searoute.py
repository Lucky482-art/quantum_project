import searoute

# searoute expects [lon, lat] format
origin = [72.8353, 18.9438]  # Mumbai
destination = [4.145, 51.949]  # Rotterdam

route = searoute.searoute(origin, destination)
coords = route['geometry']['coordinates']
print(f"Type: {type(route)}")
print(f"Total points: {len(coords)}")
print(f"First 3 points: {coords[:3]}")
print(f"Last 3 points: {coords[-3:]}")
print(f"Distance km: {route['properties']['length']}")
