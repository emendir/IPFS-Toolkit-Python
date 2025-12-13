TRANSM_REQ_MAX_RETRIES = 3
TRANSM_SEND_TIMEOUT_SEC = 30
TRANSM_RECV_TIMEOUT_SEC = 30

BUFFER_SIZE = 2048  # the communication buffer size
# the size of the chunks into which files should be split before transmission
BLOCK_SIZE = 1048576  # 1MiB

sending_ports = [x for x in range(20001, 20500)]
