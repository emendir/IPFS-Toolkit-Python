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
    result = subprocess.run(
        "tests/build_docker.sh" + args_str,
        shell=True,
        capture_output=True,
        text=True,
    )
    os.chdir(cwd)
    if result.returncode == 1:
        print(colored("IPFS-Toolkit docker udpate failed!", "red"))
        return False


if __name__ == '__main__':
    build_docker()
