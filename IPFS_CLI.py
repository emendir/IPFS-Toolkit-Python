import json
from threading import Thread
import tempfile
from subprocess import Popen, PIPE
from datetime import datetime

import stat
# import urllib.request
import tarfile
import os
import shutil
import platform
import IPFS_LNS
android_distros = ["lineageos", "android"]

ipfs_url = "https://github.com/ipfs/go-ipfs/releases/download/v0.12.2/go-ipfs_v0.12.2_linux-arm64.tar.gz"
ipfs_zip_path = "go-ipfs_v0.12.2_linux-arm64.tar.gz"


def RunCommand(cmd):
    if isinstance(cmd, str):
        cmd = cmd.split(" ")
    try:
        proc = Popen(cmd, stdout=PIPE)
    except:
        return None
    proc.wait()
    text = ""
    for line in proc.stdout:
        text += line.decode('utf-8')
    return text


ipfs_cmd = "ipfs"
if not RunCommand([ipfs_cmd]):
    if bool(RunCommand("./ipfs")):
        ipfs_cmd = "./ipfs"


def IsDaemonRunning():
    try:
        proc = Popen([ipfs_cmd, "swarm", "peers"], stdout=PIPE, stderr=PIPE)

        proc.wait()
        text = ""
        if proc.stderr.readline():
            return False
        else:
            return True
    except:
        return


def RunDaemon():
    try:
        proc = Popen([ipfs_cmd, "daemon", "--enable-pubsub-experiment"],
                     stdout=PIPE, stdin=PIPE)
        while True:
            data = proc.stdout.read1().decode()
            if data.strip("\n") == "Daemon is ready" or IsDaemonRunning():
                return True
    except:
        return


def DownloadIPFS_Binary(downloading_callback=None):
    global found_ipfs
    global ipfs_cmd
    if not RunCommand([ipfs_cmd]):
        if bool(RunCommand("./ipfs")):
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

            result = RunCommand("go-ipfs/install.sh")
            if "cannot install" in result and "ipfs" in os.listdir("go-ipfs"):
                shutil.copy("go-ipfs/ipfs", "ipfs")
                st = os.stat("ipfs")
                os.chmod("ipfs", st.st_mode | stat.S_IEXEC)
                ipfs_cmd = "./ipfs"
    found_ipfs = bool(RunCommand([ipfs_cmd]))
    if found_ipfs:
        # init ipfs
        if not RunCommand([ipfs_cmd, "id"]):
            RunCommand([ipfs_cmd, "init"])
        # configure ipfs
        RunCommand(
            [ipfs_cmd, "config", "--json Experimental.Libp2pStreamMounting", "true"])
        # run ipfs
        RunDaemon()


found_ipfs = bool(RunCommand([ipfs_cmd]))


if found_ipfs:
    if not RunCommand([ipfs_cmd, "id"]):
        RunCommand([ipfs_cmd, "init"])


# Publishes the input data to specified the IPFS PubSub topic


def PublishToTopic(topic, data):
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
            RunCommand([ipfs_cmd, "pubsub", "pub", topic, tp.name])
    else:
        RunCommand([ipfs_cmd, "pubsub", "pub", topic, data])


# Listens to the specified IPFS PubSub topic and passes received data to the input eventhandler function
# master, slave = pty.openpty()
# proc = Popen(ipfs_cmd + " pubsub sub test", shell=True,
#              stdin=PIPE, stdout=slave, stderr=slave, close_fds=True)


class PubsubListener():
    terminate = False
    __listening = False

    def __init__(self, topic, eventhandler):
        self.topic = topic
        self.eventhandler = eventhandler
        self.Listen()

    def _listen(self):
        if self.__listening:
            return
        self.__listening = True
        """blocks the calling thread"""
        while not self.terminate:
            proc = Popen([ipfs_cmd, "pubsub", "sub", self.topic],
                         stdout=PIPE, stdin=PIPE)
            while True:
                data = proc.stdout.read1()
                Thread(target=self.eventhandler, args=(data,)).start()
        self.__listening = False

    def __DecodeBase64URL(self, data: str):
        """Performs the URL-Safe multibase decoding required by the new pubsub function (since IFPS v0.11.0) on strings"""
        # print(data)
        data = str(data)[1:].encode()
        missing_padding = len(data) % 4
        if missing_padding:
            data += b'=' * (4 - missing_padding)
        # print(data.decode())
        # print(urlsafe_b64decode(data))
        return urlsafe_b64decode(data)

    def Listen(self):
        self.terminate = False
        thr = Thread(target=self._listen, args=())
        thr.start()

    def Terminate(self):
        """May let one more pubsub message through"""
        self.terminate = True


