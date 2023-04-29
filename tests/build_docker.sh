# STOP AND DELETE ALL DOCKER CONTAINERS OF THIS IMAGE
docker stop $(docker ps --filter "ancestor=emendir/ipfs-toolkit" -aq) >/dev/null  2>/dev/null
docker rm $(docker ps --filter "ancestor=emendir/ipfs-toolkit" -aq)  >/dev/null  2>/dev/null

docker build -t emendir/ipfs-toolkit .