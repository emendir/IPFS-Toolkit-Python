## This is a module that enables the user to transmit and receive transmissions of data over the Interplanetary File System's P2P network (libp2p).
## To use it you must have IPFS running on your computer.

## This module is based on a modification of NetTerm that uses TCP. NetTerm is originally made to use UDP communication.
## This module is therefore a rather inefficient way of transmitting data, and it isn't as reliable as the UDP version.

## This module was rather hurridly put together and not all the comments will be accurate.
## It therefore still needs to be polished off.
## It's main functionality (transmitting data over the IPFS Network have been properly tested, though)

## Configure IPFS to enable all this:
## ipfs config --json Experimental.Libp2pStreamMounting true

## TODO:
##      terminate Listeners (currently not working due to TCP sockets)
##      handle interrupted communication
##      get rid of the delay periods in Transmission. Why are they necessary in TCP? I didn't need them in the UDP Version

import socket
import threading
from threading import Thread
import _thread
import multiprocessing
from datetime import datetime
import time
import traceback
from datetime import datetime
import os
from inspect import signature
import traceback
import copy

from IPFS_API import *
import IPFS_API
IPFS_API.Start()


# -------------- Settings ---------------------------------------------------------------------------------------------------
print_log = True # whether or not to print debug in output terminal

delay_1 = 0.05
delay_2 = 0.05

def_buffer_size = 1024  # the communication buffer size
free_sending_ports = [(x, False) for x in range(20001, 20500)]

# -------------- User Functions ----------------------------------------------------------------------------------------------
# Transmits a bytearray of any length to the specified host.
# Returns a transmitter object so that the status of the transmission can be monitored
def TransmitData(data, peerID, listener_name, buffer_size = def_buffer_size):
    """
    Transmits the input data (a bytearray of any length) to the computer with the specified network address.

    Usage:
        transmitter = Send("data to transmit".encode("utf-8"), "Qm123456789", "applicationNo2", 2048)    # transmits "data to transmit" to the computer with the Peer ID "Qm123456789", for the IPFS_DataTransmission listener called "applicationNo2" at a buffersize of 1024 bytes

    Parameters:
        bytearray data: the data to be transmitted to the receiver
        string peerID: the IPFS peer ID of [the recipient computer to send the data to]
        string listener_name: the name of the IPFS-Data-Transmission-Listener instance running on the recipient computer to send the data to (allows distinguishing multiple IPFS-Data-Transmission-Listeners running on the same computer for different applications)
        int buffer_size: the size in bytes of the buffers (data packets which the trnsmitteddata is divided up into) (default 1024 bytes)

    Returns:
        Transmitter transmitter: the object that contains all the machinery used to transmit the data to the receiver, from which the transmission status will in the future be able to get called from
    """
    return Transmitter(data, peerID, listener_name, buffer_size)

# Sets itself up to receive data transmissions, transmitted by the sender using the TransmitData function.
# Returns the Listener object so that receiving the data transmissions can be stopped by calling listener.Terminate().
def ListenForTransmissions(listener_name, eventhandler):
    """
    Listens for incoming transmission requests (senders requesting to transmit data to us) and sets up the machinery needed to receive those transmissions.

    Usage:
        def OnReceive(data, sender_peerID):
            print("Received data from  " + sender_peerID)
            print(data.decode("utf-8"))

        # listening with a Listener-Name of "applicationNo2"
        listener = ReceiveTransmissions("applicationNo2", OnReceive)

        # When we no longer want to receive any transmissions:
        listener.Terminate()

    Parameters:
        string listener_name: the name of this TransmissionListener (chosen by user, allows distinguishing multiple IPFS-Data-Transmission-Listeners running on the same computer for different applications)
        function(bytearray data, string peerID) eventhandler: the function that should be called when a transmission of data is received
    """
    # This function itself is called to process the transmission request buffer sent by the transmission sender.
    def ReceiveTransmissionRequests(data, addr):
        if print_log:
            print("processing transmission request...")
        # decoding the transission request buffer
        try:
            # Performing buffer integrity check
            integrity_byte = data[0]
            data = data[1:]
            sum = 0
            for byte in data:
                sum+= byte
                if sum > 65000:# if the sum is reaching the upper limit of an unsigned 16-bit integer
                    sum = sum%256   # reduce the sum to its modulus256 so that the calculation above doesn't take too much processing power in later iterations of this for loop
            # if the integrity byte doesn't match the buffer, exit the function ignoring the buffer
            if sum%256 != integrity_byte:
                if print_log:
                    print("Received a buffer with a non-matching integrity buffer")
                return

            index = data.index(bytearray([255]))
            peerID = data[0:index].decode()
            data = data[index+1:]

            index = data.index(bytearray([0]))
            sender_port = FromB255No0s(data[0:index])
            data = data[index+1:]

            buffer_size = FromB255No0s(data)

            return TransmissionListener(peerID, sender_port, buffer_size, eventhandler)

        except Exception as e:
            print("")
            print("Exception in NetTerm.ReceiveTransmissions.ReceiveTransmissionRequests()")
            print("----------------------------------------------------")
            traceback.print_exc() # printing stack trace
            print("----------------------------------------------------")
            print("")
            print(e)
            print("Could not decode transmission request.")



    request_listener = Listener2(ReceiveTransmissionRequests, 0, def_buffer_size)
    port = request_listener.port
    CreateListeningConnection(listener_name, port)

    if print_log:
        print("Listening for incoming transmission requests on port", port)

    return request_listener







