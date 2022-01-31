FROM ubuntu:focal
MAINTAINER Ricardo González<correoricky@gmail.com>

ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USERNAME=ricardo
ARG GROUP=ricardo

# Avoid interactuation with installation of some package that needs the locale.
ENV TZ=Europe/Madrid
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install --no-install-recommends \
        build-essential \
        ccache \
        cmake \
        gdb \
        git \
        jq \
        libasio-dev \
        libssl-dev \
        libtinyxml2-dev \
        python3-pip \
        sudo \
        valgrind \
        vim \
        wget \
        wireshark \
    && yes yes | DEBIAN_FRONTEND=teletype dpkg-reconfigure wireshark-common \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN if [ ${USER_ID:-0} -ne 0 ] && [ ${GROUP_ID:-0} -ne 0 ]; then \
    groupadd -g ${GROUP_ID} ${GROUP} &&\
    useradd -l -u ${USER_ID} -g ${GROUP} -G sudo,wireshark ${USERNAME} &&\
    install -d -m 0755 -o ${USERNAME} -g ${GROUP} /home/${USERNAME}/workspace/repos &&\
    install -d -m 0755 -o ${USERNAME} -g ${GROUP} /home/${USERNAME}/workspace/eprosima &&\
    chown --changes --silent --no-dereference --recursive \
        ${USER_ID}:${GROUP_ID} \
        /home/${USERNAME} && \
    echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
    ;fi

RUN pip3 install -U \
        setuptools
RUN pip3 install \
        vcstool \
        colcon-common-extensions \
        colcon-mixin

ENV TERM xterm-256color
ENV PATH /home/${USERNAME}/.local/bin:$PATH
ENV MAKEFLAGS -j7 -l6.8
USER ${USERNAME}
WORKDIR /home/${USERNAME}/workspace
