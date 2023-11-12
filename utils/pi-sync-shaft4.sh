while true
do
    rsync -avz --inplace --delete ../ x@shaft-rpi4.dace-alpha.ts.net:"/app/"
done
