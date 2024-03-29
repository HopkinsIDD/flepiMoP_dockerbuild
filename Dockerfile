FROM ubuntu:20.04

USER root
ENV TERM linux

# set locale info
RUN apt-get update && apt-get install -y locales && locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# set noninteractive installation
ENV DEBIAN_FRONTEND noninteractive
#ENV R_BASE_VERSION 4.2.2-1.2004.0
ENV R_BASE_VERSION 4.3.0-1.2004.0

# see https://www.digitalocean.com/community/tutorials/how-to-install-r-on-ubuntu-18-04
# https://cran.r-project.org/bin/linux/debian/
# https://cran.r-project.org/bin/linux/ubuntu/README.html
RUN set -e \
      && apt-get update \
      && apt-get -u dist-upgrade \
      && apt-get -y install --no-install-recommends --no-install-suggests \
        gnupg2 gnupg1 ca-certificates software-properties-common \
      && apt-key adv --keyserver keyserver.ubuntu.com --recv-keys E298A3A825C0D65DFD57CBB651716619E084DAB9 \
      && add-apt-repository 'deb https://cloud.r-project.org/bin/linux/ubuntu focal-cran40/' \
      && add-apt-repository ppa:git-core/ppa \
      && add-apt-repository ppa:deadsnakes/ppa

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # needed packages
    tzdata \
    sudo \
    less \
    build-essential \
    git-core \
    git-lfs \
    curl \
    pandoc \
    pandoc-citeproc \
    postgresql-client \
    libpq-dev \
    libssl-dev \
    openssl \
    libgdal-dev \
    libyaml-dev \
    libjpeg-dev \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    libblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    libxml2-dev \
    libcurl4-openssl-dev \
    libfontconfig1-dev \
    libcairo2-dev \
    libudunits2-dev \
    libharfbuzz-dev \
    libfribidi-dev \ 
    gfortran \
    unzip \
    zip \
    pbzip2 \
    vim-nox \
    nano \
    libbz2-dev \
    libsqlite3-dev \
    sqlite3 \
    openssh-server \
    libsnappy-dev \
    libncurses-dev \
    libreadline-dev \
    supervisor \
    awscli \
    r-base-dev=${R_BASE_VERSION} \
    r-base=${R_BASE_VERSION} \
    cmake \
    python3.10 \
    python3.10-dev \
    python3.10-distutils \
    python3.10-venv \
    # make sure we have up-to-date CA certs or curling some https endpoints (like python.org) may fail
    ca-certificates \
    cmake \
    # app user creation
    && sudo ln -s /usr/bin/python3.10 /usr/local/bin/python \
    && sudo ln -s /usr/bin/pip3 /usr/local/bin/pip \
    && useradd -m app \
    && mkdir -p /home/app \
    && chown -R app:app /home/app \
    # set up sudo for app user
    && sudo echo "app ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/app \
    && sudo usermod -a -G staff app

WORKDIR /home/app
USER app
ENV HOME /home/app

#####
# Python (managed via pyenv)
#####
# 
ENV PYTHON_VERSION 3.10
ENV VENV_ROOT /var/python/$PYTHON_VERSION/virtualenv
COPY --chown=app:app flepimop-cache/gempyor_pkg $HOME/gempyor_pkg

RUN sudo python -m venv $VENV_ROOT \
  && sudo chown app:app -R $VENV_ROOT \
  && $VENV_ROOT/bin/python3.10 -m pip install --upgrade setuptools pip boto3 \
  && $VENV_ROOT/bin/python3.10 -m pip install $HOME/gempyor_pkg

COPY --chown=app:app Docker.bashrc $HOME/.bashrc
COPY --chown=root:root Docker.bashrc /root/.bashrc

#####
# R
#####

# Use renv for R package management
RUN sudo Rscript -e "install.packages('renv',repos='https://cloud.r-project.org/')"
COPY --chown=app:app renv/renv.cache $HOME/.cache
COPY --chown=app:app renv/renv.lock $HOME/renv.lock
COPY --chown=app:app renv/renv $HOME/renv
COPY --chown=app:app Docker.Rprofile $HOME/.Rprofile
COPY --chown=app:app flepimop-cache/R_packages $HOME/flepi/R_packages
COPY --chown=app:app flepimop-cache/main_scripts $HOME/flepi/main_scripts

COPY --chown=app:app build/local_install.R $HOME/build/local_install.R

CMD ["/bin/bash"]
