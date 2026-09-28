#!/usr/bin/env python3
"""
Rebalance Synthetic Dataset for Supplier Risk Intelligence.

This script updates operational variables across suppliers in orders_extended.csv,
orders.csv, and suppliers.csv so that risk scores emerge naturally from the
underlying operational metrics:
- late_order rate
- average delay and delay variability
- lead-time days and lead-time variability
- disruption frequency
- volume exposure

Target Supplier Population: 150 suppliers
Target Distribution:
- LOW:      40-50% (~68 suppliers, 45.3%)
- MEDIUM:   25-35% (~46 suppliers, 30.7%)
- HIGH:     10-20% (~24 suppliers, 16.0%)
- CRITICAL:  5-10% (~12 suppliers,  8.0%)

Threshold Boundary Cases:
- 29-31: boundary between LOW and MEDIUM
- 59-61: boundary between MEDIUM and HIGH
- 79-81: boundary between HIGH and CRITICAL
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Paths
base_dir = Path(__file__).resolve().parent.parent.parent
data_raw = base_dir / "data" / "raw"

orders_ext_path = data_raw / "orders_extended.csv"
orders_path = data_raw / "orders.csv"
suppliers_path = data_raw / "suppliers.csv"

print(f"Loading data from {data_raw}...")
orders_ext = pd.read_csv(orders_ext_path)
suppliers_df = pd.read_csv(suppliers_path)

all_suppliers = sorted(suppliers_df["supplier_id"].unique())
n_suppliers = len(all_suppliers)
print(f"Total suppliers found: {n_suppliers}")

# Target counts
# CRITICAL: 18 (12.0%, target 10-15%)
# HIGH: 34 (22.7%, target 20-25%)
# MEDIUM: 48 (32.0%, target 30-35%)
# LOW: 50 (33.3%, target 30-40%)
# Sum = 150

np.random.seed(42)

# Specific boundary assignments (deterministic)
critical_suppliers = all_suppliers[132:150]    # 18 suppliers (S0133 - S0150)
high_suppliers = all_suppliers[98:132]        # 34 suppliers (S0099 - S0132)
medium_suppliers = all_suppliers[50:98]       # 48 suppliers (S0051 - S0098)
low_suppliers = all_suppliers[0:50]           # 50 suppliers (S0001 - S0050)

supplier_profiles = {}

# 1. CRITICAL SUPPLIERS (18 suppliers, target: 80 - 96)
# Boundary around 80-81: S0133, S0134
for i, sid in enumerate(critical_suppliers):
    step = i / 17.0  # 0 to 1
    late_rate = 0.875 + step * 0.065     # 0.875 - 0.94
    vol_factor = 1.42 + step * 0.43     # 1.42 - 1.85
    avg_delay = 6.0 + step * 2.3        # 6.0 - 8.3
    lead_std = 7.8 + step * 3.2         # 7.8 - 11.0
    disr_rate = 0.46 + step * 0.14      # 0.46 - 0.60
    reliability = 0.68 - step * 0.08    # 0.68 - 0.60
    supplier_profiles[sid] = {
        "tier": "CRITICAL",
        "late_rate": late_rate,
        "vol_factor": vol_factor,
        "avg_delay": avg_delay,
        "lead_std": lead_std,
        "disr_rate": disr_rate,
        "reliability": round(reliability, 3),
        "risk_slope": 0.82 + step * 0.18,
    }

# 2. HIGH SUPPLIERS (34 suppliers, target: 60 - 79.9)
# Boundary around 78-79.5 (High edge near Critical): S0131, S0132
# Boundary around 60-61.5 (High edge near Medium): S0099, S0100
for i, sid in enumerate(high_suppliers):
    step = i / 33.0
    late_rate = 0.745 + step * 0.115    # 0.745 - 0.86
    vol_factor = 1.15 + step * 0.25     # 1.15 - 1.40
    avg_delay = 4.4 + step * 1.4        # 4.4 - 5.8
    lead_std = 6.2 + step * 1.5         # 6.2 - 7.7
    disr_rate = 0.33 + step * 0.11      # 0.33 - 0.44
    reliability = 0.78 - step * 0.06    # 0.78 - 0.72
    supplier_profiles[sid] = {
        "tier": "HIGH",
        "late_rate": late_rate,
        "vol_factor": vol_factor,
        "avg_delay": avg_delay,
        "lead_std": lead_std,
        "disr_rate": disr_rate,
        "reliability": round(reliability, 3),
        "risk_slope": 0.60 + step * 0.21,
    }

# 3. MEDIUM SUPPLIERS (48 suppliers, target: 30 - 59.9)
# Boundary around 58-59.5 (Medium edge near High): S0097, S0098
# Boundary around 30-31.5 (Medium edge near Low): S0051, S0052
for i, sid in enumerate(medium_suppliers):
    step = i / 47.0
    late_rate = 0.43 + step * 0.29      # 0.43 - 0.72
    vol_factor = 0.65 + step * 0.45     # 0.65 - 1.10
    avg_delay = 1.9 + step * 2.3        # 1.9 - 4.2
    lead_std = 3.2 + step * 2.8         # 3.2 - 6.0
    disr_rate = 0.12 + step * 0.19      # 0.12 - 0.31
    reliability = 0.86 - step * 0.06    # 0.86 - 0.80
    supplier_profiles[sid] = {
        "tier": "MEDIUM",
        "late_rate": late_rate,
        "vol_factor": vol_factor,
        "avg_delay": avg_delay,
        "lead_std": lead_std,
        "disr_rate": disr_rate,
        "reliability": round(reliability, 3),
        "risk_slope": 0.30 + step * 0.29,
    }

# 4. LOW SUPPLIERS (50 suppliers, target: 0 - 29.9)
# Boundary around 28-29.5 (Low edge near Medium): S0049, S0050
for i, sid in enumerate(low_suppliers):
    step = i / 49.0
    late_rate = 0.02 + step * 0.37      # 0.02 - 0.39
    vol_factor = 0.20 + step * 0.42     # 0.20 - 0.62
    avg_delay = 0.1 + step * 1.5        # 0.1 - 1.6
    lead_std = 0.8 + step * 2.2         # 0.8 - 3.0
    disr_rate = 0.01 + step * 0.09      # 0.01 - 0.10
    reliability = 0.98 - step * 0.09    # 0.98 - 0.89
    supplier_profiles[sid] = {
        "tier": "LOW",
        "late_rate": late_rate,
        "vol_factor": vol_factor,
        "avg_delay": avg_delay,
        "lead_std": lead_std,
        "disr_rate": disr_rate,
        "reliability": round(reliability, 3),
        "risk_slope": step * 0.29,
    }

print("Profiles initialized for all 150 suppliers.")

# Apply updates to orders_extended
print("Updating orders_extended data...")
new_orders_ext = orders_ext.copy()

# Base units multiplier mapping
base_units = new_orders_ext["units"].copy()

# Process each supplier
order_indices_by_sup = new_orders_ext.groupby("supplier_id").groups

for sid, profile in supplier_profiles.items():
    if sid not in order_indices_by_sup:
        continue
    idx = order_indices_by_sup[sid]
    n_orders = len(idx)
    
    # 1. Units scaling by vol_factor
    new_orders_ext.loc[idx, "units"] = np.maximum(
        1,
        np.round(base_units.loc[idx] * profile["vol_factor"])
    ).astype(int)
    
    # 2. Late orders
    target_late_count = int(round(n_orders * profile["late_rate"]))
    is_late = np.zeros(n_orders, dtype=int)
    if target_late_count > 0:
        # Choose late indices randomly for this supplier
        late_sub_idx = np.random.choice(n_orders, size=min(target_late_count, n_orders), replace=False)
        is_late[late_sub_idx] = 1
    new_orders_ext.loc[idx, "late_order"] = is_late
    
    # 3. Delays
    # On time orders have delay_days = 0
    # Late orders have positive delay around avg_delay
    delays = np.zeros(n_orders, dtype=int)
    if is_late.sum() > 0:
        target_avg = profile["avg_delay"]
        # Generate positive delays with mean ~ target_avg
        late_delays = np.random.geometric(p=1.0 / max(1.5, target_avg), size=is_late.sum()) + 1
        # Scale to match desired average
        actual_mean = late_delays.mean()
        if actual_mean > 0:
            late_delays = np.maximum(1, np.round(late_delays * (target_avg / actual_mean))).astype(int)
        delays[is_late == 1] = late_delays
    new_orders_ext.loc[idx, "delay_days"] = delays
    
    # 4. Lead time days
    # Base lead time + delay_days + variation
    base_lt = 10
    variations = np.random.normal(loc=0, scale=max(0.5, profile["lead_std"]), size=n_orders)
    
    # Recent surge for high-risk / critical suppliers to create statistically meaningful anomalies
    order_dates = pd.to_datetime(new_orders_ext.loc[idx, "order_date"])
    max_date = order_dates.max()
    is_recent = (max_date - order_dates).dt.days <= 90
    recent_surge = np.zeros(n_orders)
    if profile.get("risk_slope", 0) >= 0.8:
        surge_mag = 4.5 + (profile["risk_slope"] - 0.8) * 12.0
        recent_surge = np.where(is_recent, surge_mag, 0.0)

    lead_times = np.maximum(1, np.round(base_lt + delays + variations + recent_surge)).astype(int)
    new_orders_ext.loc[idx, "lead_time_days"] = lead_times
    
    # 5. Disruption flag
    n_disr = int(round(n_orders * profile["disr_rate"]))
    disr_flags = np.zeros(n_orders, dtype=int)
    if n_disr > 0:
        disr_idx = np.random.choice(n_orders, size=min(n_disr, n_orders), replace=False)
        disr_flags[disr_idx] = 1
    new_orders_ext.loc[idx, "disruption_flag"] = disr_flags
    
    # 6. Promised date and delivery date recalculation
    # delivery_date = order_date + lead_time_days
    # promised_date = delivery_date - delay_days
    order_dates = pd.to_datetime(new_orders_ext.loc[idx, "order_date"])
    delivery_dates = order_dates + pd.to_timedelta(lead_times, unit="D")
    promised_dates = delivery_dates - pd.to_timedelta(delays, unit="D")
    new_orders_ext.loc[idx, "delivery_date"] = delivery_dates.dt.strftime("%Y-%m-%d")
    new_orders_ext.loc[idx, "promised_date"] = promised_dates.dt.strftime("%Y-%m-%d")

# Synchronize orders.csv
print("Synchronizing orders.csv...")
orders_df = pd.read_csv(orders_path)
order_sync = new_orders_ext.set_index("order_id")[["units", "late_order"]]
orders_df["units"] = orders_df["order_id"].map(order_sync["units"]).fillna(orders_df["units"]).astype(int)
orders_df["late_order"] = orders_df["order_id"].map(order_sync["late_order"]).fillna(orders_df["late_order"]).astype(int)

# Synchronize suppliers.csv reliability_baseline
print("Synchronizing suppliers.csv...")
rel_map = {sid: p["reliability"] for sid, p in supplier_profiles.items()}
suppliers_df["reliability_baseline"] = suppliers_df["supplier_id"].map(rel_map).fillna(suppliers_df["reliability_baseline"])

# Save updated files
print("Saving modified datasets...")
new_orders_ext.to_csv(orders_ext_path, index=False)
orders_df.to_csv(orders_path, index=False)
suppliers_df.to_csv(suppliers_path, index=False)
print("Datasets successfully updated and saved!")
