from __future__ import annotations

from functools import lru_cache

from app.data.loader import DataLoader
from app.data.validator import DataValidator
from app.data.preprocessing import DataPreprocessor
from app.data.feature_engineering import FeatureEngineer


class DataService:

    def __init__(self):
        self.loader = DataLoader()
        self.validator = DataValidator()
        self.preprocessor = DataPreprocessor()
        self.feature_engineer = FeatureEngineer()

    @lru_cache(maxsize=1)
    def load_data(self):

        # 1. Load raw datasets
        datasets = self.loader.load_all()

        # 2. Validate datasets
        validation = self.validator.validate_all(datasets)

        # 3. Clean / preprocess
        datasets = self.preprocessor.clean_all(datasets)

        # 4. Create engineered order features
        order_features = self.feature_engineer.create_order_features(
            datasets["orders_extended"]
        )

        datasets["order_features"] = order_features

        # Keep both validation and datasets available
        return {
            "datasets": datasets,
            "validation": validation
        }
    