connections_send = list()
connections_listen = list()
def CreateSendingConnection(peerID, protocol):
    i = 0
    for port in free_sending_ports:
        if port[1] == False:
            break
        i+=1
    port = free_sending_ports[i][0]
    free_sending_ports[i] = (port, True)
    try:
        ForwardFromPortToPeer(protocol, port, peerID)
        print(f"forwarding \"{protocol}\" from {port} to {peerID}")
    except Exception as e:
        try:
            IPFS_API.ClosePortForwarding(protocol="/x/"+protocol)
            IPFS_API.ClosePortForwarding(listenaddress = f"/ip4/127.0.0.1/tcp/{port}")
            ForwardFromPortToPeer(protocol, port, peerID)
        except:
            print("")
            print("Exception in NetTerm.ReceiveTransmissions.ReceiveTransmissionRequests()")
            print("----------------------------------------------------")
            traceback.print_exc() # printing stack trace
            print("----------------------------------------------------")
            print("")
            print(e)
            print("Error registering sending connection to IPFS")
    connections_send.append((protocol, port, peerID))
    print(port)
    return port

def CreateListeningConnection(protocol, port):
    try:
        ListenOnPort(protocol, port)
        print(f"listening for \"{protocol}\" on {port}")
    except Exception as e:
        IPFS_API.ClosePortForwarding(listenaddress = f"/ip4/127.0.0.1/tcp/{port}")
        IPFS_API.ClosePortForwarding(protocol="/x/"+protocol)
        try:
            ListenOnPort(protocol, port)
        except:
            print(f"listening for \"{protocol}\" on {port}")
            print("")
            print("Exception in NetTerm.ReceiveTransmissions.ReceiveTransmissionRequests()")
            print("----------------------------------------------------")
            traceback.print_exc() # printing stack trace
            print("----------------------------------------------------")
            print("")
            print(e)
            print("Error registering sending connection to IPFS")
    connections_listen.append((protocol, port))
    return port

def CloseSendingConnection(peerID, protocol):
    IPFS_API.ClosePortForwarding(targetaddress="/p2p/"+peerID, protocol="/x/"+protocol)
    i = 0
    for port in free_sending_ports:
        if port[1] == True:
            break
        i+=1
    port = free_sending_ports[i][0]
    free_sending_ports[i] = (port, True)
def CloseListeningConnection(protocol, port):
    IPFS_API.ClosePortForwarding(protocol="/x/"+protocol, targetaddress = f"/ip4/127.0.0.1/tcp/{port}")

def ListenToBuffers(eventhandler, port = 0, buffer_size = def_buffer_size, monitoring_interval = 5, status_eventhandler = None):
    return Listener(eventhandler, port, buffer_size, monitoring_interval, status_eventhandler)


