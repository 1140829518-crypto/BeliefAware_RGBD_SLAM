# YOLO semantic asset provenance

The frozen experiment runner loads:

```text
yolov5_RemoveDynamic/weights/yolov5s.pt
```

Recorded SHA-256:

```text
3cb5c452360bc5c1dfd19ab0aca46f5e15a64af028846867310313a966cfe920
```

The local inference source tree records:

- upstream remote: `https://github.com/ultralytics/yolov5`
- local Git revision: `d2e754b67bc08d3634df05932cc94d8c9314a7b1`
- `requirements.txt` SHA-256:
  `ce4f857e8e3d7c9f52543c38891f747c1e5bff36c050df972ed4b7d098f2bf10`
- `detect_speedup_send.py` SHA-256:
  `73ae3edbfe876e4ce46e52d6afbbdf4c2187a848cbf4b3f79c8dc841c3a1b978`

The exact public release URL from which this particular checkpoint file was
originally obtained is not recorded. The file hash is authoritative; the
checkpoint must not be substituted merely because another file is also named
`yolov5s.pt`. The checkpoint is not redistributed in this release because its
provenance and redistribution conditions must be handled separately.
