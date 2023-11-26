while true
do
      sshpass -p 'a' rsync --inplace -avz --delete --exclude-from='../rsync-ignore.txt' ../ pi@rpi:/home/pi/NemesisDrone
done
