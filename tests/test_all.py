if True:
    import sys
    import os
    sys.path.insert(0, os.path.join((os.path.dirname(__file__)),"..","src"))
    import ipfs_api
import test_peers
import test_with_docker
import test_without_docker
from ipfs_toolkit_docker.build_docker import build_docker
from time import sleep
if __name__ == "__main__":
    build_docker(verbose=False)

    test_peers.REBUILD_DOCKER = False
    test_with_docker.REBUILD_DOCKER = False
    test_without_docker.REBUILD_DOCKER = False

    test_without_docker.run_tests()
    sleep(30)
    test_with_docker.run_tests()
    sleep(30)
    test_peers.run_tests()
