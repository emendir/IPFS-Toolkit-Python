import appdirs
import os
import os.path
import json
import ipfshttpclient2 as ipfshttpclient
from subprocess import Popen, PIPE

ipfs = ipfshttpclient.client.Client()
ipfs_dir = os.path.join(appdirs.user_data_dir(), "IPFS")
lns_dir = os.path.join(appdirs.user_data_dir(), "IPFS", "LNS")

if not os.path.exists(ipfs_dir):
    os.makedirs(ipfs_dir)

if not os.path.exists(lns_dir):
    os.makedirs(lns_dir)

class Node:
    known_multiaddrs = list()
    def __init__(self, id, name = "", known_multiaddrs = list()):
        if name == "":
            self.id, self.name, self.known_multiaddrs = json.loads(id)
        else:
            self.id = id
            self.name = name
            self.known_multiaddrs = known_multiaddrs


    def ToSerial(self):
        return json.dumps([self.id, self.name, self.known_multiaddrs])

    def RememberMultiaddrs(self):
        multiaddrs = ipfs.dht.findpeer(self.id).get("Responses")[0].get("Addrs")
        edited = False
        for addr in multiaddrs:
            if not addr in self.known_multiaddrs and not "/ip6/::" in addr and not "/ip4/192.168" in addr and not "/ip4/127.0" in addr:
                self.known_multiaddrs.insert(0, addr)
                edited = True
        if edited:
            SaveContacts()

    def TryToConnect(self):
        # first trying 'ipfs dht findpeer ...'
        try:
            response = ipfs.dht.findpeer(self.id)
            if(len(response.get("Responses")[0].get("Addrs"))> 0):  # if connections succeeds
                self.RememberMultiaddrs()
                return True
        except:
            # second trying 'ipfs swarm connect' with all of this peer's previously used multiaddresses
            for addr in self.known_multiaddrs:
                #ipfs.swarm.connect(addr + "/ipfs/" + self.id)
                proc = Popen(['ipfs', 'swarm', 'connect', addr + "/ipfs/" + self.id], stdout=PIPE)
                proc.wait()

                if proc.stdout.readline()[-8:-1].decode() == 'success':
                    self.RememberMultiaddrs()
                    return True
            # if we still haven't found him, try 'ipfs dht findpeer ' one more time
            try:
                response = ipfs.dht.findpeer(self.id)
                if(len(response.get("Responses")[0].get("Addrs"))> 0):
                    self.RememberMultiaddrs()
                    return True
                else:
                    return False
            except:
                return False

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

def SaveContacts():
    """Saves the list of contacts to the config file"""
    filereader = open(os.path.join(lns_dir, "config"), "w+")
    for contact in contacts:
        filereader.write(contact.ToSerial() + "\n")
    filereader.close()

def LookUpContact(name):
    for contact in contacts:
        if contact.name == name:
            return contact.id
lookupcontact = LookUpContact
LookupContact = LookUpContact
lookupContact = LookUpContact
def AddContact(id, name):
    newcontact = Node(id, name)
    contacts.append(newcontact)
    SaveContacts()
    return newcontact


addcontact = AddContact
addContact = AddContact

def GetContact(id):
    """Parameters:
        id: either the name or IPFS ID of the contact to retrieve"""
    for contact in contacts:
        if id == contact.id or id == contact.name:
            return contact

def RemoveContact(id, name):
    for contact in contacts:
        if contact.id == id and contact.name == name:
            contacts.remove(contact)
            break

    SaveContacts()
