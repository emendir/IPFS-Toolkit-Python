FROM emendir/systemd-ipfs:24.04
COPY *.py /opt/IPFS-Toolkit/
COPY src /opt/IPFS-Toolkit/src
COPY ReadMe.md /opt/IPFS-Toolkit/
COPY requirements.txt /opt/IPFS-Toolkit/
COPY tests/docker_script.py /opt/IPFS-Toolkit
RUN python3 -m pip install --break-system-packages /opt/IPFS-Toolkit

# docker build -t emendir/ipfs-toolkit .

# docker run --privileged emendir/ipfs-toolkit
