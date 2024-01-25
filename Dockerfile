# ----------------------------------------------------------------------------------------------------------------------
#                                     NEMESIS AIR EMBEDDED SYSTEMS ENVIRONMENT
# ----------------------------------------------------------------------------------------------------------------------
FROM python:3.11.6-bookworm
RUN useradd -ms /bin/bash nemesis
USER root

# ----------------------------------------------------------------------------------------------------------------------
#                                                ENVIRONMENT SETUP
# ----------------------------------------------------------------------------------------------------------------------
# --- Tools ---
RUN apt update
RUN apt install wget build-essential nano dnsutils python3-serial -y

# --- GST, V4L & LIBCAM for Video Streaming ---
RUN apt install gstreamer1.0-plugins-base-apps libv4l-0 libgstreamer1.0-0 libgirepository-1.0-1 libgirepository1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-bad gobject-introspection python3-gst-1.0 python3-gi libcamera-v4l2 gstreamer1.0-libcamera libcamera-ipa -y

# --- RTIMULib (SenseHat & GPIO) ---
RUN mkdir -p /tmp/nemesis
WORKDIR /tmp/nemesis
RUN wget https://github.com/RPi-Distro/RTIMULib/archive/refs/tags/V7.2.1.tar.gz
RUN tar -xzf V7.2.1.tar.gz
WORKDIR /tmp/nemesis/RTIMULib-7.2.1/Linux/python
RUN python3 setup.py build
RUN python3 setup.py install

RUN apt install  -y

# --- Propulsion Brushless ESC ---
WORKDIR /tmp/nemesis
RUN wget https://github.com/joan2937/pigpio/archive/master.zip
RUN unzip master.zip
WORKDIR /tmp/nemesis/pigpio-master
RUN make
RUN make install

# --- ADD ADDITIONAL DEPENDENCIES HERE TO AVOID INVALIDATING CACHE ---

# --- Project Dependencies and files ---
COPY ./requirements-dev.txt /app/requirements-dev.txt
COPY ./requirements.txt /app/requirements.txt
RUN apt install cmake -y
RUN python3 -m pip install -r /app/requirements.txt
RUN python3 -m pip install -r /app/requirements-dev.txt

# --- Utilities ---
COPY ./src/nemesis_utilities /app/src/nemesis_utilities
WORKDIR /app/src/nemesis_utilities
RUN python3 -m pip install -e .

# --- Camera access ---
RUN usermod -aG video nemesis

# --- GST encoder for H264 (currently to enable simuling): vah264lpenc
RUN apt install gstreamer1.0-plugins-bad -y

# ----------------------------------------------------------------------------------------------------------------------
#                                                EXECUTION
# ----------------------------------------------------------------------------------------------------------------------
WORKDIR /app
USER nemesis
COPY . /app

# CMD defined in compose.yml
CMD []
ENTRYPOINT []
