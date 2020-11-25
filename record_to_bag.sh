source ~/catkin_ws/devel/setup.bash

# Start recording specific nodes from the lidar and the imu
roscore&
sleep 5

# Start the connection to the imu (and start roscore in the background)
roslaunch ros_mscl microstrain.launch &

# Start the connection to the lidar
rosrun velodyne_driver velodyne_node _model:=32C _npackets:=1 _rpm:=300&

# Start conversion from lidar to pointcloud
rosrun nodelet nodelet standalone velodyne_pointcloud/TransformNodelet _model:=32C _calibration:="$(rospack find velodyne_pointcloud)"/params/VeloView-VLP-32C.yaml&
sleep 5

rosbag record /gx5/imu/data /velodyne_points&
# rosbag record -a &
sleep 5

# Wait for user input and then attempt to kill gracefully
sleep 5
exit_code="n"
while [[ "$exit_code" != "y" ]]; do
  read -r -s -p "Stop recording (y/n): " exit_code
  printf '\n'
done
echo "$exit_code"
echo "Exiting gracefully:"
rosnode kill -a &
sleep 5
kill -9
