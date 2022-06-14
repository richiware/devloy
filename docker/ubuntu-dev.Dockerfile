ARG UBUNTU_DISTRO=focal

FROM ubuntu:${UBUNTU_DISTRO}
MAINTAINER Ricardo González<correoricky@gmail.com>

ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USERNAME=ricardo
ARG GROUP=ricardo

# Avoid interactuation with installation of some package that needs the locale.
ENV TZ=Europe/Madrid
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt update && \
    apt install -y \
        build-essential \
        cmake \
        `: # Needed for download latest cmake version.` \
        curl \
        gdb \
        git \
        `: # Needed for ccdb.` \
        jq \
        python3-pip \
        sudo \
        vim \
        wget \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

RUN if [ ${USER_ID:-0} -ne 0 ] && [ ${GROUP_ID:-0} -ne 0 ]; then \
    groupadd -g ${GROUP_ID} ${GROUP} &&\
    useradd -l -u ${USER_ID} -g ${GROUP} -G sudo ${USERNAME} &&\
    install -d -m 0755 -o ${USERNAME} -g ${GROUP} /home/${USERNAME}/workspace/repos &&\
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

# Compile and install last CCache
RUN LATEST_RELEASE=$(curl -L -s -H 'Accept: application/json' https://github.com/ccache/ccache/releases/latest); \
    LATEST_VERSION=$(echo $LATEST_RELEASE | sed -e 's/.*"tag_name":"\([^"]*\)".*/\1/'); \
    wget -O ccache.tar.gz https://github.com/ccache/ccache/archive/refs/tags/$LATEST_VERSION.tar.gz && \
    tar xvzf ccache.tar.gz && \
    cd ccache-* && \
    cmake -DZSTD_FROM_INTERNET=ON -DREDIS_STORAGE_BACKEND=OFF . && \
    cmake --build . --target install && \
    cd .. && \
    rm -rf ccache*



ENV TERM xterm-256color
ENV PATH /home/${USERNAME}/.local/bin:$PATH
ENV MAKEFLAGS -j7 -l6.8
USER ${USERNAME}
WORKDIR /home/${USERNAME}/workspace
