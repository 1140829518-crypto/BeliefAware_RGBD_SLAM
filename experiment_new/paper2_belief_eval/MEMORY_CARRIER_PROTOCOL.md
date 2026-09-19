# Strict memory-carrier ablation protocol

The comparison changes the state carrier only. All modes use the same YOLO
detector, TUM3 settings, observation definition, probability recurrence,
decision threshold, datasets, and evaluation scripts.

- Frame: probability is carried by image-plane observation locations.
- Object: probability is carried by associated semantic object IDs.
- MapPoint: probability is carried by persistent `MapPoint::mnId` landmarks.

The shared recurrence is `p_t = 0.7 p_gap + 0.3 z_t`, where
`p_gap = p_(t-1) exp(-0.05 gap)`, the initial probability is 0.5, and the
dynamic threshold is 0.8. Decisions in frame `t` use memory available through
frame `t-1`. Uncertainty and reliability adaptation are disabled in all three
modes. Object association is used only to determine carrier identity; its old
motion-probability update is not used as the ablation belief.

Only MapPoints visible inside the current frame's associated detection are
updated. Lifetime-cumulative object-to-map associations are explicitly not
treated as current observations.

State-switching frequency is evaluated on the downstream binary decision for
each observed stable MapPoint ID. Duplicate calls in one frame are collapsed
to the last decision. This makes the measurement unit identical even though
the hidden state carrier differs.
