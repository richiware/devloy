ARG CENTOS_DISTRO=9

FROM spack/centos-stream${CENTOS_DISTRO}:latest
LABEL org.opencontainers.image.authors="Ricardo González<correoricky@gmail.com>"

ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USERNAME=ricardo
ARG GROUP=ricardo

# Avoid interactuation with installation of some package that needs the locale.
ENV TZ=Europe/Madrid

RUN touch /.dockerenv

RUN dnf install -y \
        #################################
        # c++ tools                     #
        #################################
        cmake                           \
        ninja-build                     \
        gdb                             \
        lsb-release                     \
        sudo                            \
        wget                            \
        #################################
        # tools required by devloy      #
        #################################
        jq                              \
        #################################
        # python3 dependencies          #
        #################################
        python3-pip                     \
        python3-setuptools

# Install yadm
RUN curl -fLo /usr/local/bin/yadm https://github.com/yadm-dev/yadm/raw/master/yadm && chmod a+x /usr/local/bin/yadm

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

RUN if [ ${USER_ID:-0} -ne 0 ] && [ ${GROUP_ID:-0} -ne 0 ]; then \
        groupadd -g ${GROUP_ID} ${GROUP}; \
        useradd -l -u ${USER_ID} -g ${GROUP} -G wheel ${USERNAME}; \
        install -d -m 0755 -o ${USERNAME} -g ${GROUP} /home/${USERNAME}/workspace/repos && \
        chown --changes --silent --no-dereference --recursive \
            ${USER_ID}:${GROUP_ID} \
            /home/${USERNAME} && \
        echo '%wheel ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers \
    ;fi

# Compile and install last CCache
RUN LATEST_RELEASE=$(curl -L -s -H 'Accept: application/json' https://github.com/ccache/ccache/releases/latest); \
    LATEST_VERSION=$(echo $LATEST_RELEASE | sed -e 's/.*"tag_name":"\([^"]*\)".*/\1/'); \
    wget -O ccache.tar.gz https://github.com/ccache/ccache/archive/refs/tags/$LATEST_VERSION.tar.gz; \
    tar xvzf ccache.tar.gz && \
    cd ccache-* && \
    cmake -DZSTD_FROM_INTERNET=ON -DREDIS_STORAGE_BACKEND=OFF . && \
    cmake --build . --target install && \
    cd .. && \
    rm -rf ccache*

ENV TERM=xterm-256color
ENV PATH=/home/${USERNAME}/.local/bin:$PATH
ENV USER=${USERNAME}
ENV GROUP=${GROUP}
ENV USER_ID=${USER_ID}
ENV GROUP_ID=${GROUP_ID}
USER ${USERNAME}
WORKDIR /home/${USERNAME}

# Install colcon and other PIP packages
RUN python3 -m venv vdev && \
    . vdev/bin/activate && \
    pip3 install \
        git+https://github.com/richiware/devloy \
        vcstool \
        colcon-common-extensions \
        colcon-mixin

# Install my colcon mixins
RUN . vdev/bin/activate \
    && colcon mixin add default https://raw.githubusercontent.com/colcon/colcon-mixin-repository/master/index.yaml \
    && colcon mixin update default \
    && colcon mixin add richiware https://raw.githubusercontent.com/richiware/richiware-mixins/master/index.yaml \
    && colcon mixin update richiware

# Install my dotfiles
RUN . vdev/bin/activate \
    && yadm clone https://github.com/richiware/dotfiles.git --bootstrap

# Install nvim plugins
RUN nvim --headless '+echo "Installing' '+Lazy! sync' +qa

RUN   echo "yadm pull --recurse-submodules; colcon mixin update richiware" >> /home/${USERNAME}/.zlogin

WORKDIR /home/${USERNAME}/workspace
ENTRYPOINT [ "/bin/zsh" ]
CMD [ "-l" ]
