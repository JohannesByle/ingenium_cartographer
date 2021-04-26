source install_isolated/setup.bash
cd ~/ingenium_cartographer/ || exit
file=$(zenity --file-selection --title="Choose a bag file" --file-filter="*.bag")
chmod +x ~/ingenium_cartographer/display_bag.sh
gnome-terminal --working-directory=~/ingenium_cartographer/ -- ~/ingenium_cartographer/display_bag.sh "$file"
