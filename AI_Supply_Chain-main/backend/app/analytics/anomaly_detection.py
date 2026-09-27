import pandas as pd
import numpy as np

from sklearn.ensemble import IsolationForest


class AnomalyDetector:

    def detect_zscore(
        self,
        df: pd.DataFrame,
        column: str,
        threshold: float = 3.0
    ) -> pd.DataFrame:

        result = df.copy()

        values = pd.to_numeric(
            result[column],
            errors="coerce"
        )

        mean = values.mean()
        std = values.std()

        if std == 0 or pd.isna(std):

            result["z_score"] = 0.0
            result["is_anomaly"] = False

            return result

        result["z_score"] = (
            (values - mean) / std
        )

        result["is_anomaly"] = (
            result["z_score"].abs() > threshold
        )

        return result

    def detect_isolation_forest(
        self,
        df: pd.DataFrame,
        column: str,
        contamination: float = 0.02
    ) -> pd.DataFrame:

        result = df.copy()

        values = pd.to_numeric(
            result[column],
            errors="coerce"
        ).fillna(0)

        model = IsolationForest(
            contamination=contamination,
            random_state=42
        )

        predictions = model.fit_predict(
            values.to_numpy().reshape(-1, 1)
        )

        result["is_anomaly"] = (
            predictions == -1
        )

        result["anomaly_score"] = (
            model.decision_function(
                values.to_numpy().reshape(-1, 1)
            )
        )

        return result

    def summarize(
        self,
        df: pd.DataFrame,
        column: str
    ) -> dict:

        result = self.detect_zscore(
            df,
            column
        )

        anomaly_count = int(
            result["is_anomaly"].sum()
        )

        total = len(result)

        anomaly_rate = (
            anomaly_count / total
            if total
            else 0
        )

        return {
            "column": column,
            "total_records": total,
            "anomaly_count": anomaly_count,
            "anomaly_rate": round(
                anomaly_rate * 100,
                2
            )
        }
    