import appdirs
import os
import os.path
import json
# from . import ipfshttpclient2 as ipfshttpclient
from subprocess import Popen, PIPE
from threading import Thread
import ipfs_api

# ipfs = ipfshttpclient.client.Client()
ipfs_dir = os.path.join(appdirs.user_data_dir(), "IPFS")
lns_dir = os.path.join(appdirs.user_data_dir(), "IPFS", "LNS")

try:
    if not os.path.exists(ipfs_dir):
        os.makedirs(ipfs_dir)

    if not os.path.exists(lns_dir):
        os.makedirs(lns_dir)
except PermissionError:    # in a buildozer project execution fails here
    ipfs_dir = os.path.join("AppData", "IPFS")
    lns_dir = os.path.join("AppData", "IPFS", "LNS")
    if not os.path.exists(ipfs_dir):
        os.makedirs(ipfs_dir)

    if not os.path.exists(lns_dir):
        os.makedirs(lns_dir)


class Node:
    known_multiaddrs = list()
    connection_checker = None

    def __init__(self, id, name="", known_multiaddrs=list()):
        if name == "":
            self.id, self.name, self.known_multiaddrs = json.loads(id)
        else:
            self.id = id
            self.name = name
            self.known_multiaddrs = known_multiaddrs

    def to_serial(self):
        return json.dumps([self.id, self.name, self.known_multiaddrs])

    def remember_multiaddrs(self):
        multiaddrs = ipfs_api.find_peer(self.id).get("Responses")[0].get("Addrs")
        edited = False

        for addr in multiaddrs:
            if not "/ip6/::" in addr and not "/ip4/192.168" in addr and not "/ip4/127.0" in addr:
                found = False
                for k_addr in self.known_multiaddrs:
                    if addr == k_addr[0]:
                        k_addr[1] += 1
                        edited = True
                        found = True
                        break
                if not found:
                    self.known_multiaddrs.insert(0, [addr, 1])
                    edited = True
        if edited:
            save_contacts()

    def try_to_connect(self):
        """Tries to connect to this IPFS peer using 'ipfs routing findpeer ...'
        and 'ipfs swarm connect ...' with remembered multiaddresses.
        Note: Can take a long time time run. You generally want to use
        check_connection() instead of try_to_connect(), that function runs this
        function if it is not already running"""
        # first trying 'ipfs routing findpeer ...'
        try:
            response = ipfs_api.find_peer(self.id)
            if(len(response.get("Responses")[0].get("Addrs")) > 0):  # if connections succeeds
                self.remember_multiaddrs()
                return True
        except:
            # second trying 'ipfs swarm connect' with all of this peer's previously used multiaddresses
            for addr in self.known_multiaddrs:
                #ipfs.swarm.connect(addr + "/ipfs/" + self.id)
                proc = Popen(['ipfs', 'swarm', 'connect', addr[0] +
                             "/ipfs/" + self.id], stdout=PIPE)
                proc.wait()

                if proc.stdout.readline()[-8:-1].decode() == 'success':
                    self.remember_multiaddrs()
                    return True
            # if we still haven't found him, try 'ipfs routing findpeer ' one more time
            try:
                response = ipfs_api.find_peer(self.id)
                if(len(response.get("Responses")[0].get("Addrs")) > 0):
                    self.remember_multiaddrs()
                    return True
                else:
                    return False
            except:
                return False

    def check_connection(self):
        """Starts a new thread to try to connect to this peer,
        if that thread isn't already running."""
        if not self.connection_checker or not self.connection_checker.is_alive():
            self.connection_checker = Thread(target=self.try_to_connect, args=())
            self.connection_checker.start()


contacts = list()

try:
    filereader = open(os.path.join(lns_dir, "config"), "r")
    lines = filereader.readlines()
    filereader.close()
    for line in lines:
        contacts.append(Node(line))
except:
    filereader = open(os.path.join(lns_dir, "config"), "w+")
    filereader.close()


def save_contacts():
    """Saves the list of contacts to the config file"""
    filereader = open(os.path.join(lns_dir, "config"), "w+")
    for contact in contacts:
        filereader.write(contact.to_serial() + "\n")
    filereader.close()


def lookup_contact(name):
    for contact in contacts:
        if contact.name == name:
            return contact.id


lookupcontact = lookup_contact
LookupContact = lookup_contact
lookupContact = lookup_contact


def add_contact(id, name):
    if name == "":
        name = id
    newcontact = Node(id, name)
    contacts.append(newcontact)
    save_contacts()
    return newcontact


addcontact = add_contact
addContact = add_contact


def get_contact(id):
    """Parameters:
        id: either the name or IPFS ID of the contact to retrieve"""
    for contact in contacts:
        if id == contact.id or id == contact.name:
            return contact


def remove_contact(id, name):
    for contact in contacts:
        if contact.id == id and contact.name == name:
            contacts.remove(contact)
            break

    save_contacts()
