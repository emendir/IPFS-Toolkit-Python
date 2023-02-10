from ipfs_datatransmission import (
    resend_timeout_sec,
    close_timeout_sec,
    transmission_send_timeout_sec,
    transmission_request_max_retries,
    transmission_send_timeout_sec,
    transmission_receive_timeout_sec,
    def_buffer_size,
    def_block_size,
    transmit_data,
    listen_for_transmissions,
    TransmissionListener,
    start_conversation,
    listen_for_conversations,
    Conversation,
    ConversationListener,
    transmit_file,
    listen_for_file_transmissions,
    FileTransmitter,
    FileTransmissionReceiver,
    listen_to_buffers,
    listen_to_buffers_on_port,
    BufferSender,
    BufferReceiver,
    send_buffer_to_port
)
from termcolor import colored
print(colored("IPFS_DataTransmission: DEPRECATED: The IPFS_DataTransmission module has been renamed to ipfs_datatransmission to accord with PEP 8 naming conventions.", "yellow"))

# TODO: DEPRECATION WARNINGS


def TransmitData(
        data: bytes,
        peerID: str,
        req_lis_name: str,
        timeout_sec: int = transmission_send_timeout_sec,
        max_retries: int = transmission_request_max_retries):
    print(colored("IPFS_DataTransmission: DEPRECATED: This function (TransmitData) has been renamed to transmit_data to accord with PEP 8 naming conventions.", "yellow"))
    return transmit_data(
        data,
        peerID,
        req_lis_name,
        timeout_sec=timeout_sec,
        max_retries=max_retries)


def ListenForTransmissions(listener_name, eventhandler):
    print(colored("IPFS_DataTransmission: DEPRECATED: This function (ListenForTransmissions) has been renamed to listen_for_transmissions to accord with PEP 8 naming conventions.", "yellow"))
    return listen_for_transmissions(listener_name, eventhandler)


def StartConversation(conversation_name,
                      peerID,
                      others_req_listener,
                      data_received_eventhandler=None,
                      file_eventhandler=None,
                      file_progress_callback=None,
                      encryption_callbacks=None,
                      timeout_sec=transmission_send_timeout_sec,
                      max_retries=transmission_request_max_retries,
                      dir="."):
    print(colored("IPFS_DataTransmission: DEPRECATED: This function (StartConversation) has been renamed to start_conversation to accord with PEP 8 naming conventions.", "yellow"))
    return start_conversation(conversation_name,
                              peerID,
                              others_req_listener,
                              data_received_eventhandler=data_received_eventhandler,
                              file_eventhandler=file_eventhandler,
                              file_progress_callback=file_progress_callback,
                              encryption_callbacks=encryption_callbacks,
                              timeout_sec=timeout_sec,
                              max_retries=max_retries,
                              dir=dir)


def ListenForConversations(conv_name, eventhandler):
    print(colored("IPFS_DataTransmission: DEPRECATED: This function (ListenForConversations) has been renamed to listen_for_conversations to accord with PEP 8 naming conventions.", "yellow"))
    return listen_for_conversations(conv_name, eventhandler)


def TransmitFile(filepath,
                 peerID,
                 others_req_listener,
                 metadata=bytearray(),
                 progress_handler=None,
                 encryption_callbacks=None,
                 block_size=def_block_size,
                 transmission_send_timeout_sec=transmission_send_timeout_sec,
                 transmission_request_max_retries=transmission_request_max_retries
                 ):
    print(colored("IPFS_DataTransmission: DEPRECATED: This function (TransmitFile) has been renamed to transmit_file to accord with PEP 8 naming conventions.", "yellow"))
    return transmit_file(filepath,
                         peerID,
                         others_req_listener,
                         metadata=metadata,
                         progress_handler=progress_handler,
                         encryption_callbacks=encryption_callbacks,
                         block_size=block_size,
                         transmission_send_timeout_sec=transmission_send_timeout_sec,
                         transmission_request_max_retries=transmission_request_max_retries
                         )


def ListenForFileTransmissions(listener_name,
                               eventhandler,
                               progress_handler=None,
                               dir=".",
                               encryption_callbacks=None):
    print(colored("IPFS_DataTransmission: DEPRECATED: This function (ListenForFileTransmissions) has been renamed to listen_for_file_transmissions to accord with PEP 8 naming conventions.", "yellow"))
    return listen_for_file_transmissions(listener_name,
                                         eventhandler,
                                         progress_handler=progress_handler,
                                         dir=dir,
                                         encryption_callbacks=encryption_callbacks)


def SendBufferToPort(buffer, addr, port):
    print(colored("IPFS_DataTransmission: DEPRECATED: This function (SendBufferToPort) has been renamed to send_buffer_to_port to accord with PEP 8 naming conventions.", "yellow"))
    return send_buffer_to_port(buffer, addr, port)


def ListenToBuffersOnPort(eventhandler,
                          port=0,
                          buffer_size=def_buffer_size,
                          monitoring_interval=2,
                          status_eventhandler=None):
    print(colored("IPFS_DataTransmission: DEPRECATED: This function (ListenToBuffersOnPort) has been renamed to listen_to_buffers_on_port to accord with PEP 8 naming conventions.", "yellow"))
    return listen_to_buffers_on_port(eventhandler,
                                     port=port,
                                     buffer_size=buffer_size,
                                     monitoring_interval=monitoring_interval,
                                     status_eventhandler=status_eventhandler)


