# ChangeLog IPFS-Toolkit Version 0.2.2 vs 0.1.X
A lot of improvements have been made since version 0.1.5, which unfortunately means some users may have to change their code where they used this library. Here is an overview of most of what is new to v0.2.2.

## IPFS_DataTransmission:
#### DataTransmission:
In IPFS_DataTransmission the transmission protocol which has so far been my schoolboy-style home-made buffer-management system has been replaced with the much more efficient [ZeroMQ](zeromq.org) protocol. This has lead to greater speed and greater reliability.
It has, however, simplified the Transmission so far that the `Transmitter` and `TransmissionListener` classes have been deprecated, the machinery now being contained entirely in the TransmitData function and a new `TransmissionListener` class. The new `TransmissionListener` is something else than the old one: This is the object that listens to incoming transmission requests, like the `FileTransmissionListener` and `ConversationListener` classes.
#### Failure Management:
All transmission functions, such as `TransmitData()`, `Conversation.Start()`, `Conversation.Say()` and `TransmitFile()` now return a boolean to indicate whether or not they were successful. You can also specify timeouts.

Example:

```python
# timeout_sec: connection attempt timeout, multiplied with the maximum number of retries will result in the total time required for a failed attempt
# max_retries: how often the transmission should be reattempted when the timeout is reached
if IPFS_DataTransmission.TransmitData(data, peerID, "test application",  timeout_sec=10, max_retries=3):
    print("Sent Data!!")
else:
    print("Failed to send data.")
```

In FileTransmission, this has lead to the instantiation of the `FileTransmitter` class not automatically starting the Transmission, which now has to be started with the `Start()` method.

#### Cleanup Methods:
`Conversations` have a `Close()` method to clean them up, `FileTransmitter`, `ConversationListener`, and `FileTransmissionListener` have `Terminate()` methods.


```Python
file_transmitter = FileTransmitter(filepath, peerID, others_req_listener, metadata, block_size)
success = file_transmitter.Start()
if success:
    print("File transmission started.")
```
Those of you who used the `IPFS_DataTransmission.TransmitFile()` in their code won't have to make any changes there.

#### Conversation.Listen():
IPFS_DataTransmission.Conversation has a new Listen() method: it allows you to block the calling thread as you wait for an incoming transmission. This can be used instead of or along with the now optional eventhandler paramater in the `Start()` method.

Example:
```python
conv = IPFS_DataTransmission.StartConversation(
    "test-con", peerID, "general_listener")#, OnMessageReceived)

conv.Say("Hello there!".encode('utf-8'))

data = conv.Listen(timeout=5)
if data:
    print("Received data: ", data)
else:
    print("Received no more messages after waiting 5 seconds.")
conv.Close()
```

#### FileTransmission Progress Callbacks:
You can finally add progress callback functions to FileTransmitters and FileTransmissionReceivers!
The FileTransmitter will give the callback the transmission progress as a value between 0 and 1, while the FileTransmissionReceiver also provides the sender's IPFS peerID, the filename and filesize.

Example Sender:
```python
def ProgressUpdate(progress):
    print(f"sending file ... {round(progress*100)}%")

ft = IPFS_DataTransmission.TransmitFile(
    filepath, peerID, "my_apps_filelistener", metadata, ProgressUpdate)
```
Example Receiver:
```python
def ReceivingFileProgress(peer, file, filesize, progress):
    """Eventhandler which reports progress updates while receiving a file."""
    print(f"Receiving a file '{file}' from {peer}. {progress}")

def OnDataReceived(peer, file, metadata):
    """Eventhandler which gets executed after a file has been received."""
    print(f"Received file '{file}' from {peer}")


file_receiver = IPFS_DataTransmission.ListenForFileTransmissions(
    "my_apps_filelistener", OnDataReceived, ReceivingFileProgress)
```

## IPFS_API
The client object from the `ipfshttpclient` module has been renamed from `ipfs` to `http_client`.