class Listener(threading.Thread):
    """
    Listens on the specified port, forwarding all data buffers received to the provided eventhandler.

    Usage:
        # Function to process the received data buffers
        def eventhandler(data, sender_peerID):
            print("Received data from  " + sender_peerID)
            print(data.decode("utf-8"))

        listener = Listener(eventhandler, 0, 2048)   # start listening to incoming buffers on an automatically assigned port (that's what the 0 means)
        port = listener.port    # retrieve the automatically assigned port

        # Once finished and listening on that port should be stopped:
        listener.Terminate()

    Parameters:
        function(bytearray data, string sender_peerIDess) eventhandler: the eventhandler that should be called when a data buffer is received
        int port (optional, auto-assigned by OS if not specified): the port on which to listen for incoming data buffers
        int buffer_size (optional, default value 1024): the maximum size of buffers in bytes which this port should be able to receive
    """
    port = 0
    eventhandler = None
    buffer_size = def_buffer_size
    terminate = False
    sock = None
    last_time_recv = datetime.utcnow()
    def __init__(self, eventhandler, port = 0, buffer_size = def_buffer_size, monitoring_interval = 5, status_eventhandler = None):
        threading.Thread.__init__(self)
        self.port = port

        self.eventhandler = eventhandler
        self.buffer_size = buffer_size

        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)      # For UDP

        self.sock.bind(("127.0.0.1", self.port))
        self.port = self.sock.getsockname()[1]   # in case it had been 0 (requesting automatic port assiggnent)

        if status_eventhandler != None:
            self.status_eventhandler = status_eventhandler
            self.monitoring_interval = monitoring_interval
            self.last_time_recv = datetime.utcnow()
            self.status_monitor_thread = _thread.start_new_thread(self.StatusMonitor, ())

        self.start()



        if print_log:
            print("Created listener.")


    def run(self):
        self.sock.listen(1)
        conn, ip_addr = self.sock.accept()
        print("connected to somebody")

        while True:
            data = conn.recv(self.buffer_size)
            self.last_time_recv = datetime.utcnow()
            if(self.terminate == True):
                break
            if not data: break

            ev = Thread(target = self.eventhandler, args = (data, ip_addr))
            ev.start()

        conn.close()
        self.sock.close()
        CloseListeningConnection(str(self.port), self.port)
        if print_log:
            print("Closed listener.")

    def StatusMonitor(self):

        while(True):
            if self.terminate:
                break
            time.sleep(self.monitoring_interval/3)
            if(datetime.utcnow() - self.last_time_recv).total_seconds() > self.monitoring_interval:
                self.status_eventhandler((datetime.utcnow() - self.last_time_recv).total_seconds())


    # thread =  multiprocessing.Process(target = ListenIndefinately, args= ())
    # thread.start()
    #thread = _thread.start_new_thread(ListenIndefinately,())

    #return thread, used_port

    def Terminate(self):
        self.terminate = True   # marking the terminate flag as true
        self.sock.close()
        #SendBuffer(bytearray([0]),"",self.port) # to make the listener's buffer receiving while loop move forwards so that it realises it has o stop


class Listener2(threading.Thread):
    """
    Listener for TransmissionRequests
    Listens on the specified port, forwarding all data buffers received to the provided eventhandler.

    Usage:
        # Function to process the received data buffers
        def eventhandler(data, sender_peerID):
            print("Received data from  " + sender_peerID)
            print(data.decode("utf-8"))

        listener = Listener(eventhandler, 0, 2048)   # start listening to incoming buffers on an automatically assigned port (that's what the 0 means)
        port = listener.port    # retrieve the automatically assigned port

        # Once finished and listening on that port should be stopped:
        listener.Terminate()

    Parameters:
        function(bytearray data, string sender_peerIDess) eventhandler: the eventhandler that should be called when a data buffer is received
        int port (optional, auto-assigned by OS if not specified): the port on which to listen for incoming data buffers
        int buffer_size (optional, default value 1024): the maximum size of buffers in bytes which this port should be able to receive
    """
    port = 0
    eventhandler = None
    buffer_size = def_buffer_size
    terminate = False
    sock = None
    def __init__(self, eventhandler, port = 0, buffer_size = def_buffer_size):
        threading.Thread.__init__(self)
        self.port = port
        self.eventhandler = eventhandler
        self.buffer_size = buffer_size

        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)      # For UDP

        self.sock.bind(("127.0.0.1", self.port))
        self.port = self.sock.getsockname()[1]   # in case it had been 0 (requesting automatic port assiggnent)
        self.start()



        if print_log:
            print("Created listener.")


    def run(self):
        print("connected to somebody")
        while True:
            self.sock.listen(1)
            conn, ip_addr = self.sock.accept()

            data = conn.recv(self.buffer_size)
            # ev =  multiprocessing.Process(target = eventhandler, args = (data, peerID))
            # ev.start()
            if(self.terminate == True):
                break
            if not data: break
            print("Received data")

            ev = Thread(target = self.eventhandler, args = (data, ip_addr))
            ev.start()
            conn.close()

            #_thread.start_new_thread(eventhandler, (data, peerID))
        self.sock.close()
        if print_log:
            print("Closed listener.")


    # thread =  multiprocessing.Process(target = ListenIndefinately, args= ())
    # thread.start()
    #thread = _thread.start_new_thread(ListenIndefinately,())

    #return thread, used_port

    def Terminate(self):
        self.terminate = True   # marking the terminate flag as true
        #SendBuffer(bytearray([0]),"",self.port) # to make the listener's buffer receiving while loop move forwards so that it realises it has o stop






