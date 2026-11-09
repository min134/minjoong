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

카메라가 검출되지 않으면 송신기를 실행하기 전에 다음 명령으로 확인합니다.

```bash
rpicam-hello --list-cameras
# 구형 Raspberry Pi OS에서는 다음 명령을 사용합니다.
libcamera-hello --list-cameras
```

목록에 카메라가 없으면 CSI 케이블 방향과 양쪽 체결 상태를 확인하고,
Raspberry Pi 설정에서 카메라 인터페이스가 enable되어 있는지 점검한 뒤 재부팅합니다.

카메라 없이 GStreamer UDP 경로만 점검하려면 Raspberry Pi A에서 다음 테스트
패턴 명령을 실행합니다. 수신 측 주소와 포트는 실제 설정에 맞춥니다.

```bash
gst-launch-1.0 -e videotestsrc is-live=true pattern=ball \
  ! video/x-raw,width=640,height=480,framerate=30/1 \
  ! videoconvert ! x264enc tune=zerolatency speed-preset=ultrafast bitrate=500 \
  ! rtph264pay config-interval=1 pt=96 \
  ! udpsink host=192.168.0.153 port=5000 sync=false
```

다른 터미널에서 `sudo tcpdump -ni any -c 10 udp port 5000`을 실행한 상태로
위 명령을 10초 실행해 패킷이 실제로 보이는지 확인합니다.

```bash
timeout 10s gst-launch-1.0 -e videotestsrc is-live=true pattern=ball \
  ! video/x-raw,width=640,height=480,framerate=30/1 \
  ! videoconvert ! x264enc tune=zerolatency speed-preset=ultrafast bitrate=500 \
  ! rtph264pay config-interval=1 pt=96 \
  ! udpsink host=192.168.0.153 port=5000 sync=false
echo "gst-launch exit=$?"
```

수신 측 `gstreamer_receiver.sh`에서 영상과 tcpdump 패킷이 확인될 때만
UDP/GStreamer 경로가 정상인 것으로 판단하고 송신기를 실행합니다. 패킷이 없으면
`gst-inspect-1.0` 결과와 위 명령의 stderr를 먼저 확인해야 합니다.

송신 중 별도 터미널에서 다음 명령으로 프로세스 상태, 필수 플러그인,
GStreamer stderr, UDP 패킷을 확인할 수 있습니다.

```bash
pgrep -af 'camera-udp-sender.py|gst-launch-1.0'
gst-inspect-1.0 fdsrc rawvideoparse x264enc rtph264pay udpsink
sudo tcpdump -ni any udp port 5000
```

`gst-launch-1.0`가 `PREROLLING`에서 멈추면 카메라와 무관하게 다음
테스트 패턴을 실행해 GStreamer 경로를 분리 확인합니다.

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
