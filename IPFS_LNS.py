import appdirs
import os
import os.path
import json

ipfs_dir = os.path.join(appdirs.user_data_dir(), "IPFS")
lns_dir = os.path.join(appdirs.user_data_dir(), "IPFS", "LNS")

if not os.path.exists(ipfs_dir):
    os.mkdir(ipfs_dir)

if not os.path.exists(lns_dir):
    os.mkdir(lns_dir)
    os.mkdir(lns_dir)

class Node:
    def __init__(self, id, name = ""):
        if name == "":
            self.id, self.name = json.loads(id)
        else:
            self.id = id
            self.name = name

    def ToSerial(self):
        return json.dumps([self.id, self.name])

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

def LookUpContact(name):
    for contact in contacts:
        if contact.name == name:
            return contact.id
lookupcontact = LookUpContact
LookupContact = LookUpContact
lookupContact = LookUpContact
def AddContact(id, name):
    filereader = open(os.path.join(lns_dir, "config"), "w+")
    newcontact = Node(id, name)
    contacts.append(newcontact)
    for contact in contacts:
        filereader.write(contact.ToSerial() + "\n")
    filereader.close()
addcontact = AddContact
addContact = AddContact
def RemoveContact(id, name):
    for contact in contacts:
        if contact.id == id and contact.name == name:
            contacts.remove(contact)
            break

    filereader = open(os.path.join(lns_dir, "config"), "w+")
    for contact in contacts:
        filereader.write(contact.ToSerial() + "\n")
    filereader.close()
