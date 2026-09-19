# YOLO semantic asset provenance

The frozen experiment runner loads:

```text
yolov5_RemoveDynamic/weights/yolov5s.pt
```

Recorded SHA-256:

```text
3cb5c452360bc5c1dfd19ab0aca46f5e15a64af028846867310313a966cfe920
```

Official checkpoint source:

```text
https://github.com/ultralytics/yolov5/releases/download/v3.1/yolov5s.pt
```

Download and verify:

```bash
wget -O yolov5s.pt \
  https://github.com/ultralytics/yolov5/releases/download/v3.1/yolov5s.pt
echo "3cb5c452360bc5c1dfd19ab0aca46f5e15a64af028846867310313a966cfe920  yolov5s.pt" \
  | sha256sum -c -
mkdir -p yolov5_RemoveDynamic/weights
cp yolov5s.pt yolov5_RemoveDynamic/weights/yolov5s.pt
```

- checkpoint filename: `yolov5s.pt`
- byte size: `15184789`
- official release: Ultralytics YOLOv5 v3.1
- verification result: the official download is byte-identical to the frozen
  experiment checkpoint.

The local inference source tree records:

- upstream remote: `https://github.com/ultralytics/yolov5`
- local Git revision: `d2e754b67bc08d3634df05932cc94d8c9314a7b1`
- `requirements.txt` SHA-256:
  `ce4f857e8e3d7c9f52543c38891f747c1e5bff36c050df972ed4b7d098f2bf10`
- `detect_speedup_send.py` SHA-256:
  `73ae3edbfe876e4ce46e52d6afbbdf4c2187a848cbf4b3f79c8dc841c3a1b978`

The checkpoint is not redistributed in this repository. Reproduction downloads
the official asset and requires the SHA-256 check above; another file with the
same filename is not an acceptable substitute.
