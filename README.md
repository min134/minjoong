# minjoong

## Raspberry Pi A 송신

수신 측의 UDP 5000 RTP/H264 파이프라인과 호환되는 Canny 영상 송신기입니다.
기본 프로파일은 `640x480-500`이며, `720p-2000`, `640x480-500`,
`720p-4000`을 지원합니다. 비트레이트 단위는 kbps입니다.

```bash
# Raspberry Pi B의 주소를 명령행으로 지정하면 sudo 환경에서도 안전합니다.
sudo python3 canny_sender.py --profile 720p-2000 --host 192.168.0.153

# 또는 VIDEO_HOST를 sudo에 명시적으로 전달합니다.
sudo env VIDEO_HOST=192.168.0.153 python3 canny_sender.py --profile 640x480-500
```

GStreamer가 카메라 영상을 직접 전송하는 경우에는 다음과 같이 실행합니다.

```bash
sudo env VIDEO_HOST=192.168.0.153 ./gstreamer_sender.sh 720p-4000
```

수신 측에서는 `gstreamer_receiver.sh`를 실행하고 UDP 포트 5000을 엽니다.
