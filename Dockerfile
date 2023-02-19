FROM emendir/ubuntu:latest
COPY *.py /opt/IPFS-Toolkit/
COPY ipfshttpclient2 /opt/IPFS-Toolkit/ipfshttpclient2
COPY ReadMe.md /opt/IPFS-Toolkit/
COPY tests/docker_script.py /opt/IPFS-Toolkit
RUN python3 -m pip install /opt/IPFS-Toolkit
# CMD /opt/init_ipfs.sh;python3 -c "from threading import Event;a = Event();a.wait()"
CMD /opt/init_ipfs.sh;python3 /opt/IPFS-Toolkit/docker_script.py


# docker build -t emendir/ipfs-toolkit .
