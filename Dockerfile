FROM debian:10

# Install python3.10 from source since it's not available through apt
RUN apt-get update \
    && apt-get install -y build-essential \
    # ssh \  # chat GPT had some security concerns including this
    # git \ # chat GPT had some security concerns including this
    zlib1g-dev \
    wget \
    openssl \
    libssl-dev \
    libgcc-8-dev \
    libffi-dev \
    libreadline-gplv2-dev \
    libncursesw5-dev \
    libsqlite3-dev \
    tk-dev \
    libgdbm-dev \
    libc6-dev \
    libbz2-dev \
    && cd /tmp/ \
    && wget https://www.python.org/ftp/python/3.10.12/Python-3.10.12.tgz \
    && tar -xvzf Python-3.10.12.tgz \
    && cd Python-3.10.12 \
    && ./configure --enable-optimizations \
    && make -j 4 \
    && make altinstall \
    && cd \
    && rm -rf /tmp/* \
    && python3.10 -m venv ~/venv \
    && mkdir /root/algos

COPY . /root/algos
# COPY requirements.txt /root/algos/requirements.txt

RUN python3.10 -m venv ~/venv \
    && . ~/venv/bin/activate \
    && pip install --upgrade wheel pip==23.0 \
    && pip install -r /root/algos/requirements.txt

# ARG ALGOS_COMMIT
# ENV ALGOS_COMMIT=${ALGOS_COMMIT}
# RUN echo $ALGOS_COMMIT > /root/VERSION.txt


ENV PYTHONPATH=/root/algos
WORKDIR /root/algos


# ### ENTRY POINT STUFF FOR DEBUGGING. MAYBE GOOD TO WORK THIS INTO THE FLOW 
# # Copy the entrypoint script
# COPY entrypoint.sh /root/algos/entrypoint.sh
# # Make the entrypoint script executable
# RUN chmod +x /root/algos/entrypoint.sh

# # Set environment variables
# ENV PYTHONPATH=/root/algos
# WORKDIR /root/algos

# # Set the entrypoint to your script
# ENTRYPOINT ["/root/algos/entrypoint.sh"]