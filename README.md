# ingenium_cartographer
Bash scripts and config files for recording and slamming data for the Wheaton College Tel Shimron lidar project

## Installation Instructions
The order of these steps is very important, and not following this order can lead to irreparable problems with the installation.

1. Install ROS Noetic using their [guide](http://wiki.ros.org/noetic/Installation/Ubuntu)
2. If you are doing things other than just recording data (i.e processing recordings) go to step 3, othwerwise skip step 3 and run the following commands:
    ```
    mkdir catkin_ws
    cd catkin_ws
    wstool init src
    wstool merge -t src https://raw.githubusercontent.com/cartographer-project/cartographer_ros/master/cartographer_ros.rosinstall
    wstool update -t src
    ```
3. Install Cartographer ROS their [guide](https://google-cartographer-ros.readthedocs.io/en/latest/compilation.html). 
    1. At the end of this process you should have a directory called `catkin_ws` in your home directory, i.e `~/catkin_ws/`
    2. This directory should have the following structure\
      catkin_ws/\
      ├─ build_isolated/\
      ├─ devel_isolated/\
      ├─ install_isolated/\
      ├─ src/
4. Download the binaries for the MSCL library. This [link](https://github.com/LORD-MicroStrain/MSCL/releases/download/v61.0.16/c++-mscl_61.0.16_amd64.deb) will start the download. Once the download has finished install the binaries using dpgk.
    ```
    cd ~/Downloads
    sudo dpkg -i c++-mscl_61.0.16_amd64.deb
    sudo apt install -f     
    ```
5. Clone the ingenium_cartographer repository into your home directory
    ```
    cd ~
    git clone https://github.com/JohannesByle/ingenium_cartographer
    ```
6. Run the custom installation script within ingenium_cartographer to finish installing the rest of the dependencies
    ```
    cd ~/ingenium_cartographer
    . ./install.sh
    ```
7. Setting up for use without the command line (optional)
    1. Change default behavior for executable text files by edititing the nautilus preferences. The preferences can be found by clicking the hamburger button in the Files app `Preferences > Behavior > Executable Text Files > Run them`
    2. Right click on the file you want to make clickable (process_bag_gui.sh) and open properties. Check the `Allow executing file as program` under the `Permissions` tab.
