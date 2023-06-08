import test_peers
import test_with_docker
import test_without_docker
from build_docker import build_docker

if __name__ == "__main__":
    build_docker(verbose=False)

    test_peers.REBUILD_DOCKER = False
    test_with_docker.REBUILD_DOCKER = False
    test_without_docker.REBUILD_DOCKER = False

    test_without_docker.run_tests()
    test_with_docker.run_tests()
    test_peers.run_tests()
