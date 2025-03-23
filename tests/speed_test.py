""" DON'T FORGET TO REBUILD DOCKER CONTAINER
This script runs a docker container with which it tests various forms of
communication.

Set the 'file_path' variable below to the path of a file_path that can be transmitted
for testing, preferably of size 1-10MB.

Make sure IPFS is running on the local host (configured with
Libp2pStreamMounting and pubsub enabled) before running these tests.

If testing is interrupted and the docker container isn't closed properly
and the next time you run this script you get an error reading:
    docker: Error response from daemon: Conflict.
    The container name "/IPFS-Toolkit-Test" is already in use by container

run the following commands to stop and remove the unterminated container:
```
    docker stop $(docker ps -aqf "name=^IPFS-Toolkit-Test$")
    docker rm $(docker ps -aqf "name=^IPFS-Toolkit-Test$")
```
"""

# import ipfs_datatransmission
from threading import Thread
from datetime import datetime, UTC
from matplotlib import pyplot
from random import randrange
import time
import sys
from termcolor import colored
from docker_container import DockerContainer
import os
import threading

# replace with the path of a file you would like to send
file_path = "/mnt/Uverlin/Music/Davy Jones  - Pirates of the Caribbean.mp3"
# time in seconds to wait for file to transmit before calling test a failure
FILE_SEND_TIMEOUT = 20

TEST_CLI = False

if True:
    sys.path.insert(0, "..")
    if TEST_CLI:
        import ipfs_cli as ipfs_api
    else:
        import ipfs_api
    import ipfs_datatransmission

docker_peer = DockerContainer("IPFS-Toolkit-Test")
for i in range(5):
    maddr = ipfs_api.find_peer(docker_peer.ipfs_id)
    if maddr:
        break
if ipfs_api.find_peer(docker_peer.ipfs_id):
    print("FOUND PEER")
else:
    print("COULDN'T FIND PEER")


TEST_DATA = bytearray([0]*102400)


def test_transmission_speed(buffer_size):
    python_code = "import ipfs_datatransmission;import time;"
    python_code += f"ipfs_datatransmission.DEF_BUFFER_SIZE={buffer_size};"
    python_code += "listener=None;"
    python_code += "on_receive = lambda data, peer_id:listener.terminate();"
    python_code += "listener = ipfs_datatransmission.listen_for_transmissions('speed-test', on_receive);"

    Thread(target=docker_peer.run_python_code, args=(python_code,)).start()
    time.sleep(0.5)  # give listener time to set itself up

    try:
        # transmit data, counting how long it takes
        start_time = datetime.now(UTC)
        ipfs_datatransmission.transmit_data(TEST_DATA, docker_peer.ipfs_id, 'speed-test')
        finish_time = datetime.now(UTC)
    except:
        print("Retrying transmission")
        # transmit data, counting how long it takes
        start_time = datetime.now(UTC)
        ipfs_datatransmission.transmit_data(TEST_DATA, docker_peer.ipfs_id, 'speed-test')
        finish_time = datetime.now(UTC)
    return (finish_time-start_time).total_seconds()


N_REPETITIONS = 100
BUFFERSIZE_RANGE = (920, 1100)
data = [[0] * N_REPETITIONS for i in range(BUFFERSIZE_RANGE[1] - BUFFERSIZE_RANGE[0])]
# data[buffer_size][n]

x_values = list(range(BUFFERSIZE_RANGE[0], BUFFERSIZE_RANGE[1]))
y_values = [0] * len(data)

pyplot.ion()
figure, graph = pyplot.subplots(figsize=(len(data), 150))
curve, = graph.plot(x_values, y_values)

y_min = None
y_max = None
y_min = 0
y_max = 0.1

for n in range(N_REPETITIONS):
    print("Round", n+1)
    for b, buffer_size in enumerate(list(range(BUFFERSIZE_RANGE[0], BUFFERSIZE_RANGE[1]))):
        try:
            data[b][n] = test_transmission_speed(buffer_size)
        except:
            print("Restarting docker container")
            docker_peer.terminate()
            docker_peer.run()

            data[b][n] = test_transmission_speed(buffer_size)

        y_values[b] = float(sum(data[b][:n+1])) / float(n+1)
        # if y_max == None or y_values[b] > y_max:
        #     y_max = y_values[b]
        # if y_min == None or y_values[b] < y_min:
        #     y_min = y_values[b]
        graph.set_ylim([y_min-0.001, y_max+0.001])
        curve.set_ydata(y_values)
        figure.canvas.draw()
        figure.canvas.flush_events()
# peer_id = "12D3KooWGozjxzqUrR1tDihPAcE5o5XKzj1i4GG9C4yV9de2iJ7s"
# ipfs_datatransmission.transmit_data(TEST_DATA, peer_id, 'speed-test', timeout_sec=15)


if __name__ == "__main__":
    # test_find_peer()
    # test_create_conv()
    # test_send_file()
    # test_terminate()
    #
    # # shutdown docker container and make sure no loose threads are hanging
    # test_thread_cleanup()
    pass
