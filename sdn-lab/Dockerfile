# SDN Lab — minimal, fast build
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    git gcc python3-dev python3-pip python3-setuptools \
    libffi-dev libssl-dev libxml2-dev libxslt1-dev zlib1g-dev \
    curl wget vim sudo net-tools iproute2 iputils-ping \
    iperf tshark \
    openvswitch-switch openvswitch-common \
    mininet \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install ryu==4.34

COPY scripts/patch_ryu.py /tmp/patch_ryu.py
RUN python3 /tmp/patch_ryu.py && rm /tmp/patch_ryu.py

RUN ryu-manager --version

COPY app/ /root/lab/app/
COPY topo/ /root/lab/topo/
RUN mkdir -p /root/lab/output

COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /root/lab
ENTRYPOINT ["/entrypoint.sh"]
