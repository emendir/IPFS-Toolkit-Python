import IPFS_DataTransmission#_old as IPFS_DataTransmission

data = "Hello IPFS World! New way of networking coming up. Can't wait to use it!".encode("utf-8")

# Uncomment the following two lines of code to set the data to send a file
with open("/home/elborth/Desktop/00.jpg", "rb") as conff:
    data = conff.read()

IPFS_DataTransmission.TransmitData(data, "12D3KooWQzQAs2tCuY6P9V3qaKKars17JpaLkvEaHi5RBsUXVj94", "test application")