class Transmitter:
    """
    Contains all the machinery needed for transmitting data in the form of a bytearray of any length to a network address.
    It works by dividing the data into buffers and sending those buffers to the receiver, who must have a TransmissionListener object running and listening on that address.
    This system is immune to the buffers getting muddled up in their order or getting lost in cyberspace on their way to the receiver.

    Usage:
        transmitter = Transmitter("data to transmit".encode("utf-8"), "127.0.0.1", 8888, 2048)    # transmits "data to transmit" to the computer 127.0.0.1:8888 at a buffersize of 1024 bytes

    Parameters:
        bytearray data: the data to be transmitted to the receiver
        string peerID: the IP address of [the recipient computer to send the data to]
        int port: the port on the recipient computer to send the data to (on which the TransmissionListener is listening for transmission requests)
        int buffer_size: the size in bytes of the buffers (data packets which the trnsmitteddata is divided up into) (default 1024 bytes)

    """

    data = ""
    peerID = ""
    buffer_size = 1024





    their_port = None

    listener = None
    our_port = 0
    transmission_started = False

    sent_buffers = list()   # list(buffer, buffer_No)

    transmission_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)




    def __init__(self, data, peerID, listener_name, buffer_size=def_buffer_size):
        self.data = data
        self.peerID = peerID
        self.listener_name = listener_name

        self.buffer_size = buffer_size
        if buffer_size < 23:
            buffer_size = 23




        self.listener = ListenToBuffers(self.TransmissionReplyListener, status_eventhandler = self.NoCommunication)
        if print_log:
            print(self.listener.port)
        self.our_port = self.listener.port
        CreateListeningConnection(str(self.our_port), self.our_port)

        # self.listener, self.our_port = ListenToBuffers(0, self.TransmissionReplyListener)

        # sending transmission request, telling the receiver our code for the transmission, our listening port on which they should send confirmation buffers, and the buffer size to use
        self.SendTransmissionRequest()


    def SendTransmissionRequest(self):
        # sending transmission request, telling the receiver our code for the transmission, our listening port on which they should send confirmation buffers, and the buffer size to use
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = CreateSendingConnection(self.peerID, self.listener_name)
        sock.connect(("127.0.0.1", port))
        sock.send(AddIntegrityByteToBuffer(IPFS_API.MyID().encode() + bytearray([255]) + ToB255No0s(self.our_port) + bytearray([0]) + ToB255No0s(self.buffer_size)))
        sock.close()
        if print_log:
            print("Sent transmission request.")

    def sendbuffer(self, buffer):
        # Adding an integrity byte that equals the sum of all the bytes in the buffer modulus 256
        # to be able to detect data corruption:
        try:
            self.transmission_socket.send(AddIntegrityByteToBuffer(buffer))
            return True
        except:
            if print_log:
                print("Communication to receiver broken down.")
            self.FinishedTransmission(False)
            return False



    # transmits the self.data as a series of buffers
    def Transmit(self):

        if print_log:
            print("Transmission started to", self.their_port)
        self.transmission_socket.connect(("127.0.0.1",  CreateSendingConnection(self.peerID, str(self.their_port))))
        position = 0
        buffer_No = 0
        time.sleep(delay_2)
        while position < len(self.data):
            buffer_metadata = ToB255No0s(buffer_No) + bytearray([0])

            buffer_content = self.data[position: position + (self.buffer_size - len(buffer_metadata) - 1)]  # -1 to make space for the integrity buffer that gets added by the SendBuffer function
            position += (self.buffer_size - len(buffer_metadata) - 1)

            buffer = buffer_metadata + buffer_content
            if not self.sendbuffer(buffer):
                return   # aborting transmission if communication breaks down
            self.sent_buffers.append((buffer_No, buffer))    # adding the buffer to the list of sent buffers, just in case we have to resend it
            buffer_No += 1
            time.sleep(delay_1)

        time.sleep(delay_2)
        # sending last buffer saying transmission is finished
        if self.sendbuffer("finished transmission".encode("utf-8")):    # if sending the buffer succeeds
            self.sent_buffers.append((buffer_No, "finished transmission".encode("utf-8")))    # adding the buffer to the list of sent buffers, just in case we have to resend it
            if print_log:
                print("sent all data to transmit")



    def WaitToStartTransmission(self, data):
        if print_log:
            print("Waiting to start transmission, received buffer...")

        # decoding the transission request buffer
        try:
            index = data.index(bytearray([0]))
            self.their_port = FromB255No0s(data[0:index])
            data = data[index+1:]

            content = data.decode("utf-8")
        except Exception as e:
            print("")
            print("Exception in NetTerm.Transmission.WaitToStartTransmission()")
            print("----------------------------------------------------")
            traceback.print_exc() # printing stack trace
            print("----------------------------------------------------")
            print("")
            print(e)
            print("could not decode buffer")
            return

        if content == "start transmission":
            self.transmission_started = True

            self.Transmit()
        else:
            if print_log:
                print("buffer wasn't a transmission start confirmation")
            if print_log:
                print(content)

    def ProcessConfirmationBuffer(self, data):
        if(data == "finished transmission".encode("utf-8")):
            if print_log:
                print("Listener finished receiving transmission.")
            self.FinishedTransmission()
            return

        index = data.index(bytearray([0]))
        buffer_No = FromB255No0s(data[0:index])
        data = data[index+1:]

        if(data) == "conf".encode("utf-8"):
            # remving buffer from self.sent_buffers
            index = 0
            found = False
            for buffer in self.sent_buffers:
                if buffer[0] == buffer_No:
                    found = True
                    break
                index += 1
            if found == True:
                self.sent_buffers.pop(index)
                if print_log:
                    print("received confirmation buffer and removed buffer from list", buffer_No)

                # if there are older unconfirmed buffers, resend those
                if(False and index > 0):
                    for i in range(index):
                        self.sendbuffer(self.sent_buffers[i][1])
                        if print_log:
                            print("Resent buffer", self.sent_buffers[i][0])
            else:
                if print_log:
                    print("received confirmation buffer but could not find buffer in list", buffer_No)
        elif(data == "resend".encode("utf-8")):
            for buffer in self.sent_buffers:
                if buffer[0] == buffer_No:
                    self.sendbuffer(buffer[1])
                    if print_log:

                        print("Resent buffer", buffer[0])
                    return
            if print_log:
                print("Could not find the buffer which was requested to be resent.")

        else:
            if print_log:
                print(data.decode("utf-8"))
            if print_log:
                print("config buffer with unexpected format")

    def TransmissionReplyListener(self, data, peerID):
        # Performing buffer integrity check
        integrity_byte = data[0]
        data = data[1:]
        sum = 0
        for byte in data:
            sum+= byte
            if sum > 65000:# if the sum is reaching the upper limit of an unsigned 16-bit integer
                sum = sum%256   # reduce the sum to its modulus256 so that the calculation above doesn't take too much processing power in later iterations of this for loop
        # if the integrity byte doesn't match the buffer, exit the function ignoring the buffer
        if sum%256 != integrity_byte:
            if print_log:
                print(data)
                print("Received a buffer with a non-matching integrity buffer")
            return

        if self.transmission_started:
            self.ProcessConfirmationBuffer(data)
        else:
            self.WaitToStartTransmission(data)

    resend_timeout_sec = 5
    close_timeout_sec = 15
    def NoCommunication(self, time_since_last):
        print("NO COMMUNICATION " + str(time_since_last))
        if(time_since_last > self.close_timeout_sec):
            print("Aborting data transmission due to no response from receiver.")
            self.FinishedTransmission(False)
        elif(time_since_last > self.resend_timeout_sec):
            if self.transmission_started:
                print("Resending all stored buffers due to no response from receiver.")
                for buffer in self.sent_buffers:
                    self.sendbuffer(buffer[1])
            else:
                print("Resending transmission request.")
                self.SendTransmissionRequest()

    def FinishedTransmission(self, succeeded = True):
        self.listener.Terminate()
        self.transmission_socket.close()
        CloseListeningConnection(str(self.our_port), self.our_port)
        CloseSendingConnection(self.peerID, self.listener_name)
        CloseSendingConnection(self.peerID, str(self.their_port))
        if print_log:
            if succeeded:
                print("Finished transmission.")
            else:
                print("Transmission failed.")



