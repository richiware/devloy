ARG UBUNTU_DISTRO=jammy

FROM ubuntu:${UBUNTU_DISTRO}
MAINTAINER Ricardo González<correoricky@gmail.com>

ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USERNAME=ricardo
ARG GROUP=ricardo

# Avoid interactuation with installation of some package that needs the locale.
ENV TZ=Europe/Madrid

RUN apt update && \
    DEBIAN_FRONTEND=noninteractive apt install -y \
        build-essential \
        cmake \
        `: # Needed for download latest ccache version.` \
        curl \
        gdb \
        git \
        `: # Needed for ccdb.` \
        jq \
        locales \
        python3-venv \
        python3-pip \
        python3-setuptools \
        sudo \
        tzdata \
        yadm \
        wget

# Set the locale
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN if [ ${USER_ID:-0} -ne 0 ] && [ ${GROUP_ID:-0} -ne 0 ]; then \
    if [ ${GROUP_ID} -eq 1000 ]; then \
        groupmod -n ${GROUP} ubuntu; \
    else \
        groupadd -g ${GROUP_ID} ${GROUP}; \
    fi; \
    if [ ${USER_ID} -eq 1000 ]; then \
        usermod -l ${USERNAME} -g ${GROUP} -G sudo -d /home/${USERNAME} ubuntu; \
    else \
        useradd -l -u ${USER_ID} -g ${GROUP} -G sudo ${USERNAME}; \
    fi; \
        install -d -m 0755 -o ${USERNAME} -g ${GROUP} /home/${USERNAME}/workspace/repos && \
        chown --changes --silent --no-dereference --recursive \
            ${USER_ID}:${GROUP_ID} \
            /home/${USERNAME} && \
        echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
    ;fi

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
ENV USER ${USERNAME}
USER ${USERNAME}
WORKDIR /home/${USERNAME}

RUN python3 -m venv vdev && \
    . vdev/bin/activate && \
    pip3 install \
        vcstool \
        colcon-common-extensions \
        colcon-mixin

RUN . vdev/bin/activate \
    && yadm clone https://github.com/richiware/dotfiles.git --bootstrap \
    && sudo apt clean \
    && sudo rm -rf /var/lib/apt/lists/*

RUN . vdev/bin/activate \
    && colcon mixin add default https://raw.githubusercontent.com/colcon/colcon-mixin-repository/master/index.yaml \
    && colcon mixin update default \
    && colcon mixin add richiware https://raw.githubusercontent.com/richiware/richiware-mixins/master/index.yaml \
    && colcon mixin update richiware

RUN   echo "yadm pull --recurse-submodules; colcon mixin update richiware" >> /home/${USERNAME}/.zlogin

WORKDIR /home/${USERNAME}/workspace
ENTRYPOINT [ "/bin/zsh" ]
CMD [ "-l" ]
