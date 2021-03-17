cwd=$(pwd)
catkin_dir=~/catkin_ws/

function catkin_make_custom() {
if [ -d "~/catkin_ws/src/cartographer" ] 
then
    catkin_make_isolated --install --use-ninja
else
    catkin_make
fi
}

function clone_at_commit() {
  url=$1
  commit=$2
  git clone "$url"
  cd "$(basename "$url")" || exit
  git reset --hard "$commit"
  git pull
  cd .. || exit
}

cd $catkin_dir/src || exit

# This stage of the repo was tested to be working, but may not work with future ROS releases
clone_at_commit https://github.com/ros-drivers/velodyne f235ac6b0d1728e97de552f386b412f5fa5a092d

# This stage of the repo was tested to be working, but may not work with future ROS releases
clone_at_commit https://github.com/LORD-MicroStrain/ROS-MSCL e3703a0608536a6d226cc7e727914aed25bd83d5

cd $catkin_dir/ || exit
catkin_make_custom

cd $catkin_dir/src || exit
sudo rm -r velodyne
git clone https://github.com/JohannesByle/velodyne

cd $catkin_dir/ || exit
catkin_make_custom
cd "$cwd" || exit
