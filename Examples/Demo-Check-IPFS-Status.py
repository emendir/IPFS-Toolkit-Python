import ipfs_api  # import ipfs_api


try:
    # check if IPFS is running, wait max 5 seconds in case it is currently starting up
    ipfs_api.wait_till_ipfs_is_running(5)
except TimeoutError:    # if IPFS isn't runn
    print("IPFS isn't running, trying to run it myself...")
    ipfs_api.try_run_ipfs()  # try to run the IPFS daemon
    if not ipfs_api.is_ipfs_running():   # check if IPFS is running
        raise Exception("Houston, we have a problem here.")
print("IPFS is running!")
