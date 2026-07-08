FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# System deps for compilation + runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    autoconf automake libtool pkg-config build-essential cmake git curl \
    flex bison libfl-dev libelf-dev libgc-dev \
    libboost-dev libboost-program-options-dev libboost-system-dev \
    libboost-thread-dev libboost-filesystem-dev libboost-iostreams-dev \
    libgmp-dev libjudy-dev libpcap-dev libssl-dev zlib1g-dev \
    libnanomsg-dev libtool-bin libxxhash-dev \
    python3 python3-dev python3-pip python3-setuptools \
    protobuf-compiler libprotobuf-dev libprotoc-dev \
    libgrpc++-dev protobuf-compiler-grpc thrift-compiler libthrift-dev \
    net-tools iproute2 iputils-ping iperf tcpdump vim sudo make \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir grpcio protobuf scapy psutil crcmod

# Build behavioral-model (simple_switch) - native ARM64
WORKDIR /tmp
RUN git clone --depth 1 --branch main https://github.com/p4lang/behavioral-model.git && \
    cd behavioral-model && ./autogen.sh && \
    ./configure --with-thrift --with-nanomsg CXXFLAGS="-Wno-error" && \
    make -j$(nproc) && make install && ldconfig && \
    cd /tmp && rm -rf behavioral-model

# Build p4c - native ARM64  
WORKDIR /tmp
RUN git clone --depth 1 --branch main https://github.com/p4lang/p4c.git && \
    cd p4c && git submodule update --init --recursive --depth 1 && \
    mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release -DENABLE_GTEST_GMOCK=OFF -DENABLE_TEST_TOOLS=OFF && \
    make -j$(nproc) && make install && ldconfig && \
    cd /tmp && rm -rf p4c

# Mininet
RUN apt-get update && apt-get install -y -qq --no-install-recommends mininet && \
    pip3 install mininet && rm -rf /var/lib/apt/lists/*

# Tutorials
COPY p4-tutorials/ /root/tutorials/

RUN p4c-bm2-ss --version 2>&1 | head -1 && \
    simple_switch --version 2>&1 | head -1 && \
    mn --version 2>&1 | head -1 && \
    echo "P4 NATIVE ARM64 Ready"

RUN echo 'export PYTHONPATH=/root/tutorials/utils:/root/tutorials/utils/p4runtime_lib:$PYTHONPATH' >> /root/.bashrc

WORKDIR /root/tutorials/exercises
ENTRYPOINT ["/bin/bash"]
