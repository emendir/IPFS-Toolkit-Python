"""run this script with: --name CONTATINER_NAME"""

import signal
import subprocess
import time
import os
import threading
import sys
import ipfs_api


def get_option(option):
    try:
        return sys.argv[sys.argv.index(option) + 1]
    except:
        print("Invalid arguments.")
        sys.exit()


class DockerContainer():
    def __init__(self, container_name, auto_run=True):
        self.container_name = container_name
        if auto_run:
            self.run()

    def run(self):
        threading.Thread(target=self._run_docker, args=()).start()
        time.sleep(5)

        # getting container id from container name
        result = subprocess.run(
            f'docker ps -aqf "name=^{self.container_name}$"',
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        self.container_id = result.stdout.strip("\n")

        self.ipfs_id = ""
        while self.ipfs_id == "":
            time.sleep(5)
            self.ipfs_id = self.run_shell_command("ipfs id -f=\"<id>\"")
        self.wait_till_peer_connected()

    def run_python_code(self, python_code):
        command = f"docker exec {self.container_id} /usr/bin/python3 -c \"{python_code}\""
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            # check=True
        )
        return result.stdout

    def run_shell_command(self, command):
        command = f"docker exec {self.container_id} {command}"
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            # check=True
        )
        return result.stdout

    def stop(self):
        """Stops the docker container"""
        if self.container_id:
            os.system(f"docker stop {self.container_id}  >/dev/null 2>&1")

    def restart(self):
        """Creates and runs a Brenthy docker container"""
        os.system(f"docker restart {self.container_id}  >/dev/null 2>&1")
        self.wait_till_peer_connected()

    def wait_till_peer_connected(self):
        peer_connected = False
        while not peer_connected:
            peer_connected = ipfs_api.find_peer(self.ipfs_id)

    def login(self):
        import pyperclip
        command = f"docker exec -it {self.container_id} /bin/bash"
        pyperclip.copy(command)
        print(command)
        print("Command copied to clipboard.")

    def terminate(self):
        """Stops and removes the docker container"""
        print("\nStopping and removing container...")
        os.system(f"docker stop {self.container_id} >/dev/null 2>&1")
        os.system(f"docker rm {self.container_id} >/dev/null 2>&1")
        print("Finished!!")

    def _run_docker(self):
        """Creates and runs a Brenthy docker container"""
        # docker run emendir/ipfs-toolkit

        os.system(
            f"docker run --name {self.container_name} --cap-add SYS_ADMIN --privileged emendir/ipfs-toolkit")


if __name__ == "__main__":
    if "--name" in sys.argv:
        container_name = get_option("--name")
    else:
        container_name = "manually_created"
    docker_container = DockerContainer(container_name)

    def signal_handler(sig, frame):
        """Gets executed when the user hits Ctrl+C"""
        docker_container.terminate()
        sys.exit(0)

    # Handle Ctrl+C (SIGINT), shutting down docker container
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()
