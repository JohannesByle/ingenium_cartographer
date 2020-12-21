cwd=$(pwd)
cd ~/catkin_ws/src || exit

git clone https://github.com/ros-drivers/velodyne
cd velodyne || exit
# This stage of the repo was tested to be working, but may not work with future ROS releases
git reset --hard f235ac6
git pull
cd .. || exit

git clone https://github.com/LORD-MicroStrain/ROS-MSCL
#cd ROS-MSCL || exit
## This stage of the repo was tested to be working, but may not work with future ROS releases
#git reset --hard ecf15a7
#git pull
#cd .. || exit
#mv ROS-MSCL/ros_mscl .
#sudo rm -r ROS-MSCL

cd ~/catkin_ws/ || exit
catkin_make_isolated --install --use-ninja
cd ~/catkin_ws/src || exit

sudo rm -r velodyne
git clone https://github.com/JohannesByle/velodyne

cd ~/catkin_ws/ || exit
catkin_make_isolated --install --use-ninja
cd "$cwd" || exit
