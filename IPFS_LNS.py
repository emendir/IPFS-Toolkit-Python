from ipfs_lns import (
    Node,
    save_contacts,
    lookup_contact,
    add_contact,
    get_contact,
    remove_contact
)
from termcolor import colored
print(colored("IPFS_LNS: DEPRECATED: The IPFS_LNS module has been renamed to ipfs_lns to accord with PEP 8 naming conventions.", "yellow"))


def SaveContacts():
    print(colored("IPFS_LNS: DEPRECATED: This function (SaveContacts) has been renamed to save_contacts to accord with PEP 8 naming conventions.", "yellow"))
    return save_contacts()


def LookupContact(name):
    print(colored("IPFS_LNS: DEPRECATED: This function (LookupContact) has been renamed to lookup_contact to accord with PEP 8 naming conventions.", "yellow"))
    return lookup_contact(name)


def AddContact(id, name):
    print(colored("IPFS_LNS: DEPRECATED: This function (AddContact) has been renamed to add_contact to accord with PEP 8 naming conventions.", "yellow"))
    return add_contact(id, name)


def GetContact(id):
    print(colored("IPFS_LNS: DEPRECATED: This function (GetContact) has been renamed to get_contact to accord with PEP 8 naming conventions.", "yellow"))
    return get_contact(id)


def RemoveContact(id, name):
    print(colored("IPFS_LNS: DEPRECATED: This function (RemoveContact) has been renamed to remove_contact to accord with PEP 8 naming conventions.", "yellow"))
    return remove_contact(id, name)
