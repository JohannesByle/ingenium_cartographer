// Include the ROS C++ APIs
#include <ros/ros.h>
#include <rosbag/bag.h>
#include <rosbag/view.h>
#include <std_msgs/Int32.h>
#include <std_msgs/String.h>
#include <sensor_msgs/Imu.h>
#include <sensor_msgs/PointCloud2.h>
#include <velodyne_msgs/VelodyneScan.h>
#include <velodyne_pointcloud/rawdata.h>
#include <velodyne_pointcloud/pointcloudXYZIRT.h>
#include <velodyne_pointcloud/transform.h>
#include <math.h>

#include <boost/foreach.hpp>
#define foreach BOOST_FOREACH

// Standard C++ entry point
int main(int argc, char** argv) {
    velodyne_rawdata::RawData data;
    double min_range = 0.0;
    double max_range = 12000.0;
    data.setParameters(min_range, max_range,0,2*M_PI);
    data.setupOffline("/home/johannes/catkin_ws/src/velodyne/velodyne_pointcloud/params/VeloView-VLP-32C.yaml", max_range, min_range);
    rosbag::Bag new_bag;
    new_bag.open("test.bag", rosbag::bagmode::Write);

    rosbag::Bag bag;
    bag.open("/home/johannes/Downloads/2020-11-25-09-49-03.bag", rosbag::bagmode::Read);
    boost::shared_ptr<velodyne_rawdata::DataContainerBase> container_ptr;
    rosbag::View view(bag);
    foreach(rosbag::MessageInstance const m, view)
    {
        container_ptr = boost::shared_ptr<velodyne_pointcloud::PointcloudXYZIRT>(new velodyne_pointcloud::PointcloudXYZIRT(max_range, min_range, "velodyne", "odom", 1));

        velodyne_msgs::VelodyneScan::ConstPtr s = m.instantiate<velodyne_msgs::VelodyneScan>();
        if (s != NULL) {
            std::cout << "\n";
            std::cout << typeid(*container_ptr).name();
            std::cout << "\n";
            std::cout << typeid(container_ptr).name();
            std::cout << "\n";
            std::cout << "b3 setup \n";
            container_ptr->setup(s);
            std::cout << "after setup \n";
            data.unpack(s->packets[0], *container_ptr, s->header.stamp);
            std::cout << "after unpack \n";
            sensor_msgs::PointCloud2 pcl = container_ptr->finishCloud();
            std::cout << pcl;
            new_bag.write("/velodyne_points", s->header.stamp, pcl);
        }

    }

    bag.close();
}