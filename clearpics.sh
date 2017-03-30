STR=$(date +%Y-%m-%d_%H-%M-%S)
echo $STR
mkdir /home/pi/drive_ext/$STR

mv /home/pi/drive_ext/pics /home/pi/drive_ext/$STR
mv /home/pi/drive_ext/backup /home/pi/drive_ext/$STR
mv /home/pi/drive_ext/gif /home/pi/drive_ext/$STR
mv /home/pi/drive_ext/pics_w /home/pi/drive_ext/$STR
mv /home/pi/drive_ext/screen /home/pi/drive_ext/$STR
mv /home/pi/drive_ext/mosaic /home/pi/drive_ext/$STR

sudo rm -rf /home/pi/drive_ext/pics
mkdir /home/pi/drive_ext/pics
sudo rm -rf /home/pi/drive_ext/backup
mkdir /home/pi/drive_ext/backup
sudo rm -rf /home/pi/drive_ext/gif
mkdir /home/pi/drive_ext/gif
sudo rm -rf /home/pi/drive_ext/pics_w
mkdir /home/pi/drive_ext/pics_w
sudo rm -rf /home/pi/drive_ext/screen
mkdir /home/pi/drive_ext/screen
sudo rm -rf /home/pi/drive_ext/mosaic
mkdir /home/pi/drive_ext/mosaic