"""
Find activities that have cadence or power (watts) data in their time series.
Prints Strava upstream_id for each match — use these IDs to test the API importer.

Run inside Docker:
    docker-compose exec geo-activity-playground python scripts/find_cadence_power_activities.py
"""
import os
import pathlib

import pandas as pd
import sqlalchemy

os.chdir("/data")

engine = sqlalchemy.create_engine("sqlite:///database.sqlite")

with engine.connect() as conn:
    rows = conn.execute(
        sqlalchemy.text(
            "SELECT upstream_id, time_series_uuid, name FROM activities "
            "WHERE upstream_id IS NOT NULL AND time_series_uuid IS NOT NULL"
        )
    ).fetchall()

print(f"Checking {len(rows)} Strava activities for cadence/power data...\n")

results = []
for upstream_id, uuid, name in rows:
    path = pathlib.Path("Time Series") / f"{uuid}.parquet"
    if not path.exists():
        continue
    df = pd.read_parquet(path, columns=None)
    has_cadence = "cadence" in df.columns and df["cadence"].notna().any()
    has_watts = "watts" in df.columns and df["watts"].notna().any()
    if has_cadence or has_watts:
        results.append((upstream_id, name, has_cadence, has_watts))

print(f"{'upstream_id':<15} {'cadence':>8} {'watts':>8}  name")
print("-" * 70)
for upstream_id, name, has_cadence, has_watts in results:
    print(f"{upstream_id:<15} {'yes' if has_cadence else 'no':>8} {'yes' if has_watts else 'no':>8}  {name}")

print(f"\nTotal: {len(results)} activities with cadence or power data.")
