FROM centos/devtoolset-7-toolchain-centos7
USER root


RUN yum update -y                                                                               && \
    yum install -y wget

RUN wget -qO- https://micromamba.snakepit.net/api/micromamba/linux-64/latest | tar -xvj bin/micromamba --strip-components=1 && \
    ./micromamba shell init -s bash -p ~/micromamba                                                                         && \
    rm -rf /var/lib/{apt,dpkg,cache,log}                                                                                    && \
    cp ./micromamba /usr/bin                                                                                                && \
    micromamba create -n workflow_executor_env                                                                              && \
    micromamba install workflow-executor=1.0.25 -c eoepca -c conda-forge -n workflow_executor_env                           && \
    rm -fr /srv/conda/pkgs                                                                                                  && \
    rm -fr /tmp/*