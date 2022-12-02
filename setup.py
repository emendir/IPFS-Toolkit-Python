

import setuptools
import os
import sys
sys.path.append(os.path.dirname(__file__))
if True:    # just to sto my IDE's script formatter moving the following import to the start of the script
    from __project__ import project_name, version
with open(os.path.join(os.path.dirname(__file__), "ReadMe.md"), "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name=project_name,
    version=version,
    author="emendir",
    description="A set of tools  for working with IPFS in Python: a programmer-friendly API wrapper, P2P data-transmission machinery, and accelerated connections to known peers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://ipfs.io/ipns/k2k4r8nismm5mmgrox2fci816xvj4l4cudnuc55gkfoealjuiaexbsup#IPFS-Toolkit",

    project_urls={
        # "Source Code on IPNS": "https://ipfs.io/ipns/k2k4r8k7h909zdodsvbxe32sahpfdkqcqqn1npblummw4df6iv7dj5xh",
        "Github": "https://github.com/emendir/IPFS-Toolkit-Python",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    py_modules=['IPFS_API', 'IPFS_DataTransmission', 'IPFS_LNS', 'IPFS_CLI', 'Errors'],
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
    install_requires=['multiaddr', 'appdirs', 'idna', 'httpcore', 'httpx', 'requests', 'varint'],
)
