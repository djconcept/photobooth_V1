STR=$(date +%Y-%m-%d_%H-%M-%S)
echo $STR
mkdir /media/pi/PHOTOBOOTH/$STR/


cp -R /home/pi/drive_ext/pics/ /media/pi/PHOTOBOOTH/$STR/
cp -R /home/pi/drive_ext/pics_w/ /media/pi/PHOTOBOOTH/$STR/

echo "La copie c'est bien déroulée"