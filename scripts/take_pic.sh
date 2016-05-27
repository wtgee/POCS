#!/bin/bash

P=$1
T=$2
F=$3
# echo 'Taking picture'
# echo "P=${P}"
# echo "T=${T}"
# echo "F=${F}"

opts="--port ${P} --set-config eosremoterelease=Immediate --wait-event=${T}s --set-config eosremoterelease=4 --wait-event-and-download=1s --filename=${F}"

# echo $opts

/usr/bin/gphoto2 ${opts} &> /dev/null