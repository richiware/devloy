ARG DISTRO=ubuntu
ARG RELEASE=noble

########################################################################
# Base stage.
#
# apt sources, toolchain and locale. Shared by the ccache builder and by
# the final image, so these packages are built and cached only once.
########################################################################
FROM ${DISTRO}:${RELEASE} AS base
LABEL org.opencontainers.image.authors="Ricardo González<correoricky@gmail.com>"

# Avoid interactuation with installation of some package that needs the locale.
ENV TZ=Europe/Madrid
ENV DEBIAN_FRONTEND=noninteractive

# Fingerprint of "Launchpad PPA for Neovim PPA Team", the key that
# `add-apt-repository ppa:neovim-ppa/unstable` installs.
ARG NEOVIM_PPA_KEY=9DBB0BE9366964F134855E2255F96FCF8231B6DD

# Everything in a single layer: the package lists (~53MB) must be removed in
# the very same layer that creates them, otherwise they stay in the image no
# matter how many `apt clean` run later on.
RUN touch /.dockerenv && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        lsb-release && \
    #################################
    # PPA for neovim                #
    #################################
    # Added by hand instead of with add-apt-repository: that one command
    # drags in software-properties-common (python3-gi, dbus, krb5, ~177MB).
    if [ "$(lsb_release -si | tr '[:upper:]' '[:lower:]')" = "ubuntu" ]; then \
        install -d /etc/apt/keyrings && \
        curl -fsSL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x${NEOVIM_PPA_KEY}" \
            -o /etc/apt/keyrings/neovim-ppa.asc && \
        grep -q 'BEGIN PGP PUBLIC KEY BLOCK' /etc/apt/keyrings/neovim-ppa.asc && \
        printf '%s\n' \
            'Types: deb' \
            'URIs: https://ppa.launchpadcontent.net/neovim-ppa/unstable/ubuntu/' \
            "Suites: $(lsb_release -sc)" \
            'Components: main' \
            'Signed-By: /etc/apt/keyrings/neovim-ppa.asc' \
            > /etc/apt/sources.list.d/neovim-ppa.sources && \
        apt-get update; \
    fi && \
    apt-get install -y --no-install-recommends \
        #################################
        # c++ tools                     #
        #################################
        build-essential                 \
        cmake                           \
        ninja-build                     \
        gdb                             \
        locales                         \
        lsb-release                     \
        sudo                            \
        tzdata                          \
        wget                            \
        #################################
        # tools required                #
        #################################
        curl                            \
        git                             \
        #################################
        # pulled in as recommends of    #
        # git/curl, needed explicitly   #
        # with --no-install-recommends  #
        #################################
        less                            \
        openssh-client                  \
        patch                           \
        #################################
        # tools required by devloy      #
        #################################
        jq                              \
        yadm                            \
        #################################
        # python3 dependencies          #
        #################################
        # python3-pip and python3-setuptools are not needed: pip inside the
        # venv comes from python3-venv's ensurepip.
        python3-venv && \
    #################################
    # Set the locale               #
    #################################
    sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen && \
    rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

########################################################################
# CCache builder stage.
#
# Throw-away stage: only the stripped binary reaches the final image, so
# neither the sources nor the downloaded zstd are ever committed.
########################################################################
FROM base AS ccache-builder

# Compile and install last CCache
RUN export DISTRO_NAME=$(lsb_release -s -i | tr '[:upper:]' '[:lower:]') && \
    export DISTRO_RELEASE=$(lsb_release -sr | cut -d. -f1) && \
    if [ "${DISTRO_NAME}" = "ubuntu" ] && [ $DISTRO_RELEASE -ge 22 ]; then \
        LATEST_RELEASE=$(curl -L -s -H 'Accept: application/json' https://github.com/ccache/ccache/releases/latest); \
        LATEST_VERSION=$(echo $LATEST_RELEASE | sed -e 's/.*"tag_name":"\([^"]*\)".*/\1/'); \
        wget -O ccache.tar.gz https://github.com/ccache/ccache/archive/refs/tags/$LATEST_VERSION.tar.gz; \
    else \
        wget -O ccache.tar.gz https://github.com/ccache/ccache/archive/refs/tags/v4.11.3.tar.gz; \
    fi; \
    tar xzf ccache.tar.gz && \
    cd ccache-* && \
    cmake -DCMAKE_BUILD_TYPE=Release -DZSTD_FROM_INTERNET=ON -DREDIS_STORAGE_BACKEND=OFF . && \
    cmake --build . --target install && \
    strip /usr/local/bin/ccache

########################################################################
# Final image.
########################################################################
FROM base

ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USERNAME=ricardo
ARG GROUP=ricardo

COPY --from=ccache-builder /usr/local/bin/ccache /usr/local/bin/ccache

RUN if [ ${USER_ID:-0} -ne 0 ] && [ ${GROUP_ID:-0} -ne 0 ]; then \
        export DISTRO_NAME=$(lsb_release -s -i | tr '[:upper:]' '[:lower:]') && \
        export DISTRO_RELEASE=$(lsb_release -sr | cut -d. -f1) && \
        if [ ${GROUP_ID} -eq 1000 ] && [ "${DISTRO_NAME}" = "ubuntu" ] && [ $DISTRO_RELEASE -ge 24 ]; then \
            groupmod -n ${GROUP} ubuntu; \
        else \
            groupadd -g ${GROUP_ID} ${GROUP}; \
        fi; \
        if [ ${USER_ID} -eq 1000 ] && [ "${DISTRO_NAME}" = "ubuntu" ] && [ $DISTRO_RELEASE -ge 24 ]; then \
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

# Create non-existing groups
RUN groupadd sudo || true && \
    groupadd -g 85 usb || true

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
    pip3 install --no-cache-dir \
        git+https://github.com/richiware/colocon \
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
# The bootstrap installs packages but never runs `apt update`, so the lists are
# fetched here and dropped again inside this same layer.
RUN . vdev/bin/activate \
    && sudo apt-get update \
    && yadm clone https://github.com/richiware/dotfiles.git --bootstrap \
    && sudo rm -rf /var/lib/apt/lists/* \
    && rm -rf ~/.cache/go-build ~/.cache/pip ~/.cache/luarocks

# Install nvim plugins
# The plugin .git directories are ~85MB and are not needed to load them; drop
# them (`Lazy update` inside the container is traded for the image being
# rebuilt to update plugins).
RUN nvim --headless '+echo "Installing"' '+Lazy! sync' +qa \
    && rm -rf ~/.local/share/nvim/lazy/*/.git ~/.cache/nvim

RUN   echo "yadm pull --recurse-submodules; colcon mixin update richiware" >> /home/${USERNAME}/.zlogin

WORKDIR /home/${USERNAME}/workspace
ENTRYPOINT [ "/bin/zsh" ]
CMD [ "-l" ]
