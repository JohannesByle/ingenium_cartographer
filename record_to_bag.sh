#!/bin/bash
# Run cartographer setup
# source /opt/ros/noetic/setup.bash
# Start the connection to the imu (and start roscore in the background)
source ~/catkin_ws/devel_isolated/setup.bash
source ~/catkin_ws/devel/setup.bash
roslaunch ros_mscl microstrain.launch &
sleep 2

# Start the connection to the lidar
rosrun velodyne_driver velodyne_node _model:=32C _npackets:=1 _rpm:=300 &
sleep 2

# Start recording specific nodes from the lidar and the imu
rosbag record /gx5/imu/data /velodyne_packets &
sleep 2

echo "Currently recording, press any key to exit"
read -r
rosnode kill -a
