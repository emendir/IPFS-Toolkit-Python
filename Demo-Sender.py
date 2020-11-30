import IPFS_DataTransmission#_old as IPFS_DataTransmission

data = "Hello IPFS World! New way of networking coming up. Can't wait to use it!".encode("utf-8")

# Uncomment the following two lines of code to set the data to send a file
# with open("PASTE YoUR PATH HERE", "rb") as conff:
#     data = conff.read()

IPFS_DataTransmission.TransmitData(data, "PASTE PEER ID HERE", "test application")
