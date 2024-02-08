FROM debian:10

# Install dependencies
RUN apt-get update \
    && apt-get install -y build-essential zlib1g-dev wget openssl \
    libssl-dev libgcc-8-dev libffi-dev libreadline-gplv2-dev \
    libncursesw5-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev \
    && cd /tmp/ \
    && wget https://www.python.org/ftp/python/3.10.12/Python-3.10.12.tgz \
    && tar -xvzf Python-3.10.12.tgz \
    && cd Python-3.10.12 \
    && ./configure --enable-optimizations \
    && make -j 4 \
    && make altinstall \
    && cd \
    && rm -rf /tmp/*

# Create virtual environment
RUN python3.10 -m venv /root/venv

# Set environment variables
ENV PYTHONPATH=/root/algos
ENV PATH="/root/venv/bin:$PATH"

# Copy project files
COPY . /root/algos

# Install Python dependencies
RUN pip install --upgrade wheel pip==23.0 \
    && pip install -r /root/algos/requirements.txt

# Set work directory
WORKDIR /root/algos