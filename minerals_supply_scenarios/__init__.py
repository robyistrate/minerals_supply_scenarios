__version__ = (0, 0, 1)

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

from .supply_scenarios import MetalSupplyScenarios
