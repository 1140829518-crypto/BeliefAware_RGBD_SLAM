# Public configuration index

- `methods.env`: exact runtime mode switches for V3 and V4.
- `sequences.example.yml`: machine-editable dataset path template.
- `Bonn.yaml`: Bonn-specific RGB-D calibration used by the internal method.
- `../Examples/RGB-D/TUM3.yaml`: TUM Freiburg 3 calibration.
- `../dataset_associations/`: frozen TUM RGB-depth associations.

Only filesystem roots and compute-device selection should be changed. Do not
change method switches, camera calibration, thresholds, or belief parameters.
