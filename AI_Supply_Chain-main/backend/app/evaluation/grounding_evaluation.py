from __future__ import annotations

import re
from typing import Any


class EvidenceGroundingEvaluator:

    NUMERIC_FIELDS = [
        "risk_score",
        "stockout_rate",
        "demand_pressure",
        "days_of_cover",
        "average_inventory",
        "average_daily_demand",
        "late_rate",
        "average_delay",
        "anomaly_count",
        "total_records",
        "trend_per_day",
    ]

    CATEGORICAL_FIELDS = [
        "risk_level",
    ]

    IMPORTANT_FIELDS = (
        NUMERIC_FIELDS
        + CATEGORICAL_FIELDS
    )

    # ---------------------------------------------------------
    # TEXT NORMALIZATION
    # ---------------------------------------------------------

    def _normalize_text(self, value: Any) -> str:

        if value is None:
            return ""

        text = str(value).strip().lower()

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text

    # ---------------------------------------------------------
    # NUMBER VARIANTS
    # ---------------------------------------------------------

    def _format_number_variants(
        self,
        value: Any
    ) -> list[str]:

        try:
            number = float(value)
        except (TypeError, ValueError):
            return []

        variants = set()

        # Original rounded values
        variants.add(
            str(round(number, 2))
        )

        variants.add(
            str(round(number, 4))
        )

        # Integer representation
        if number.is_integer():
            variants.add(
                str(int(number))
            )

        # Percentage representation
        if 0 <= number <= 1:

            percentage = number * 100

            variants.add(
                str(round(percentage, 2))
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

        return list(variants)

    # ---------------------------------------------------------
    # NUMERIC MATCHING
    # ---------------------------------------------------------

    def _numeric_match(
        self,
        value: Any,
        answer: str
    ) -> bool:

        answer_lower = self._normalize_text(answer)

        variants = self._format_number_variants(
            value
        )

        for variant in variants:

            # Escape the value so decimal points
            # are treated literally.
            pattern = re.escape(
                variant.lower()
            )

            # Avoid matching 2.5 inside 12.5
            pattern = (
                rf"(?<!\d){pattern}"
                rf"(?!\d)"
            )

            if re.search(
                pattern,
                answer_lower
            ):
                return True

        return False

    # ---------------------------------------------------------
    # CATEGORICAL MATCHING
    # ---------------------------------------------------------

    def _categorical_match(
        self,
        value: Any,
        answer: str
    ) -> bool:

        if value is None:
            return False

        expected = self._normalize_text(
            value
        )

        answer_lower = self._normalize_text(
            answer
        )

        if not expected:
            return False

        # Direct word/phrase match
        pattern = (
            rf"\b{re.escape(expected)}\b"
        )

        if re.search(
            pattern,
            answer_lower
        ):
            return True

        return False

    # ---------------------------------------------------------
    # FIELD MATCHING
    # ---------------------------------------------------------

    def _field_matches(
        self,
        field: str,
        value: Any,
        answer: str
    ) -> bool:

        if field in self.CATEGORICAL_FIELDS:
            return self._categorical_match(
                value=value,
                answer=answer
            )

        return self._numeric_match(
            value=value,
            answer=answer
        )

    # ---------------------------------------------------------
    # EVALUATION
    # ---------------------------------------------------------

    def evaluate(
        self,
        answer: str,
        evidence: list[dict[str, Any]]
    ) -> dict[str, Any]:

        if not answer or not answer.strip() or not evidence:

            return {
                "grounded": False,
                "coverage": 0.0,
                "checked_fields": [],
                "matched_fields": [],
                "missing_fields": []
            }

        checked_fields = []
        matched_fields = []
        missing_fields = []

        # -----------------------------------------------------
        # Evaluate every evidence item
        # -----------------------------------------------------

        for item in evidence:

            if not isinstance(item, dict):
                continue

            for field in self.IMPORTANT_FIELDS:

                if field not in item:
                    continue

                value = item[field]

                if value is None:
                    continue

                # Skip empty strings
                if isinstance(value, str):
                    if not value.strip():
                        continue

                checked_fields.append(field)

                matched = self._field_matches(
                    field=field,
                    value=value,
                    answer=answer
                )

                if matched:
                    matched_fields.append(field)
                else:
                    missing_fields.append(field)

        # -----------------------------------------------------
        # Remove duplicates
        # -----------------------------------------------------

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
            for field in dict.fromkeys(
                missing_fields
            )
            if field not in matched_fields
        ]

        # -----------------------------------------------------
        # No evaluatable evidence
        # -----------------------------------------------------

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
                "missing_fields": []
            }

        # -----------------------------------------------------
        # Coverage
        # -----------------------------------------------------

        coverage = (
            len(matched_fields)
            / len(checked_fields)
        )

        # -----------------------------------------------------
        # Grounding decision
        #
        # 50%+ evidence coverage is considered grounded.
        # -----------------------------------------------------

        grounded = coverage >= 0.50

        return {
            "grounded": grounded,
            "coverage": round(
                coverage,
                4
            ),
            "checked_fields": checked_fields,
            "matched_fields": matched_fields,
            "missing_fields": missing_fields
        }
    