import IPFS_DataTransmission


data = "Hello IPFS World! New way of networking coming up. Can't wait to use it!".encode("utf-8")
data = "Greetings from real laptoip to virtual macjhine".encode("utf-8")


# data = "Hi Markus!".encode("utf-8")


# Uncomment the following two lines of code to set the data to send a file
#with open("/home/yochanan/Music/Link to Music/Davy Jones  - Pirates of the Caribbean.mp3", "rb") as conff:
#    conff.position = 4194304
    #data = conff.read()

# tablet
peerID = "12D3KooWDTtukVdcjjiSkGQGUFtPVjYXY7RyJisTW59wFLst93zZ"
#VM
peerID = "12D3KooWEkcGRPJUYyb3P2pxes6jBpET9wzDrFXxfHX8CTwHq4YB"

#Lisa
#peerID="12D3KooWCTTQe1rSy25DvPSbfigJvtAhikq41qfgjAVziH6Vvv2Y"

# Elborth
peerID = "Qmcbjtfh5RfyFnrPk6uQ5EfhHzPQqPC1Vga7twguXSg2Pm"

peerID = "12D3KooWEkcGRPJUYyb3P2pxes6jBpET9wzDrFXxfHX8CTwHq4YB"

#Llearuin
peerID = "12D3KooWGKNuAQPyaYTDbeiWFN3S2SSTbxH74XCbJNdf7prG9qPE"

IPFS_DataTransmission.TransmitDataAwait(data, peerID, "test application")
print("Sent Data!!")

#Phone:
#IPFS_DataTransmission.TransmitData(data, "12D3KooWDk7EhH8yS5deVZWoEBLSr5LRYCFLtN2GkVDtqv5sn4d7", "test application")


#Sha'ul
#IPFS_DataTransmission.TransmitData(data, "QmZeWJNsvA1ZbfMHfwEAhmA57NiQJ1MZMcAuZ3KKfrFCPZ", "test application")

#Lisa
#IPFS_DataTransmission.TransmitData(data, "12D3KooWCTTQe1rSy25DvPSbfigJvtAhikq41qfgjAVziH6Vvv2Y", "test application")

#Ela
#IPFS_DataTransmission.TransmitData(data, "12D3KooWF2h7setsFBEEngccRjzDKzHcCMYiaX7AzwzmLBibQ46S", "test application")
# Markus
#IPFS_DataTransmission.TransmitData(data, "12D3KooWGSrrKUKb3CXtCSQtWLDMo2grZXRPfTAMCmmpXVXqPbdR", "test application")

# Lorenza
#IPFS_DataTransmission.TransmitData(data, "12D3KooWFZqHWFRKDtEAzQnWdGYXd5dg2N9vPyeHyq7UP92eNxuR", "test application")


# VM
#IPFS_DataTransmission.TransmitData(data, "QmNk3UYD6uYzEyebwjkaQzA3jAFT5q7DcvSJ8uiJCBki7j", "test application")
