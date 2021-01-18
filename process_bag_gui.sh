cd ~/ingenium_cartographer/ || exit
file=$(zenity --file-selection --title="Choose a bag file" --file-filter="*.bag")
chmod +x ~/ingenium_cartographer/process_bag.sh
zenity --question --text="Spawn RVIZ window?" --width=150
if [ $? = 1 ]; then
  gnome-terminal --working-directory=~/ingenium_cartographer/ -- ~/ingenium_cartographer/process_bag.sh "$file"
else
  gnome-terminal --working-directory=~/ingenium_cartographer/ -- ~/ingenium_cartographer/process_bag.sh "$file" -v
fi
