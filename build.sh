#!/bin/bash

dirname=$PWD
result="${dirname%"${dirname##*[!/]}"}" # extglob-free multi-trailing-/ trim
result="${result##*/}" # remove everything before the last / (like basename)

if [ "$result" != "hoth" ]; then
    echo 'ERROR: Run this command from the algos root directory!'
    return 1
fi

if [ $1 ]; then
    tag=$1
else
    tag=$USER
fi

HOOTH_COMMIT=$(git rev-parse HEAD)
SHORT_HASH=$(git rev-parse --short HEAD)

docker build \
    --build-arg ALGOS_COMMIT=$ALGOS_COMMIT \
    -t algos:$tag \
    -t algos:$SHORT_HASH \
    .
