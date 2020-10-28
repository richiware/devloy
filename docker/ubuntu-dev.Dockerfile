FROM ubuntu
MAINTAINER Ricardo González<correoricky@gmail.com>

ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USERNAME=ricardo
ARG GROUP=ricardo

# Avoid interactuation with installation of some package that needs the locale.
ENV TZ=Europe/Madrid
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && \
    apt-get -y install --no-install-recommends \
        sudo \
        wget \
        build-essential \
        cmake \
        git \
        gdb \
        ccache \
        jq \
        python3-pip \
        libgtest-dev \
        valgrind \
        libasio-dev \
        libtinyxml2-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN cd /usr/src/googletest && \
    cmake . && \
    cmake --build . --target install

RUN if [ ${USER_ID:-0} -ne 0 ] && [ ${GROUP_ID:-0} -ne 0 ]; then \
    groupadd -g ${GROUP_ID} ${GROUP} &&\
    useradd -l -u ${USER_ID} -g ${GROUP} ${USERNAME} &&\
    install -d -m 0755 -o ${USERNAME} -g ${GROUP} /home/${USERNAME}/workspace/repos &&\
    install -d -m 0755 -o ${USERNAME} -g ${GROUP} /home/${USERNAME}/workspace/eprosima &&\
    chown --changes --silent --no-dereference --recursive \
        ${USER_ID}:${GROUP_ID} \
        /home/${USERNAME} && \
    adduser ${USERNAME} sudo && \
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
