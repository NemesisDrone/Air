# ----------------------------------------------------------------------------------------------------------------------
#                                     NEMESIS AIR EMBEDDED SYSTEMS ENVIRONMENT
# ----------------------------------------------------------------------------------------------------------------------
FROM python:3.11.5-slim-bookworm
# USER: nemesis
RUN useradd -ms /bin/bash nemesis

USER root
WORKDIR /app
COPY . /app

# ----------------------------------------------------------------------------------------------------------------------
#                                                ENVIRONMENT SETUP
# ----------------------------------------------------------------------------------------------------------------------
# --- Tools ---
RUN apt update
RUN apt install wget build-essential nano dnsutils -y

# --- RTIMULib (SenseHat & GPIO) ---
RUN mkdir -p /tmp/nemesis
WORKDIR /tmp/nemesis
RUN wget https://github.com/RPi-Distro/RTIMULib/archive/refs/tags/V7.2.1.tar.gz
RUN tar -xzf V7.2.1.tar.gz
WORKDIR /tmp/nemesis/RTIMULib-7.2.1/Linux/python
RUN python3 setup.py build
RUN python3 setup.py install
WORKDIR /app

# --- Project Dependencies ---
RUN python3 -m pip install -r requirements.txt
RUN python3 -m pip install -r requirements-dev.txt

# --- Utilities ---
WORKDIR /app/src/nemesis_utilities
RUN python3 -m pip install -e .

# ----------------------------------------------------------------------------------------------------------------------
#                                              ENVIRONMENT EXECUTION
# ----------------------------------------------------------------------------------------------------------------------
USER nemesis
WORKDIR /app/src/

# CMD defined in docker-compose.yml
CMD []
ENTRYPOINT []