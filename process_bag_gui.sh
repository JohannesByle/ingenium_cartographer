cd ~/ingenium_cartographer/ || exit
file=$(zenity --file-selection --title="Choose a bag file" --file-filter="*.bag")
if [ ! -f "$file" ]; then
  echo "$file is not a file."
  return 1
fi
chmod +x ~/ingenium_cartographer/process_bag.sh
gnome-terminal --working-directory=/home/johannes/ingenium_cartographer/ -- ~/ingenium_cartographer/process_bag.sh "$file"
