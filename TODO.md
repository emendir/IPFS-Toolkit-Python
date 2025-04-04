## Docs
- how to specify custom address for IPFS daemon interface
  - `PY_IPFS_HTTP_CLIENT_DEFAULT_ADDR=/dns/ipfs/tcp/5001/http`, 
  - `ipfs_api.ipfshttpclient.client.Client(addr="/dns/ipfs/tcp/5001/http")`

## API
- make parameter names more consistent, e.g. `timeout` & `timeout_sec`
- make ipfs_api.read() empty file work

## IPFS Peers:
- docs
- take care of ipfs_lns
- support using ipfs_cli
- timeout errors cleanup resources first
- add_peer=register_contact_event. Best function name?

## FileTransmission:
- abortion
- test blocksize upgrades

## DataTransmission:
- terminate properly on error (test it in conv properly, see if more needs to be done for FileTransission)
- include encryption parameters in transmit_data?


## ipfs_http_client
- write tests for all routing functionality
- write tests for all pubsub functionality
- pass kwargs

## Documentation
- improve ReadMe
- ipfs_cli: docs
- add more realistic encryption scenario to DataTransmission Encryption example


## Tests
verify docker container is new on build (cause we've disabled verbose output on docker build)

