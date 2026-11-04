#!/usr/bin/env bash

gst-launch-1.0 libcamerasrc \
  ! video/x-raw,width=640,height=480 \
  ! videoconvert \
  ! x264enc tune=zerolatency \
  ! rtph264pay \
  ! udpsink host=127.0.0.1 port=5000