def ListenToBuffers(eventhandler,
                    proto,
                    buffer_size=def_buffer_size,
                    monitoring_interval=2,
                    status_eventhandler=None,
                    eventhandlers_on_new_threads=True):
    print(colored("IPFS_DataTransmission: DEPRECATED: This function (ListenToBuffersConversation.) has been renamed to listen_to_buffers to accord with PEP 8 naming conventions.", "yellow"))
    return listen_to_buffers(eventhandler,
                             proto,
                             buffer_size=buffer_size,
                             monitoring_interval=monitoring_interval,
                             status_eventhandler=status_eventhandler,
                             eventhandlers_on_new_threads=eventhandlers_on_new_threads)


"""Methods for classes:"""


def __ConversationStart(self,
                        conversation_name,
                        peerID,
                        others_req_listener,
                        data_received_eventhandler=None,
                        file_eventhandler=None,
                        file_progress_callback=None,
                        encryption_callbacks=None,
                        transmission_send_timeout_sec=transmission_send_timeout_sec,
                        transmission_request_max_retries=transmission_request_max_retries,
                        dir="."
                        ):
    print(colored("IPFS_DataTransmission.Conversation: DEPRECATED: This function (Start) has been renamed to start to accord with PEP 8 naming conventions.", "yellow"))
    return self.start(conversation_name,
                      peerID,
                      others_req_listener,
                      data_received_eventhandler=data_received_eventhandler,
                      file_eventhandler=file_eventhandler,
                      file_progress_callback=file_progress_callback,
                      encryption_callbacks=encryption_callbacks,
                      transmission_send_timeout_sec=transmission_send_timeout_sec,
                      transmission_request_max_retries=transmission_request_max_retries,
                      dir=dir
                      )


def __ConversationJoin(self,
                       conversation_name,
                       peerID,
                       others_trsm_listener,
                       data_received_eventhandler=None,
                       file_eventhandler=None,
                       file_progress_callback=None,
                       encryption_callbacks=None,
                       transmission_send_timeout_sec=transmission_send_timeout_sec,
                       transmission_request_max_retries=transmission_request_max_retries,
                       dir="."):
    print(colored("IPFS_DataTransmission.Conversation: DEPRECATED: This function (Join) has been renamed to join to accord with PEP 8 naming conventions.", "yellow"))
    self.join(conversation_name,
              peerID,
              others_trsm_listener,
              data_received_eventhandler=data_received_eventhandler,
              file_eventhandler=file_eventhandler,
              file_progress_callback=file_progress_callback,
              encryption_callbacks=encryption_callbacks,
              transmission_send_timeout_sec=transmission_send_timeout_sec,
              transmission_request_max_retries=transmission_request_max_retries,
              dir=dir)


def __ConversationListen(self, timeout=None):
    print(colored("IPFS_DataTransmission.Conversation: DEPRECATED: This function (Listen) has been renamed to listen to accord with PEP 8 naming conventions.", "yellow"))
    return self.listen(timeout=None)


def __ConversationListenForFile(self, abs_timeout=None, no_coms_timeout=None, timeout_exception=False):
    print(colored("IPFS_DataTransmission.Conversation: DEPRECATED: This function (ListenForFile) has been renamed to listen_for_file to accord with PEP 8 naming conventions.", "yellow"))
    return self.listen_for_file(abs_timeout=None, no_coms_timeout=None, timeout_exception=False)


def __ConversationSay(self,
                      data,
                      timeout_sec=Conversation._transmission_send_timeout_sec,
                      max_retries=Conversation._transmission_request_max_retries
                      ):
    print(colored("IPFS_DataTransmission.Conversation: DEPRECATED: This function (Say) has been renamed to say to accord with PEP 8 naming conventions.", "yellow"))
    return self.say(
        data,
        timeout_sec=timeout_sec,
        max_retries=max_retries
    )


def __ConversationTransmitFile(self,
                               filepath,
                               metadata=bytearray(),
                               progress_handler=Conversation.file_progress_callback,
                               block_size=def_block_size,
                               transmission_send_timeout_sec=Conversation._transmission_send_timeout_sec,
                               transmission_request_max_retries=Conversation._transmission_request_max_retries
                               ):
    print(colored("IPFS_DataTransmission.Conversation: DEPRECATED: This function (TransmitFile) has been renamed to transmit_file to accord with PEP 8 naming conventions.", "yellow"))
    return self.transmit_file(
        filepath,
        metadata=metadata,
        progress_handler=progress_handler,
        block_size=block_size,
        transmission_send_timeout_sec=transmission_send_timeout_sec,
        transmission_request_max_retries=transmission_request_max_retries
    )


def __ConversationTerminate(self):
    print(colored("IPFS_DataTransmission.Conversation: DEPRECATED: This function (Terminate) has been renamed to terminate to accord with PEP 8 naming conventions.", "yellow"))
    return self.terminate()


def __ConversationClose(self):
    print(colored("IPFS_DataTransmission.Conversation: DEPRECATED: This function (Close) has been renamed to terminate to accord with PEP 8 naming conventions.", "yellow"))
    return self.terminate()


Conversation.Start = __ConversationStart
Conversation.Join = __ConversationJoin
Conversation.Listen = __ConversationListen
Conversation.ListenForFile = __ConversationListenForFile
Conversation.Say = __ConversationSay
Conversation.TransmitFile = __ConversationTransmitFile
Conversation.Terminate = __ConversationTerminate
Conversation.Close = __ConversationClose


def __FileTransmitterStart(self):
    print(colored("IPFS_DataTransmission.FileTransmitter: DEPRECATED: This function (Start) has been renamed to start to accord with PEP 8 naming conventions.", "yellow"))
    return self.start()


FileTransmitter.Start = __FileTransmitterStart
