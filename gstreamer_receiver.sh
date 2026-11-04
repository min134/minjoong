#!/usr/bin/env bash

gst-launch-1.0 udpsrc port=5000 \
  caps="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264" \
  ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false
