while true
do
    sshpass -p 'nemesis' rsync -avz --inplace --delete --exclude-from='../rsync-ignore.txt' ../ nemesis@rpi2.dace-alpha.ts.net:"/home/nemesis/app"
done
