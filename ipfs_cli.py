import json
from threading import Thread
import tempfile
from subprocess import Popen, PIPE
# from datetime import datetime

import stat
# import urllib.request
import tarfile
import os
import shutil
import platform
import ipfs_lns
from base64 import urlsafe_b64decode
android_distros = ["lineageos", "android"]

ipfs_url = "https://github.com/ipfs/go-ipfs/releases/download/v0.12.2/go-ipfs_v0.12.2_linux-arm64.tar.gz"
ipfs_zip_path = "go-ipfs_v0.12.2_linux-arm64.tar.gz"


def run_command(cmd, as_str=True):
    """
    Parameters:
        as_str: whether or not to return output decoded as string or raw bytes
    """
    if isinstance(cmd, str):
        cmd = cmd.split(" ")
    try:
        proc = Popen(cmd, stdout=PIPE)
    except:
        return None
    proc.wait()
    if as_str:
        text = ""
    else:
        text = b''
    for line in proc.stdout:
        if as_str:
            text += line.decode('utf-8')
        else:
            text += line
    return text


ipfs_cmd = "ipfs"
if not run_command([ipfs_cmd]):
    if bool(run_command("./ipfs")):
        ipfs_cmd = "./ipfs"


def is_ipfs_running():
    return len(my_multiaddrs()) > 0


def try_run_ipfs():
    print("Starting IPFS...")
    proc = Popen([ipfs_cmd, "daemon", "--enable-pubsub-experiment"],
                 stdout=PIPE, stdin=PIPE)
    while True:
        data = proc.stdout.read1().decode()
        if data.strip("\n") == "Daemon is ready":
            return True


def download_ipfs_binary(downloading_callback=None):
    global found_ipfs
    global ipfs_cmd
    if not run_command([ipfs_cmd]):
        if bool(run_command("./ipfs")):
            ipfs_cmd = "./ipfs"
        else:
            if downloading_callback:
                Thread(target=downloading_callback, args=()).start()
            architecture_codes = {
                "aarch64": "arm64",
                "armv8l": "arm64",
                "x86_64": "amd64",
            }
            try:
                architecture = architecture_codes[platform.machine()]
            except:
                return

            ipfs_url = f"https://github.com/ipfs/go-ipfs/releases/download/v0.12.2/go-ipfs_v0.12.2_{platform.system().lower()}-{architecture}.tar.gz"

            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
            from urllib import request
            request.urlretrieve(ipfs_url, ipfs_zip_path)
            with tarfile.open(ipfs_zip_path, "r:gz") as tar:
                safe_tar_extract(tar)

            result = run_command("go-ipfs/install.sh")
            if "cannot install" in result and "ipfs" in os.listdir("go-ipfs"):
                shutil.copy("go-ipfs/ipfs", "ipfs")
                st = os.stat("ipfs")
                os.chmod("ipfs", st.st_mode | stat.S_IEXEC)
                ipfs_cmd = "./ipfs"
    found_ipfs = bool(run_command([ipfs_cmd]))
    if found_ipfs:
        # init ipfs
        if not run_command([ipfs_cmd, "id"]):
            run_command([ipfs_cmd, "init"])
        # configure ipfs
        run_command(
            [ipfs_cmd, "config", "--json Experimental.Libp2pStreamMounting", "true"])
        # run ipfs
        try_run_ipfs()


found_ipfs = bool(run_command([ipfs_cmd]))


if found_ipfs:
    if not run_command([ipfs_cmd, "id"]):
        run_command([ipfs_cmd, "init"])


# Publishes the input data to specified the IPFS PubSub topic


def pubsub_publish(topic, data):
    """Publishes te specified data to the specified IPFS-PubSub topic.
    Parameters:
        topic: str: the name of the IPFS PubSub topic to publish to
        data: string or bytes/bytearray: either the filepath of a file whose
            content should be published to the pubsub topic,
            or the raw data to be published as a string or bytearray.
            When using an older version of IPFS < v0.11.0 however,
            only plai data as a string is accepted.
    """
    if isinstance(data, str) and not os.path.exists(data):
        data = data.encode()
    if isinstance(data, bytes) or isinstance(data, bytearray):
        with tempfile.NamedTemporaryFile() as tp:
            tp.write(data)
            tp.flush()
            run_command([ipfs_cmd, "pubsub", "pub", topic, tp.name])
    else:
        run_command([ipfs_cmd, "pubsub", "pub", topic, data])


# Listens to the specified IPFS PubSub topic and passes received data to the input eventhandler function
# master, slave = pty.openpty()
# proc = Popen(ipfs_cmd + " pubsub sub test", shell=True,
#              stdin=PIPE, stdout=slave, stderr=slave, close_fds=True)


