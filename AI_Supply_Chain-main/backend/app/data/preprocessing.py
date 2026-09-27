import pandas as pd


class DataPreprocessor:

    def clean_orders(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        df = df.copy()

        # Remove duplicate order IDs
        if "order_id" in df.columns:
            df = df.drop_duplicates(
                subset=["order_id"]
            )

        # Numeric conversion
        if "units" in df.columns:
            df["units"] = pd.to_numeric(
                df["units"],
                errors="coerce"
            )

        # Invalid units
        if "units" in df.columns:
            df.loc[
                df["units"] < 0,
                "units"
            ] = None

        # Late-order normalization
        if "late_order" in df.columns:

            df["late_order"] = (
                df["late_order"]
                .astype(str)
                .str.lower()
                .map({
                    "yes": 1,
                    "true": 1,
                    "1": 1,
                    "no": 0,
                    "false": 0,
                    "0": 0
                })
            )

        return df

    def clean_numeric_columns(
        self,
        df: pd.DataFrame,
        columns: list[str]
    ) -> pd.DataFrame:

        df = df.copy()

        for column in columns:

            if column in df.columns:

                df[column] = pd.to_numeric(
                    df[column],
                    errors="coerce"
                )

        return df

    def clean_all(
        self,
        datasets: dict[str, pd.DataFrame]
    ) -> dict[str, pd.DataFrame]:

        cleaned = {}

        for name, df in datasets.items():

            current = df.copy()

            if name in [
                "orders",
                "orders_extended"
            ]:
                current = self.clean_orders(current)

            cleaned[name] = current

        return cleaned
    