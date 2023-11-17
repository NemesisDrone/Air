# ----------------------------------------------------------------------------------------------------------------------
#                                     NEMESIS AIR EMBEDDED SYSTEMS ENVIRONMENT
# ----------------------------------------------------------------------------------------------------------------------
FROM python:3.11.6-bookworm
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
RUN apt install wget build-essential nano -y

# --- GST, V4L, OCV for Video Streaming ---
RUN apt install gir1.2-gst-plugins-bad-1.0 libopenh264-7 gstreamer1.0-plugins-base-apps libv4l-0 libgstreamer1.0-0 libgirepository-1.0-1 libgirepository1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-bad gobject-introspection python3-gst-1.0 python3-gi -y

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

# CMD defined in compose.yml
CMD []
ENTRYPOINT []