class PubsubListener():
    _terminate = False
    __listening = False

    def __init__(self, topic, eventhandler):
        self.topic = topic
        self.eventhandler = eventhandler
        self.listen()

    def _listen(self):
        if self.__listening:
            return
        self.__listening = True
        """blocks the calling thread"""
        while not self._terminate:
            self.proc = Popen([ipfs_cmd, "pubsub", "sub", self.topic],
                              stdout=PIPE, stdin=PIPE)
            while True:
                data = {
                    "senderID": "",
                    "data": self.proc.stdout.read1(),
                }
                if self._terminate:
                    return
                Thread(target=self.eventhandler, args=(data,)).start()
        self.__listening = False

    def __decode_base64_url(self, data: str):
        """Performs the URL-Safe multibase decoding required by the new pubsub function (since IFPS v0.11.0) on strings"""
        # print(data)
        data = str(data)[1:].encode()
        missing_padding = len(data) % 4
        if missing_padding:
            data += b'=' * (4 - missing_padding)
        # print(data.decode())
        # print(urlsafe_b64decode(data))
        return urlsafe_b64decode(data)

    def listen(self):
        self._terminate = False
        self.listener_thread = Thread(target=self._listen, args=(),
                                      name=f"ipfs_cli.pubsub_listener {self.topic}")
        self.listener_thread.start()

    def terminate(self, wait=False):
        """May let one more pubsub message through.

        Args:
            wait (bool): whether or not this function should block until all
                activity has been stopped and resources have been cleaned up
        """
        self._terminate = True
        pubsub_publish(self.topic, "terminate".encode())
        if wait:
            self.listener_thread.join()


def pubsub_subscribe(topic, eventhandler):
    """
    Listens to the specified IPFS PubSub topic, calling the eventhandler
    whenever a message is received, passing the message data and its sender
    to the evventhandler.
    Parameters:
        topic: str: the name of the IPFS PubSub topic to publish to
        eventhandler: function(dict): the function to be executed whenever a message is received.
                            The eventhandler parameter is a dict with the keys 'data' and 'senderID',
                            except when using an older version of IPFS < v0.11.0,
                            in which case only the message is passed as a string.
    Returns a PubsubListener object which can  be terminated with the .terminate() method (and restarted with the .listen() method)
    """
    return PubsubListener(topic, eventhandler)


def publish(path: str):
    """
    upload a file or a directory to IPFS.
    Returns the Hash of the uploaded file.
    """
    result = run_command([ipfs_cmd, "add", "-r", path]).split("\n")
    while result[-1] == "":
        result.pop(-1)
    return result[-1].split(" ")[1]
# Downloads the file with the specified ID and saves it with the specified path


def pin(cid: str):
    run_command([ipfs_cmd, "pin", "add", cid])


def unpin(cid: str):
    run_command([ipfs_cmd, "pin", "rm", cid])


def download(CID, path=""):
    path_option = ""
    if path:
        path_option = f"-o={path}"
    run_command([ipfs_cmd, "get", CID,  path_option])


def read(CID):
    return run_command([ipfs_cmd, "cat", CID], as_str=False)


def create_ipns_record(name: str, type: str = "rsa", size: int = 2048):

    result = run_command(
        [ipfs_cmd, "key", "gen", f"--type={type}", f"--size={str(size)}", name])
    return result.strip("\n")


def update_ipns_record_from_cid(name: str, cid: str, ttl: str = "24h", lifetime: str = "24h"):
    """
    Parameters:
        string ttl: Time duration this record should be cached for.
                                Uses the same syntax as the lifetime option.
                                (caution: experimental).
        string lifetime: Time duration that the record will be valid for.
                                Default: 24h.
    """
    run_command([ipfs_cmd, "name", "publish",
                 f"--key={name}", f"--ttl={ttl}", f"--lifetime={lifetime}", f"/ipfs/{cid}"])


def update_ipns_record(name: str, path, ttl: str = "24h", lifetime: str = "24h"):
    """
    Parameters:
        string ttl: Time duration this record should be cached for.
                                Uses the same syntax as the lifetime option.
                                (caution: experimental).
        string lifetime: Time duration that the record will be valid for.
                                Default: 24h.
    """
    cid = publish(path)
    update_ipns_record_from_cid(name, cid, ttl=ttl, lifetime=lifetime)
    return cid


def download_ipns_record(name, path="", nocache=False):
    return download(resolve_ipns_key(name, nocache=nocache), path)


def resolve_ipns_key(ipns_id, nocache=False):
    return run_command([ipfs_cmd, "name", "resolve", f"--nocache={nocache}", f"{ipns_id}"]).strip("\n")


def read_ipns_record(name, nocache=False):
    return read(resolve_ipns_key(name, nocache=nocache))

# Returns a list of the multiaddresses of all connected peers


def list_peer_multiaddrs():
    proc = Popen(['ipfs', 'swarm', 'peers'], stdout=PIPE)
    proc.wait()
    peers = []
    for line in proc.stdout:
        peers.append(line.decode('utf-8').strip("\n"))

    return peers

# Returns the multiaddresses of input the peer ID


