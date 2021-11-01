import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="IPFS-Toolkit",
    version="0.0.6",
    author="emendir",
    description="A set of tools  for working with IPFS in Python: a programmer-friendly API wrapper, P2P data-transmission machinery, and accelerated connections to known peers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://ipfs.io/ipns/k2k4r8k7h909zdodsvbxe32sahpfdkqcqqn1npblummw4df6iv7dj5xh",
    project_urls={
        "IPNS": "https://ipfs.io/ipns/k2k4r8k7h909zdodsvbxe32sahpfdkqcqqn1npblummw4df6iv7dj5xh",
        "Github": "https://github.com/emendir/IPFS-Toolkit-Python",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    py_modules = ['IPFS_API', 'IPFS_DataTransmission', 'IPFS_LNS'],
    install_requires = ['multiaddr', 'appdirs'],
)
