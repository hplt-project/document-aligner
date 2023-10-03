FROM ubuntu:latest as builder
RUN apt-get update \
 && apt-get install -y \
      libboost-program-options-dev \
      libboost-test-dev \
      libicu-dev \
      zlib1g-dev \
      cmake \
      build-essential

COPY . /root/

RUN mkdir /root/build \
 && cd /root/build \
 && cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo \
 && make -j docalign docjoin

FROM ubuntu:latest as runner
COPY --from=builder /root/build/bin/* /usr/local/bin/
