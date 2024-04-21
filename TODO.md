# IPFS Peers:
- docs
- take care of ipfs_lns
- support using ipfs_cli
- timeout errors cleanup resources first
- add_peer=register_contact_event. Best function name?

# FileTransmission:
- abortion
- test blocksize upgrades

# DataTransmission:
- terminate properly on error (test it in conv properly, see if more needs to be done for FileTransission)
- include encryption parameters in transmit_data?

# ipfs_http_client
- migrate find_peer and find_providers from dht to routing
- write tests for all routing functionality
- write tests for all pubsub functionality
- pass kwargs

# Documentation
- improve ReadMe
- ipfs_cli: docs
- add more realistic encryption scenario to DataTransmission Encryption example


# Tests
verify docker container is new on build (cause we've disabled verbose output on docker build)

