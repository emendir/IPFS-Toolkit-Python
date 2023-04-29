import os


def build_docker(verbose=True):
    print("Building docker image...")
    cwd = os.getcwd()
    os.chdir("..")
    args_str = ""
    if not verbose:
        args_str += " >/dev/null"
    os.system("tests/build_docker.sh"+args_str)
    os.chdir(cwd)


if __name__ == '__main__':
    build_docker()
