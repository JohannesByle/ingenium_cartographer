#!/bin/bash
# Get bag file from args
file=$(realpath "$1")
if [ ! -f "$file" ]; then
  echo "$file is not a file."
  return 1
fi

# Run ros setup
source /opt/ros/noetic/setup.bash
# Run cartographer setup
echo "$HOME"/catkin_ws/install_isolated/setup.bash
source "$HOME"/catkin_ws/install_isolated/setup.bash

roscore &
sleep 2

roslaunch ~/ingenium_cartographer/cartographer_config/display.launch &
sleep 2

rosbag play "$file"
sleep 2
