"""Shared configuration. One place to change things."""

CITIES = {
    "liverpool": {"south": 53.35, "north": 53.45, "west": -3.02, "east": -2.85},
    "cambridge": {"south": 52.17, "north": 52.25, "west": 0.09, "east": 0.18},
}

# Coordinate reference systems
WGS84 = "EPSG:4326"        # lat/lon
BNG = "EPSG:27700"         # British National Grid, metres

# Allocation parameters
ALLOCATION_RADIUS_M = 250.0     # ignore racks further than this from a theft
KERNEL_SIGMA_M = 100.0          # 
TARGET_RACK_SHARE = 0.40        # fraction of thefts occurring at public parking

RAW = "data/raw"
INTERIM = "data/interim"
SITE = "site"