# Contains all the machinery needed for receiving a transmission.
class TransmissionListener:
    """
    Contains all the machinery needed for receiving a transmission of data in the form of a bytearray of any length over a network.
    It receives the data divided into buffers by the sender, who has a Transmitter object running and transmitting the data to us.
    This system is immune to the buffers getting muddled up in their order or getting lost in cyberspace on their way to the receiver.

    Usage:
        This class must be used within a larger piece of machinery for receiving transmissions. This class only handles the reception
        of a single transmission after the transmitter has alsready sent the transmission request.
        That transmission request (a single buffer) contains encoded in it the port and buffer size needed to create a TransmissionListener object.
        To learn how to use this class, see ReceiveTransmissions(port, eventhandler)

    Parameters:
        string peerID: the IP address of [the computer who wants to transmit data to s]
        int sender_port: the port on the sender computer to send our transmission status data to
        int buffer_size: the size in bytes of the buffers (data packets which the trnsmitteddata is divided up into) (default 1024 bytes)
        function(bytearray data, string sender_peerID): the user-defined eventhandler to receive the data transmitted once the the transmission is finished
    """

    peerID = None
    port = 0
    eventhandler= None
    buffer_size = 0






    sender_port = None

    transmission_finished = False
    buffers = list()
    lis_port = None
    trsm_lis_port = None
    buffer_size = None
    listener_thread = None

    trsm_replier = None
    def __init__(self, peerID, sender_port, buffer_size, eventhandler):
        self.peerID = peerID
        self.sender_port = sender_port
        self.buffer_size = buffer_size
        self.eventhandler = eventhandler


        # setting up listener for receiving and processing the transmission self.buffers
        self.listener_thread = ListenToBuffers(self.ProcessTransmissionBuffer, 0, self.buffer_size, status_eventhandler = self.NoCommunication)
        self.trsm_lis_port = self.listener_thread.port
        CreateListeningConnection(str(self.trsm_lis_port), self.trsm_lis_port)
        if print_log:
            print("Ready to receive transmission.")


        port = CreateSendingConnection(peerID, str(sender_port))
        print(port)
        self.trsm_replier = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.trsm_replier.connect(("127.0.0.1", port))
        # Telling sender we're ready to start receiving the transmission, telling him which self.port we're listening on
        self.sendbuffer(ToB255No0s(self.trsm_lis_port) + bytearray([0]) + "start transmission".encode("utf-8"))





    # function for easily replying to sender using the self.port and self.buffer_size they specified
    def sendbuffer(self, buffer):
        try:
            self.trsm_replier.send(AddIntegrityByteToBuffer(buffer))
        except:
            if print_log:
                print("Communication to transmitter has broken down")
            self.FinishedTransmission(False)

    # Processes the buffers received over the transmission
    def ProcessTransmissionBuffer(self, data, peerID):
        # Performing buffer integrity check
        integrity_byte = data[0]
        data = data[1:]
        sum = 0
        for byte in data:
            sum+= byte
            if sum > 65000:# if the sum is reaching the upper limit of an unsigned 16-bit integer
                sum = sum%256   # reduce the sum to its modulus256 so that the calculation above doesn't take too much processing power in later iterations of this for loop
        # if the integrity byte doesn't match the buffer, exit the function ignoring the buffer
        if sum%256 != integrity_byte:
            if print_log:
                print("Received a buffer with a non-matching integrity byte")
                print(data)
            return
        if print_log:
            print("received transmission buffer")
        # decoding the transission buffer
        if(data == "finished transmission".encode("utf-8")):
            if print_log:
                print("Sender finished transmission")
            self.transmission_finished = True
            missing_buffer_count = 0
            index = 0
            for buffer in self.buffers:
                if(buffer == bytearray()):
                    self.sendbuffer(ToB255No0s(index) + bytearray([0]) + "resend".encode("utf-8"))
                    if print_log:
                        print("Requested buffer", index, "to be resent")
                    missing_buffer_count+=1
                index += 1
            if(missing_buffer_count == 0):
                self.FinishedTransmission()

            return

        index = data.index(bytearray([0]))
        buffer_No = FromB255No0s(data[0:index])
        data = data[index+1:]

        content = data

        # Adding empty entries to the sorted buffer list if the list doesn't have an entry for this buffer yet
        while buffer_No >= len(self.buffers):
            self.buffers.append(bytearray())

        self.buffers[buffer_No] = content

        # sending confirmation buffer so that the sender knows we've received this buffer
        self.sendbuffer(ToB255No0s(buffer_No) + bytearray([0]) + "conf".encode("utf-8"))

        if self.transmission_finished:
            missing_buffer_count = 0
            index = 0
            for buffer in self.buffers:
                if(buffer == bytearray()):
                    missing_buffer_count+=1

            if(missing_buffer_count == 0):
                self.FinishedTransmission()
            return

    resend_timeout_sec = 5
    close_timeout_sec = 15
    def NoCommunication(self, time_since_last):
        print("NO COMMUNICATION " + str(time_since_last))
        if(time_since_last > self.close_timeout_sec):
            print("Aborting data transmission due to no response from receiver.")
            self.FinishedTransmission(False)
        elif(time_since_last > self.resend_timeout_sec):
            print("Resending transmission confirmation.")
            self.sendbuffer(ToB255No0s(self.trsm_lis_port) + bytearray([0]) + "start transmission".encode("utf-8"))

    def FinishedTransmission(self, succeeded = True):
        if succeeded:
            if print_log:
                print("Transmission finished.")
            self.sendbuffer("finished transmission".encode("utf-8"))
            data = bytearray()
            for buffer in self.buffers:
                data = data + buffer
            _thread.start_new_thread(self.eventhandler,(data, self.peerID))
        else:
            if print_log:
                print("Transmission failed.")
        CloseListeningConnection(str(self.trsm_lis_port), self.trsm_lis_port)
        CloseSendingConnection(self.peerID, str(self.sender_port))




        self.listener_thread.Terminate()
        self.trsm_replier.close()





