# Formal accuracy artifacts

The formal accuracy campaign used the two artifacts recorded in
`EXPECTED_SHA256.txt`. The exact payloads are included here as
`rgbd_tum.accuracy` and `libORB_SLAM2.accuracy.so`.

They were recovered deterministically by relinking the preserved formal-build
object files without recompilation. Both resulting payloads exactly match the
hashes recorded before the formal experiments. The runtime-instrumented
artifacts in the sibling `runtime/` directory remain different binaries and
must not be substituted.

Status: **payload included and SHA-256 verified**.
