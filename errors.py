class DataTransmissionError(Exception):
    def __init__(self, message: str = "Failed to transmit the requested data to the specified peer."):
        self.message = message

    def __str__(self):
        return self.message


class PeerNotFound(Exception):
    def __init__(self, message: str = "Could not find the specified peer on the IPFS network. Perhaps try again."):
        self.message = message

    def __str__(self):
        return self.message


class InvalidPeer(Exception):
    def __init__(self, message: str = "The specified IPFS peer ID is invalid."):
        self.message = message

    def __str__(self):
        return self.message


class CommunicationTimeout(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class ListenTimeout(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class UnreadableReply(Exception):
    def __init__(self, message: str = "Received data that we couldn't read."):
        self.message = message

    def __str__(self):
        return self.message


class IPFS_Error(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class Error(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message
