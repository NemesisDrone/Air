# ----------------------------------------------------------------------------------------------------------------------
#                                     NEMESIS AIR EMBEDDED SYSTEMS ENVIRONMENT
# ----------------------------------------------------------------------------------------------------------------------
FROM python:3.11.6-bookworm
# USER: nemesis
#RUN useradd -ms /bin/bash nemesis

USER root

# ----------------------------------------------------------------------------------------------------------------------
#                                                ENVIRONMENT SETUP
# ----------------------------------------------------------------------------------------------------------------------
# --- Tools ---
RUN apt update
RUN apt install wget build-essential nano dnsutils -y

# --- GST, V4L, OCV for Video Streaming ---
RUN apt install libgstreamer1.0-0 libgstreamer-opencv1.0-0 libv4l-0 python3-gst-1.0 python3-opencv python3-websockets -y

# --- RTIMULib (SenseHat & GPIO) ---
RUN mkdir -p /tmp/nemesis
WORKDIR /tmp/nemesis
RUN wget https://github.com/RPi-Distro/RTIMULib/archive/refs/tags/V7.2.1.tar.gz
RUN tar -xzf V7.2.1.tar.gz
WORKDIR /tmp/nemesis/RTIMULib-7.2.1/Linux/python
RUN python3 setup.py build
RUN python3 setup.py install

# --- Project Dependencies and files ---
COPY ./requirements-dev.txt /app/requirements-dev.txt
COPY ./requirements.txt /app/requirements.txt
RUN python3 -m pip install -r /app/requirements.txt
RUN python3 -m pip install -r /app/requirements-dev.txt

# --- Utilities ---
COPY ./src/nemesis_utilities /app/src/nemesis_utilities
WORKDIR /app/src/nemesis_utilities
RUN python3 -m pip install -e .

# ----------------------------------------------------------------------------------------------------------------------
#                                                EXECUTION
# ----------------------------------------------------------------------------------------------------------------------
#USER nemesis
WORKDIR /app/src/
COPY . /app

# CMD defined in compose.yml
CMD []
ENTRYPOINT []
