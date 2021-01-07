file1=$(zenity --file-selection --title="Choose first point cloud" --file-filter="*.ply")
file2=$(zenity --file-selection --title="Choose second point cloud" --file-filter="*.ply")
chmod +x ~/ingenium_cartographer/subtract.sh
gnome-terminal --working-directory=/home/johannes/ingenium_cartographer/ -- ~/ingenium_cartographer/subtract.sh "$file1" "$file2"
