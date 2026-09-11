"""PWNUAV - vulnerable-by-design MAVLink drone lab."""
import os
# setdefault won't override an externally-set MAVLINK20, which is acceptable for this lab
os.environ.setdefault("MAVLINK20", "1")

__version__ = "0.1.0"