def AddIntegrityByteToBuffer(buffer):
    # Adding an integrity byte that equals the sum of all the bytes in the buffer modulus 256
    # to be able to detect data corruption:
    sum = 0
    for byte in buffer:
        sum+= byte
        if sum > 65000:# if the sum is reaching the upper limit of an unsigned 16-bit integer
            sum = sum%256   # reduce the sum to its modulus256 so that the calculation above doesn't take too much processing power in later iterations of this for loop
    return bytearray([sum%256]) + buffer  # adding the integrity byte to the start of the buffer


# turns a base 10 integer into a base 255 integer in  the form of an array of bytes where each byte represents a digit, and where no byte has the value 0
def ToB255No0s(number):
    array = bytearray([])
    while(number > 0):
        array.insert(0, int(number%255 + 1)) # modulus + 1 in order to get a range of possible values from 1-256 instead of 0-255
        number -= number%255
        number = number / 255
    return array
def FromB255No0s(array):
    number = 0
    order = 1
    # for loop backwards through th ebytes in array
    i = len(array) - 1  # th eindex of the last byte in the array
    while(i >= 0):
        number = number + (array[i] - 1) * order    # byte - 1 to change the range from 1-266 to 0-255
        order = order * 255
        i = i - 1
    return number



# encoding bytearrays into strings and vice versa to work with JSON encoding
def StringToBytes(string):
    byts = bytearray([])
    while(len(string) > 0):
        byts.append(int(string[0:3]))
        string = string[3:]
    return bytearray(byts)
def BytesToString(bytes):
    string = ""
    for byte in bytes:
        stri = str(byte)
        while(len(stri) < 3):
            stri = "0" + stri
        string = string + stri
    return string
