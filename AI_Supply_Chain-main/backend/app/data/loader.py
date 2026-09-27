from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.config import get_raw_data_path


class DataLoader:

    def __init__(self):

        self.raw_data_path = get_raw_data_path()

    def load_csv(self, filename: str) -> pd.DataFrame:

        file_path = self.raw_data_path / filename

        if not file_path.exists():

            raise FileNotFoundError(
                f"Dataset not found: {file_path}"
            )

        return pd.read_csv(file_path)

    def load_all(self) -> dict[str, pd.DataFrame]:

        files = {
            "orders": "orders.csv",
            "orders_extended": "orders_extended.csv",
            "products": "product_attributes.csv",
            "suppliers": "suppliers.csv",
            "three_pl": "three_pl.csv",
            "cities": "cities_data.csv",
            "routes": "routes.csv",
            "demand": "demand_daily.csv",
            "inventory": "inventory_daily.csv",
            "disruptions": "disruptions.csv",
        }

        datasets = {}

        for name, filename in files.items():

            datasets[name] = self.load_csv(filename)

        return datasets
    