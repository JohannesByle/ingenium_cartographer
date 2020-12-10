import rosbag
import os
import sys


def get_first_n(bag_file, n_max, topic_of_interest="/velodyne_points"):
    bag = rosbag.Bag(bag_file)
    new_bag_filename = "first_n.bag"
    new_bag = rosbag.Bag(new_bag_filename, "w")
    n = 0
    for topic, msg, t in bag.read_messages():
        if n > n_max:
            break
        if not topic_of_interest or topic == topic_of_interest:
            n += 1
        print((topic, t))
        new_bag.write(topic, msg, t)

    new_bag.close()
    if os.path.exists(new_bag_filename.replace(".bag", ".orig.bag")):
        os.remove(new_bag_filename.replace(".bag", ".orig.bag"))


if __name__ == "__main__":
    if len(sys.argv) > 3:
        get_first_n(sys.argv[1], int(sys.argv[2]), sys.argv[3])
    else:
        get_first_n(sys.argv[1], int(sys.argv[2]))
