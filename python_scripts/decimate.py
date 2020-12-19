#!/usr/bin/env python3
from pyntcloud import PyntCloud
import pandas as pd
import sys


def decimate(file, max_points=5000000):
    max_points = int(max_points)
    cloud = PyntCloud.from_file(file)
    cloud.points = pd.DataFrame(cloud.points)
    if len(cloud.points.index) > max_points:
        cloud.points = cloud.points.sample(max_points)
    cloud.to_file(file[:-4] + "_small.ply")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        decimate(*sys.argv[1:])
