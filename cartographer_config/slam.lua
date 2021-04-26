-- Copyright 2016 The Cartographer Authors
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--      http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

include "map_builder.lua"
include "trajectory_builder.lua"

options = {
    map_builder = MAP_BUILDER,
    trajectory_builder = TRAJECTORY_BUILDER,
    map_frame = "map",
    tracking_frame = "base_link",
    published_frame = "base_link",
    odom_frame = "odom",
    provide_odom_frame = true,
    publish_frame_projected_to_2d = false,
    use_pose_extrapolator = true,
    use_odometry = false,
    use_nav_sat = false,
    use_landmarks = false,
    num_laser_scans = 0,
    num_multi_echo_laser_scans = 0,
    num_subdivisions_per_laser_scan = 1,
    num_point_clouds = 1,
    lookup_transform_timeout_sec = 0.2,
    submap_publish_period_sec = 0.3,
    pose_publish_period_sec = 5e-3,
    trajectory_publish_period_sec = 30e-3,
    rangefinder_sampling_ratio = 1.,
    odometry_sampling_ratio = 1.,
    fixed_frame_pose_sampling_ratio = 1.,
    imu_sampling_ratio = 1.,
    landmarks_sampling_ratio = 1.,
}

-- This should not be changed unless the frequency of the lidar is changed, this is how many many scans per rotation of the lidar
TRAJECTORY_BUILDER_3D.num_accumulated_range_data = 160
-- The following setting changes how big the submaps are, i.e. the larger the number the larger the submap and the fewer submaps in total
-- TRAJECTORY_BUILDER_3D.submaps.num_range_data = 1e7	

-- This looks promising, and worked well for indoor slams, but worked really poorly in outdoor slams.
-- But the poor result in outdoor slams may be a function of poor choices in other settings
-- TRAJECTORY_BUILDER_3D.use_online_correlative_scan_matching = true


-- These settings affect the resolution of the map stored by Cartographer
-- TRAJECTORY_BUILDER_3D.submaps.high_resolution = 0.05
-- TRAJECTORY_BUILDER_3D.submaps.low_resolution = 0.15
-- As of 4/22 these seems best for these settings
-- Higer resolution going from 0.15 ro 0.05 helped the scan
--0.015 for high did not change it much when set to 0.05 before

-- These settings affect the resolution as well
-- I'm not sure about the voxel filter size and max_length, but min_num_points on its own seems to work really well
-- TRAJECTORY_BUILDER_3D.voxel_filter_size = 0.1
-- TRAJECTORY_BUILDER_3D.high_resolution_adaptive_voxel_filter.max_length = 0.1
-- This makes each frame use at least 10 mil points in the slam
-- TRAJECTORY_BUILDER_3D.high_resolution_adaptive_voxel_filter.min_num_points = 1e7

MAP_BUILDER.use_trajectory_builder_3d = true
MAP_BUILDER.num_background_threads = 7

-- The following settings affect the global slam
POSE_GRAPH.optimization_problem.huber_scale = 5e2
-- Set the optimize_every_n_nodex to 0 to turn of global slam
-- One theory is that turning off global slam might improve the slam since we are never move away from our inital measuring point
-- i.e when measuring a dig site the majority of the dig site is constantly visible, and we don't move away from it.
-- Turning off the global slam would then be joined with making the submaps huge, i.e just one big submap rather than many small ones.
POSE_GRAPH.optimize_every_n_nodes = 320
POSE_GRAPH.constraint_builder.sampling_ratio = 0.03
POSE_GRAPH.optimization_problem.ceres_solver_options.max_num_iterations = 10
POSE_GRAPH.constraint_builder.min_score = 0.62
POSE_GRAPH.constraint_builder.global_localization_min_score = 0.66
POSE_GRAPH.optimization_problem.log_solver_summary = true

--voxel size should stay small

return options

