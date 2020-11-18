source devel/setup.bash

# Start the connection to the imu (and start roscore in the background)
roslaunch ros_mscl microstrain.launch &
sleep 5

# Start the connection to the lidar
rosrun velodyne_driver velodyne_node _model:=32C &
sleep 5

# Start conversion from lidar to pointcloud
rosrun nodelet nodelet standalone velodyne_pointcloud/TransformNodelet _model:=32C&
sleep 10

# Start recording specific nodes from the lidar and the imu
rosbag record /gx5/imu/data /velodyne_points &
sleep 5

# Wait for user input and then attempt to kill gracefully
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
