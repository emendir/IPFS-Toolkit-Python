import os

import subprocess
from termcolor import colored
from datetime import datetime


def build_docker(verbose=True):
    print("Building docker image...")
    cwd = os.getcwd()
    os.chdir("..")
    args_str = ""
    if not verbose:
        args_str += " >/dev/null"
    os.system("tests/build_docker.sh" + args_str)
    os.chdir(cwd)

    result = subprocess.run(
        "docker inspect -f '{{.Created}}' emendir/ipfs-toolkit",
        shell=True,
        capture_output=True,
        text=True,
        check=True
    )

    docker_creation_date = datetime.strptime(
        result.stdout.split(".")[0], "%Y-%m-%dT%H:%M:%S")
    if (datetime.utcnow() - docker_creation_date).total_seconds() < 100:
        print("IPFS-Toolkit docker updated!")
        return True
    else:
        print(colored("IPFS-Toolkit docker udpate failed!", "red"))
        return False


if __name__ == '__main__':
    build_docker()
