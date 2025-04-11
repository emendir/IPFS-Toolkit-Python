# STOP AND DELETE ALL DOCKER CONTAINERS OF THIS IMAGE
# the absolute path of this script's directory
script_dir="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd $script_dir/../..

docker stop $(docker ps --filter "ancestor=emendir/ipfs-toolkit" -aq) >/dev/null 2>/dev/null
docker rm $(docker ps --filter "ancestor=emendir/ipfs-toolkit" -aq)  >/dev/null 2>/dev/null
# 
# rsync -XAva --exclude-from=.gitignore  --delete ../KuboPythonLib tests/ipfs_toolkit_docker/python_packages/
# rsync -XAva  ../KuboPythonLib/src/ --delete tests/ipfs_toolkit_docker/python_packages/KuboPythonLib/src/
rsync -XAva  ../KuboPythonLib/dist/*.whl tests/ipfs_toolkit_docker/python_packages/

docker build -t emendir/ipfs-toolkit -f tests/ipfs_toolkit_docker/Dockerfile .


# docker run --cap-add SYS_ADMIN --privileged emendir/ipfs-toolkit
