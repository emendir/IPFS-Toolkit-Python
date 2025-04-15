# import inspect
try:
    pass
except:
    pass


class DataTransmissionError(Exception):
    """Is called when a fatal failure occurs during data transmission."""

    def __init__(self, message: str = "Failed to transmit the requested data to the specified peer."):
        self.message = message

    def __str__(self):
        return self.message


class PeerNotFound(Exception):
    """Is called when a function can't proceed because the desired IPFS peer
    can't be found on the internet. Simply trying again sometimes solves this.
    """

    def __init__(self, message: str = "Could not find the specified peer on the IPFS network. Perhaps try again."):
        self.message = message

    def __str__(self):
        return self.message


class InvalidPeer(Exception):
    """Is called when an invalid IPFS peer ID is provided."""

    def __init__(self, message: str = "The specified IPFS peer ID is invalid."):
        self.message = message

    def __str__(self):
        return self.message


class CommunicationTimeout(Exception):
    """Is called when a timeout is reached while trying to communicate with a
    peer.
    """

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class ConvListenTimeout(Exception):
    """Is called when one of the `.listen*` functions of a `Conversation`
    object yields no results. 
    """

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class UnreadableReply(Exception):
    """Is called when a corrupted response is received from a peer while
    communicating.
    """

    def __init__(self, message: str = "Received data that we couldn't read."):
        self.message = message

    def __str__(self):
        return self.message


class IPFS_Error(Exception):
    """A generic error that arises from IPFS itself or our interaction with it.
    """

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message
