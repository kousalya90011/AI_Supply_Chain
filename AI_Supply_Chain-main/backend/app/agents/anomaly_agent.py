from __future__ import annotations

import pandas as pd


class AnomalyAgent:

    def __init__(self, data_service):
        self.data_service = data_service

    def run(
        self,
        column: str = "delay_days",
        top_n: int = 10
    ) -> dict:

        try:

            # -------------------------------------------------
            # Load data
            # -------------------------------------------------

            datasets = (
                self.data_service
                .load_data()
                .get("datasets", {})
            )

            orders = datasets.get("order_features")

            if orders is None or orders.empty:
                return {
                    "status": "error",
                    "message": "Order data is not available."
                }

            # -------------------------------------------------
            # Validate column
            # -------------------------------------------------

            if column not in orders.columns:
                return {
                    "status": "error",
                    "message": (
                        f"Column '{column}' is not available. "
                        f"Available columns: "
                        f"{list(orders.columns)}"
                    )
                }

            df = orders.copy()

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

            df = df.dropna(
                subset=[column]
            )

            if df.empty:
                return {
                    "status": "error",
                    "message": (
                        f"No numeric values found in {column}."
                    )
                }

            total_records = len(df)

            # -------------------------------------------------
            # Zero-inflated delay handling
            # -------------------------------------------------
            #
            # delay_days commonly contains:
            #
            # 0 = on-time
            # 1 = one-day delay
            # 2 = two-day delay
            # ...
            #
            # If we calculate IQR over all values and most
            # values are 0, Q1 and Q3 can both become 0.
            #
            # Therefore, for delay_days we calculate the
            # anomaly threshold using POSITIVE delays only.
            # -------------------------------------------------

            if column == "delay_days":

                positive_delays = df[
                    df[column] > 0
                ].copy()

                if positive_delays.empty:
                    return {
                        "status": "success",
                        "agent": "Anomaly Detection Agent",
                        "findings": [
                            {
                                "column": column,
                                "total_records": total_records,
                                "anomaly_count": 0,
                                "anomaly_rate": 0.0,
                                "q1": 0.0,
                                "q3": 0.0,
                                "iqr": 0.0,
                                "lower_bound": 0.0,
                                "upper_bound": 0.0,
                                "analysis_population": 0,
                                "zero_delay_records": total_records,
                                "top_anomalies": []
                            }
                        ],
                        "evidence": [
                            {
                                "column": column,
                                "total_records": total_records,
                                "anomaly_count": 0,
                                "anomaly_rate": 0.0,
                                "q1": 0.0,
                                "q3": 0.0,
                                "iqr": 0.0,
                                "lower_bound": 0.0,
                                "upper_bound": 0.0,
                                "analysis_population": 0,
                                "zero_delay_records": total_records,
                                "top_anomalies": []
                            }
                        ],
                        "source": {
                            "dataset": "order_features",
                            "method": "IQR_positive_delays"
                        }
                    }

                analysis_df = positive_delays

            else:

                # For other numerical columns, use the
                # standard IQR approach.
                analysis_df = df.copy()

            # -------------------------------------------------
            # Calculate IQR
            # -------------------------------------------------

            q1 = analysis_df[column].quantile(0.25)

            q3 = analysis_df[column].quantile(0.75)

            iqr = q3 - q1

            lower_bound = (
                q1 - 1.5 * iqr
            )

            upper_bound = (
                q3 + 1.5 * iqr
            )

            # -------------------------------------------------
            # Detect anomalies
            # -------------------------------------------------

            anomalies = analysis_df[
                (analysis_df[column] < lower_bound)
                |
                (analysis_df[column] > upper_bound)
            ].copy()

            anomaly_count = len(anomalies)

            anomaly_rate = (
                anomaly_count / total_records
                if total_records
                else 0
            )

            # -------------------------------------------------
            # Calculate deviation
            # -------------------------------------------------

            median_value = (
                analysis_df[column].median()
            )

            anomalies["deviation"] = (
                abs(
                    anomalies[column]
                    - median_value
                )
            )

            anomalies = anomalies.sort_values(
                "deviation",
                ascending=False
            )

            # -------------------------------------------------
            # Select useful evidence columns
            # -------------------------------------------------

            display_columns = [
                column
            ]

            for candidate in [
                "order_id",
                "product_id",
                "supplier_id",
                "three_pl",
                "route_id"
            ]:

                if candidate in anomalies.columns:

                    display_columns.append(
                        candidate
                    )

            top_anomalies = (
                anomalies[
                    display_columns
                ]
                .head(top_n)
                .to_dict(
                    orient="records"
                )
            )

            # -------------------------------------------------
            # Additional statistics
            # -------------------------------------------------

            zero_delay_records = int(
                (df[column] == 0).sum()
            )

            positive_delay_records = int(
                (df[column] > 0).sum()
            )

            # -------------------------------------------------
            # Evidence
            # -------------------------------------------------

            evidence = {

                "column": column,

                "total_records": total_records,

                "anomaly_count": anomaly_count,

                "anomaly_rate": round(
                    anomaly_rate,
                    4
                ),

                "q1": round(
                    float(q1),
                    4
                ),

                "q3": round(
                    float(q3),
                    4
                ),

                "iqr": round(
                    float(iqr),
                    4
                ),

                "lower_bound": round(
                    float(lower_bound),
                    4
                ),

                "upper_bound": round(
                    float(upper_bound),
                    4
                ),

                "analysis_population": len(
                    analysis_df
                ),

                "zero_delay_records": (
                    zero_delay_records
                ),

                "positive_delay_records": (
                    positive_delay_records
                ),

                "top_anomalies": top_anomalies
            }

            # -------------------------------------------------
            # Final response
            # -------------------------------------------------

            return {

                "status": "success",

                "agent": (
                    "Anomaly Detection Agent"
                ),

                "findings": [
                    evidence
                ],

                "evidence": [
                    evidence
                ],

                "source": {

                    "dataset": (
                        "order_features"
                    ),

                    "method": (
                        "IQR_positive_delays"
                        if column == "delay_days"
                        else "IQR"
                    )
                }
            }

        except Exception as exc:

            return {
                "status": "error",
                "message": str(exc)
            }