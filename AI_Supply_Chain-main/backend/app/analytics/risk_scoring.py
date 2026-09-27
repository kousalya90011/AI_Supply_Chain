from __future__ import annotations

import numpy as np


def normalize(
    value: float,
    minimum: float,
    maximum: float
) -> float:

    if maximum <= minimum:
        return 0.0

    score = (
        (value - minimum)
        / (maximum - minimum)
    )

    return float(np.clip(score, 0, 1))


def calculate_risk_level(
    risk_score: float
) -> str:

    score = float(risk_score)

    if score >= 80:
        return "CRITICAL"

    if score >= 60:
        return "HIGH"

    if score >= 30:
        return "MEDIUM"

    return "LOW"


def supplier_risk_score(
    late_rate: float,
    volume_exposure: float,
    lead_time_anomaly: float = 0.0
) -> float:

    score = (
        0.50 * np.clip(late_rate * 100, 0, 100)
        + 0.20 * np.clip(volume_exposure, 0, 100)
        + 0.30 * np.clip(lead_time_anomaly, 0, 100)
    )

    return round(
        float(np.clip(score, 0, 100)),
        2
    )


def delivery_risk_score(
    late_rate: float,
    average_delay: float,
    anomaly_score: float = 0.0
) -> float:

    delay_component = np.clip(
        late_rate * 100,
        0,
        100
    )

    average_delay_component = np.clip(
        average_delay * 10,
        0,
        100
    )

    anomaly_component = np.clip(
        anomaly_score,
        0,
        100
    )

    score = (
        0.50 * delay_component
        + 0.30 * average_delay_component
        + 0.20 * anomaly_component
    )

    return round(
        float(np.clip(score, 0, 100)),
        2
    )


def inventory_risk_score(
    stockout_rate: float,
    demand_pressure: float,
    coverage_score: float
) -> float:

    score = (
        0.50 * np.clip(
            stockout_rate * 100,
            0,
            100
        )
        + 0.30 * np.clip(
            demand_pressure * 100,
            0,
            100
        )
        + 0.20 * np.clip(
            coverage_score,
            0,
            100
        )
    )

    return round(
        float(np.clip(score, 0, 100)),
        2
    )


class RiskScoringEngine:

    def __init__(self):

        self.risk_score = 0.0

        # Keep this as a string for existing code
        # that reads self.scorer.risk_level.
        self.risk_level = "LOW"

    def _set_result(
        self,
        score: float
    ) -> float:

        self.risk_score = round(
            float(np.clip(score, 0, 100)),
            2
        )

        self.risk_level = calculate_risk_level(
            self.risk_score
        )

        return self.risk_score

    def calculate_supplier_score(
        self,
        late_rate: float,
        volume_exposure: float,
        lead_time_anomaly: float = 0.0,
        lead_time_risk: float | None = None
    ) -> float:

        if lead_time_risk is not None:
            lead_time_anomaly = lead_time_risk

        score = supplier_risk_score(
            late_rate=late_rate,
            volume_exposure=volume_exposure,
            lead_time_anomaly=lead_time_anomaly
        )

        return self._set_result(score)

    def calculate_delivery_score(
        self,
        late_rate: float,
        average_delay: float,
        anomaly_score: float = 0.0
    ) -> float:

        score = delivery_risk_score(
            late_rate=late_rate,
            average_delay=average_delay,
            anomaly_score=anomaly_score
        )

        return self._set_result(score)

    def calculate_inventory_score(
        self,
        stockout_rate: float,
        demand_pressure: float,
        coverage_score: float
    ) -> float:

        score = inventory_risk_score(
            stockout_rate=stockout_rate,
            demand_pressure=demand_pressure,
            coverage_score=coverage_score
        )

        return self._set_result(score)

    def calculate_route_score(
        self,
        late_rate: float,
        average_delay: float = 0.0,
        anomaly_score: float = 0.0
    ) -> float:

        score = delivery_risk_score(
            late_rate=late_rate,
            average_delay=average_delay,
            anomaly_score=anomaly_score
        )

        return self._set_result(score)

    def get_risk_level(
        self,
        risk_score: float | None = None
    ) -> str:

        if risk_score is None:
            return self.risk_level

        return calculate_risk_level(risk_score)