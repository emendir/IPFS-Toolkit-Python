
FROM emendir/systemd-ipfs:24.04
COPY *.py /opt/IPFS-Toolkit/
COPY src /opt/IPFS-Toolkit/src
COPY ReadMe.md /opt/IPFS-Toolkit/
COPY requirements.txt /opt/IPFS-Toolkit/
COPY pyproject.toml /opt/IPFS-Toolkit/
COPY tests/ipfs_toolkit_docker/python_packages/ /opt/python_packages/


# RUN for python_package in /opt/python_packages/*; do pip install --break-system-packages --root-user-action ignore "$python_package"; done
RUN python3 -m pip install --break-system-packages /opt/IPFS-Toolkit
RUN python3 -m pip install --break-system-packages /opt/IPFS-Toolkit/src/ipfs_tk


# disable ipfs systemd service when testing with libkubo
# RUN systemctl disable ipfs

COPY Examples/ /opt/IPFS-Toolkit/Examples
COPY tests/docker_script.py /opt/IPFS-Toolkit

# docker build -t emendir/ipfs-toolkit .

# docker run -it --privileged emendir/ipfs-toolkit
