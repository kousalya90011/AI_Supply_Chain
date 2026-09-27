from __future__ import annotations

import re
from typing import Any


class EvidenceGroundingEvaluator:

    NUMERIC_FIELDS = [
        "risk_score",
        "stockout_rate",
        "demand_pressure",
        "days_of_cover",
        "days_cover",
        "average_inventory",
        "avg_inventory",
        "average_daily_demand",
        "avg_daily_demand",
        "late_rate",
        "average_delay",
        "delay_days",
        "anomaly_count",
        "total_records",
        "trend_per_day",
        "value",
        "confidence",
    ]

    CATEGORICAL_FIELDS = [
        "risk_level",
        "metric",
        "entity_id",
        "entity_type",
        "source_type",
        "retrieval_method",
    ]

    IMPORTANT_FIELDS = (
        NUMERIC_FIELDS
        + CATEGORICAL_FIELDS
    )

    def _normalize_text(
        self,
        value: Any,
    ) -> str:

        if value is None:
            return ""

        text = str(
            value
        ).strip().lower()

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text

    def _format_number_variants(
        self,
        value: Any,
    ) -> list[str]:

        try:
            number = float(value)

        except (
            TypeError,
            ValueError,
        ):
            return []

        variants: set[str] = set()

        variants.add(
            str(
                round(
                    number,
                    2,
                )
            )
        )

        variants.add(
            str(
                round(
                    number,
                    4,
                )
            )
        )

        if number.is_integer():

            variants.add(
                str(
                    int(number)
                )
            )

        # Decimal -> percentage
        if 0 <= number <= 1:

            percentage = (
                number * 100
            )

            variants.add(
                str(
                    round(
                        percentage,
                        2,
                    )
                )
            )

            variants.add(
                f"{round(percentage, 2)}%"
            )

            variants.add(
                f"{round(percentage, 1)}%"
            )

            if percentage.is_integer():

                variants.add(
                    f"{int(percentage)}%"
                )

        return list(
            variants
        )

    def _numeric_match(
        self,
        value: Any,
        answer: str,
    ) -> bool:

        answer_lower = (
            self._normalize_text(
                answer
            )
        )

        variants = (
            self._format_number_variants(
                value
            )
        )

        for variant in variants:

            pattern = re.escape(
                variant.lower()
            )

            pattern = (
                rf"(?<!\d)"
                rf"{pattern}"
                rf"(?!\d)"
            )

            if re.search(
                pattern,
                answer_lower,
            ):
                return True

        return False

    def _categorical_match(
        self,
        value: Any,
        answer: str,
    ) -> bool:

        if value is None:
            return False

        expected = (
            self._normalize_text(
                value
            )
        )

        answer_lower = (
            self._normalize_text(
                answer
            )
        )

        if not expected:
            return False

        # Supplier/product IDs such as
        # S0001 / S001 and P00003
        # are better checked as substrings
        # than word-boundary expressions.

        if (
            expected.startswith("s")
            or expected.startswith("p")
        ):

            return expected in answer_lower

        pattern = (
            rf"\b"
            rf"{re.escape(expected)}"
            rf"\b"
        )

        return bool(
            re.search(
                pattern,
                answer_lower,
            )
        )

    def _field_matches(
        self,
        field: str,
        value: Any,
        answer: str,
    ) -> bool:

        if field in self.CATEGORICAL_FIELDS:

            return self._categorical_match(
                value=value,
                answer=answer,
            )

        return self._numeric_match(
            value=value,
            answer=answer,
        )

    def _extract_evidence_value(
        self,
        item: dict[str, Any],
    ) -> list[tuple[str, Any]]:

        candidates: list[
            tuple[str, Any]
        ] = []

        # ----------------------------------------------------
        # Direct evidence fields
        # ----------------------------------------------------

        for field in self.IMPORTANT_FIELDS:

            if field not in item:
                continue

            value = item.get(
                field
            )

            if value is None:
                continue

            if (
                isinstance(value, str)
                and not value.strip()
            ):
                continue

            candidates.append(
                (
                    field,
                    value,
                )
            )

        # ----------------------------------------------------
        # Nested data/value
        # ----------------------------------------------------

        nested = (
            item.get("data")
            or item.get("value")
        )

        if isinstance(
            nested,
            dict,
        ):

            for field in self.IMPORTANT_FIELDS:

                if field not in nested:
                    continue

                value = nested.get(
                    field
                )

                if value is None:
                    continue

                if (
                    isinstance(value, str)
                    and not value.strip()
                ):
                    continue

                candidates.append(
                    (
                        field,
                        value,
                    )
                )

        return candidates

    def evaluate(
        self,
        answer: str,
        evidence: list[
            dict[str, Any]
        ],
    ) -> dict[str, Any]:

        if (
            not answer
            or not answer.strip()
            or not evidence
        ):

            return {
                "grounded": False,
                "coverage": 0.0,
                "checked_fields": [],
                "matched_fields": [],
                "missing_fields": [],
            }

        checked_fields: list[
            str
        ] = []

        matched_fields: list[
            str
        ] = []

        missing_fields: list[
            str
        ] = []

        # ----------------------------------------------------
        # Evaluate evidence
        # ----------------------------------------------------

        for item in evidence:

            if not isinstance(
                item,
                dict,
            ):
                continue

            candidates = (
                self._extract_evidence_value(
                    item
                )
            )

            for field, value in candidates:

                checked_fields.append(
                    field
                )

                matched = (
                    self._field_matches(
                        field=field,
                        value=value,
                        answer=answer,
                    )
                )

                if matched:

                    matched_fields.append(
                        field
                    )

                else:

                    missing_fields.append(
                        field
                    )

        # ----------------------------------------------------
        # Remove duplicates
        # ----------------------------------------------------

        checked_fields = list(
            dict.fromkeys(
                checked_fields
            )
        )

        matched_fields = list(
            dict.fromkeys(
                matched_fields
            )
        )

        missing_fields = [
            field
            for field
            in dict.fromkeys(
                missing_fields
            )
            if field
            not in matched_fields
        ]

        # ----------------------------------------------------
        # No measurable fields
        # ----------------------------------------------------

        if not checked_fields:

            return {
                "grounded": bool(
                    answer.strip()
                ),
                "coverage": (
                    1.0
                    if answer.strip()
                    else 0.0
                ),
                "checked_fields": [],
                "matched_fields": [],
                "missing_fields": [],
            }

        # ----------------------------------------------------
        # Coverage
        # ----------------------------------------------------

        coverage = (
            len(matched_fields)
            / len(checked_fields)
        )

        grounded = (
            coverage >= 0.50
        )

        return {
            "grounded": grounded,
            "coverage": round(
                coverage,
                4,
            ),
            "checked_fields": (
                checked_fields
            ),
            "matched_fields": (
                matched_fields
            ),
            "missing_fields": (
                missing_fields
            ),
        }