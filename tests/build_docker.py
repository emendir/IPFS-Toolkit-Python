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
    exit_code = os.system("tests/build_docker.sh" + args_str)
    os.chdir(cwd)
    if exit_code == 1:
        print(colored("Docker image udpate failed!", "red"))
        return False


if __name__ == '__main__':
    build_docker()