def find_peer(ID: str):
    response = run_command([ipfs_cmd, "routing", "findpeer", ID])
    return {"Responses": [{"ID": ID, "Addrs": response.split("\n")}]}

# Returns the IPFS ID of the currently running IPFS node


def my_id():
    return json.loads(run_command([ipfs_cmd, "id"])).get("ID")


def my_multiaddrs():
    multi_addrs = json.loads(run_command([ipfs_cmd, "id"])).get("Addresses")
    if multi_addrs:
        return multi_addrs
    else:
        return []


myid = my_id


def create_tcp_listening_connection(name, port):
    run_command([ipfs_cmd, "p2p", "listen", "/x/" +
                 name, "/ip4/127.0.0.1/tcp/" + str(port)])


ListenUDP = create_tcp_listening_connection
listenudp = create_tcp_listening_connection
listenonport = create_tcp_listening_connection
listen = create_tcp_listening_connection
listen = create_tcp_listening_connection


def create_tcp_sending_connection(name: str, port, peerID):
    # result = run_command([ipfs_cmd, "p2p", "forward", "/x/" + name, "/ip4/127.0.0.1/tcp/" +
    #                     str(port), "/p2p/" + peerID])
    cmd = [ipfs_cmd, "p2p", "forward", "/x/" + name, "/ip4/127.0.0.1/tcp/" +
           str(port), "/p2p/" + peerID]

    try:
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
    except:
        return None
        # proc = Popen(['ipfs', 'id'], stdout=PIPE)
    proc.wait()
    e = proc.stderr.readline()
    if e:
        print(e)
        return False    # signal failure
    else:
        return True     # signal success


def close_all_tcp_connections(listeners_only=False):
    """Close all libp2p stream-mounting (IPFS port-forwarding) connections.
    Args:
        listeners_only (bool): if set to True, only listening connections are closed
    """
    if listeners_only:
        cmd = [ipfs_cmd, "p2p", "close", "-l", "/p2p/"+my_id()]
    else:
        cmd = [ipfs_cmd, "p2p", "close", "-a"]
    run_command(cmd)


def close_tcp_sending_connection(name: str = None, port: str = None, peer_id: str = None):
    """Close specific sending libp2p stream-mounting (IPFS port-forwarding) connections.
    Args:
        name (str): the name of the connection to close
        port (str): the local forwarded TCP port of the connection to close
        peer_id (str): the target peer_id of the connection to close
    """
    if name and name[:3] != "/x/":
        name = "/x/" + name
    if port and isinstance(port, int):
        listenaddress = f"/ip4/127.0.0.1/tcp/{port}"
    else:
        listenaddress = port
    if peer_id and peer_id[:5] != "/p2p/":
        targetaddress = "/p2p/" + peer_id
    else:
        targetaddress = peer_id
    cmd = [ipfs_cmd, "p2p", "close"]
    if all:
        cmd.append("--all")
    else:
        if name:
            cmd.append(f"--name={name}")
        if listenaddress:
            cmd.append(f"--listen-address={listenaddress}")
        if targetaddress:
            cmd.append(f"--target-address={targetaddress}")
    run_command(cmd)


def close_tcp_listening_connection(name: str = None, port: str = None):
    """Close specific listening libp2p stream-mounting (IPFS port-forwarding) connections.
    Args:
        name (str): the name of the connection to close
        port (str): the local listening TCP port of the connection to close
    """
    if name and name[:3] != "/x/":
        name = "/x/" + name
    if port and isinstance(port, int):
        targetaddress = f"/ip4/127.0.0.1/tcp/{port}"
    else:
        targetaddress = port
    cmd = [ipfs_cmd, "p2p", "close"]
    if all:
        cmd.append("--all")
    else:
        if name:
            cmd.append(f"--name={name}")
        if targetaddress:
            cmd.append(f"--target-address={targetaddress}")
    run_command(cmd)


def check_peer_connection(id, name=""):
    """
    Tries to connect to the specified peer, and stores its multiaddresses in ipfs_lns.
    Paramaters:
        id: the IPFS PeerID or the ipfs_lns name  of the computer to connect to
        name: (optional) the human readable name of the computer to connect to (not critical, you can put in whatever you like)"""
    contact = ipfs_lns.get_contact(id)
    if not contact:
        contact = ipfs_lns.add_contact(id, name)
    return contact.check_connection()


def safe_tar_extract(tar, path=".", members=None, *, numeric_owner=False):
    """
    Security patch to replace the tar.extractall function,
    by TrellixVulnTeam to fix the CVE-2007-4559 'bug'.
    """
    def is_within_directory(directory, target):

        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)

        prefix = os.path.commonprefix([abs_directory, abs_target])

        return prefix == abs_directory

    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not is_within_directory(path, member_path):
            raise Exception("Attempted Path Traversal in Tar File")

    tar.extractall(path, members, numeric_owner=numeric_owner)