def SubscribeToTopic(topic, eventhandler):
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
    Returns a PubsubListener object which can  be terminated with the .Terminate() method (and restarted with the .Listen() method)
    """
    return PubsubListener(topic, eventhandler)


def UnSubscribeFromTopic(topic, eventhandler):
    index = 0
    for subscription in subscriptions:
        if(subscription[0] == topic and subscription[1] == eventhandler):
            subscription[2].terminate()
            break
        index = index + 1
    # remove the subscription from the list of subscriptions
    subscriptions.pop(index)


def Publish(path: str):
    """
    Upload a file or a directory to IPFS.
    Returns the Hash of the uploaded file.
    """
    result = RunCommand([ipfs_cmd, "add", "-r", path]).split("\n")
    while result[-1] == "":
        result.pop(-1)
    return result[-1].split(" ")[1]
# Downloads the file with the specified ID and saves it with the specified path


def Pin(cid: str):
    RunCommand([ipfs_cmd, "pin", "add", cid])


def Unpin(cid: str):
    RunCommand([ipfs_cmd, "pin", "rm", cid])


def DownloadFile(CID, path=""):
    path_option = ""
    if path:
        path_option = f"-o={path}"
    RunCommand([ipfs_cmd, "get", CID,  path_option])


def CatFile(CID):
    return RunCommand([ipfs_cmd, "cat", CID])


def CreateIPNS_Record(name: str, type: str = "rsa", size: int = 2048):

    result = RunCommand(
        [ipfs_cmd, "key", "gen", f"--type={type}", f"--size={str(size)}", name])
    return result.strip("\n")


def UpdateIPNS_RecordFromHash(name: str, cid: str, ttl: str = "24h", lifetime: str = "24h"):
    """
    Parameters:
        string ttl: Time duration this record should be cached for.
                                Uses the same syntax as the lifetime option.
                                (caution: experimental).
        string lifetime: Time duration that the record will be valid for.
                                Default: 24h.
    """
    RunCommand([ipfs_cmd, "name", "publish",
               f"--key={name}", f"--ttl={ttl}", f"--lifetime={lifetime}", f"/ipfs/{cid}"])


def UpdateIPNS_Record(name: str, path, ttl: str = "24h", lifetime: str = "24h"):
    """
    Parameters:
        string ttl: Time duration this record should be cached for.
                                Uses the same syntax as the lifetime option.
                                (caution: experimental).
        string lifetime: Time duration that the record will be valid for.
                                Default: 24h.
    """
    cid = Publish(path)
    UpdateIPNS_RecordFromHash(name, cid, ttl=ttl, lifetime=lifetime)
    return cid


def DownloadIPNS_Record(name, path="", nocache=False):
    return DownloadFile(ResolveIPNS_Key(name, nocache=nocache), path)


def ResolveIPNS_Key(ipns_id, nocache=False):
    return RunCommand([ipfs_cmd, "name", "resolve", f"--nocache={nocache}", f"{ipns_id}"]).strip("\n")


def CatIPNS_Record(name, nocache=False):
    return CatFile(ResolveIPNS_Key(name, nocache=nocache))

# Returns a list of the multiaddresses of all connected peers


def ListPeerMaddresses():
    proc = Popen(['ipfs', 'swarm', 'peers'], stdout=PIPE)
    proc.wait()
    peers = []
    for line in proc.stdout:
        peers.append(line.decode('utf-8').strip("\n"))

    return peers

# Returns the multiaddresses of input the peer ID


def FindPeer(ID: str):
    response = RunCommand([ipfs_cmd, "dht", "findpeer", ID])
    return {"Responses": [{"ID": ID, "Addrs": response.split("\n")}]}

# Returns the IPFS ID of the currently running IPFS node


def MyID():
    return json.loads(RunCommand([ipfs_cmd, "id"])).get("ID")


myid = MyID


def ListenOnPort(protocol, port):
    RunCommand([ipfs_cmd, "p2p", "listen", "/x/" +
               protocol, "/ip4/127.0.0.1/tcp/" + str(port)])


ListenUDP = ListenOnPort
listenudp = ListenOnPort
listenonport = ListenOnPort
Listen = ListenOnPort
listen = ListenOnPort


def ForwardFromPortToPeer(protocol: str, port, peerID):
    # result = RunCommand([ipfs_cmd, "p2p", "forward", "/x/" + protocol, "/ip4/127.0.0.1/tcp/" +
    #                     str(port), "/p2p/" + peerID])
    cmd = [ipfs_cmd, "p2p", "forward", "/x/" + protocol, "/ip4/127.0.0.1/tcp/" +
           str(port), "/p2p/" + peerID]
    if isinstance(cmd, str):
        cmd = cmd.split(" ")
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


def ClosePortForwarding(all: bool = False, protocol: str = None, listenaddress: str = None, targetaddress: str = None):
    cmd = [ipfs_cmd, "p2p", "close"]
    if all:
        cmd.append("--all")
    else:
        if protocol:
            cmd.append(f"--protocol={protocol}")
        if listenaddress:
            cmd.append(f"--listen-address={listenaddress}")
        if targetaddress:
            cmd.append(f"--target-address={targetaddress}")
    RunCommand(cmd)


def CheckPeerConnection(id, name=""):
    """
    Tries to connect to the specified peer, and stores its multiaddresses in IPFS_LNS.
    Paramaters:
        id: the IPFS PeerID or the IPFS_LNS name  of the computer to connect to
        name: (optional) the human readable name of the computer to connect to (not critical, you can put in whatever you like)"""
    contact = IPFS_LNS.GetContact(id)
    if not contact:
        contact = IPFS_LNS.AddContact(id, name)
    return contact.CheckConnection()


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
