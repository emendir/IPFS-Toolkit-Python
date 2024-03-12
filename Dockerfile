FROM emendir/systemd-ipfs:latest
COPY *.py /opt/IPFS-Toolkit/
COPY ipfshttpclient2 /opt/IPFS-Toolkit/ipfshttpclient2
COPY ReadMe.md /opt/IPFS-Toolkit/
COPY tests/docker_script.py /opt/IPFS-Toolkit
RUN python3 -m pip install /opt/IPFS-Toolkit

# docker build -t emendir/ipfs-toolkit .

# docker run --privileged emendir/ipfs-toolkit
