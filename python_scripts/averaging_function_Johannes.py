import pandas as pd
import numpy as np

full_path = r"""/home/lidar/ingenium_cartographer/24-2024-07-04/24-2024-07-04cut.txt"""
df = pd.DataFrame(pd.read_csv(full_path, sep=' ', header=None))
df = df[list(range(3))]
df.columns = ["x", "y", "z"]
print("DataFrame acquired.")

def get_avg(df, step, axes=None):
    cols = ["x", "y", "z"]
    axes = [cols.index(n) for n in axes] if axes else range(3)
    rounded_cols = [f"rounded_{n}" for n in cols]
    df[rounded_cols] = df[cols].div(step).round().mul(step)
    return df.groupby([rounded_cols[n] for n in axes]).mean()[cols]

# Average across all dimensions

# Flatten the z axis
averaged_df = get_avg(df, 0.03, ["x", "y"])
print("Function Called.")
np.savetxt('24-2024-07-04cutAVG.txt', averaged_df, delimiter=' ')
print("Program has finished running.")
