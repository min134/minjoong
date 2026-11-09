# minjoong

## Raspberry Pi A 송신

수신 측의 UDP 5000 RTP/H264 파이프라인과 호환되는 Canny 영상 송신기입니다.
기본 프로파일은 `640x480-500`이며, `720p-2000`, `640x480-500`,
`720p-4000`을 지원합니다. 비트레이트 단위는 kbps입니다.

### 최신 송신 파일 받기

기존 작업 디렉터리를 사용한다면 먼저 원격 `main`을 동기화하고 파일이 있는지 확인합니다.

```bash
cd ~/1104/minjoong
git fetch origin
git pull --ff-only origin main
test -f camera-udp-sender.py && echo "camera-udp-sender.py is ready"
```

`camera-udp-sender.py`가 없으면 올바른 저장소 디렉터리인지 `pwd`와
`git remote -v`로 확인한 뒤 위 명령을 다시 실행합니다.

```bash
# Raspberry Pi B의 주소를 명령행으로 지정하면 sudo 환경에서도 안전합니다.
sudo python3 camera-udp-sender.py --profile 720p-2000 --host 192.168.0.153

# 또는 VIDEO_HOST를 sudo 명령에 명시적으로 전달합니다.
sudo VIDEO_HOST=192.168.0.153 python3 camera-udp-sender.py --profile 640x480-500
```

GStreamer가 카메라 영상을 직접 전송하는 경우에는 다음과 같이 실행합니다.

```bash
sudo VIDEO_HOST=192.168.0.153 ./gstreamer_sender.sh 720p-4000
```

수신 측에서는 `gstreamer_receiver.sh`를 실행하고 UDP 포트 5000을 엽니다.
