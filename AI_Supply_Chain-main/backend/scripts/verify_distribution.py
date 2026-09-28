import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from app.services.analytics_service import AnalyticsService

svc = AnalyticsService()
df = svc.supplier_risk()

print("=" * 60)
print("SUPPLIER RISK POPULATION & DISTRIBUTION VALIDATION")
print("=" * 60)
print(f"Total suppliers evaluated: {len(df)}")

vc = df["risk_level"].value_counts()
print("\nRisk Level Breakdown:")
for lvl in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
    cnt = vc.get(lvl, 0)
    pct = (cnt / len(df)) * 100
    print(f"  {lvl:10s}: {cnt:3d} suppliers ({pct:5.1f}%)")

print("\nRisk Score Statistics:")
print(f"  Minimum risk score: {df['risk_score'].min():.2f}")
print(f"  Maximum risk score: {df['risk_score'].max():.2f}")
print(f"  Mean risk score:    {df['risk_score'].mean():.2f}")

print("\nBoundary Cases Check:")
b_low_med = df[(df["risk_score"] >= 28.5) & (df["risk_score"] <= 31.5)][["supplier_id", "risk_score", "risk_level", "late_rate", "volume_exposure"]]
print(f"\nBoundary ~29-31 (LOW/MEDIUM transition): {len(b_low_med)} found")
print(b_low_med.to_string(index=False))

b_med_high = df[(df["risk_score"] >= 58.5) & (df["risk_score"] <= 61.5)][["supplier_id", "risk_score", "risk_level", "late_rate", "volume_exposure"]]
print(f"\nBoundary ~59-61 (MEDIUM/HIGH transition): {len(b_med_high)} found")
print(b_med_high.to_string(index=False))

b_high_crit = df[(df["risk_score"] >= 78.5) & (df["risk_score"] <= 81.5)][["supplier_id", "risk_score", "risk_level", "late_rate", "volume_exposure"]]
print(f"\nBoundary ~79-81 (HIGH/CRITICAL transition): {len(b_high_crit)} found")
print(b_high_crit.to_string(index=False))

print("\nRepresentative Sample From Each Category:")
for lvl in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
    sample = df[df["risk_level"] == lvl].head(2)
    print(f"\n[{lvl}]")
    print(sample[["supplier_id", "risk_score", "risk_level", "late_rate", "volume_exposure", "risk_reason"]].to_string(index=False))
