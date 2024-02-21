while true
do
    sshpass -p 'nemesis' rsync -avz --inplace --delete --exclude-from='../rsync-ignore.txt' ../ nemesis@rpi1.dace-alpha.ts.net:"/home/nemesis/app"
done
