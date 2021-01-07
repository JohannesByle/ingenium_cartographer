#!/bin/bash
# Run cartographer setup
# source /opt/ros/noetic/setup.bash
# Start the connection to the imu (and start roscore in the background)
cd /home/ubuntu/ingenium_cartographer
roslaunch ros_mscl microstrain.launch&
sleep 2

# Start the connection to the lidar
rosrun velodyne_driver velodyne_node _model:=32C _npackets:=1 _rpm:=300&
sleep 2

# Start recording specific nodes from the lidar and the imu
rosbag record /gx5/imu/data /velodyne_packets&
sleep 2

