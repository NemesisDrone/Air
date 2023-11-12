while true
do
      sshpass -p 'a' rsync --inplace -avz --delete ../ pi@rpi:/home/pi/Air
done
