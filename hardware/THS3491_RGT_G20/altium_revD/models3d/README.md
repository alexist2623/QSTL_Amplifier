# Rev D component 3D models

The PCB embeds STEP data for all **26 fitted components**. External STEP files
are retained for maintenance; opening the PCB does not require a KiCad or
FreeCAD installation. `placements.json` records model files, origins, rotation,
side, dimensions and hashes. Copper, pad shapes and component positions are
unchanged by the model addition.

The following intentionally have no physical body: R5 (DNP)
and H1-H4 (mounting holes without hardware). TP1 was removed from the PCB and
schematic on 2026-10-28. J4/J5/J6/J8 wire pads were removed
and replaced by J9/J10 DC barrel inputs on 2026-10-28.

R15 (1 Mohm output load) was removed from both the PCB and schematic on 2026-10-27.

## Sources and fidelity

- J9/J10: generated **nominal** PJ-102AH body, bore, center pin and three terminals.
  Body 14.4 x 9 x 11 mm; terminal locations follow the
  [Same Sky drawing](https://www.sameskydevices.com/product/resource/pj-102ah.pdf)
  and the KiCad PJ-102AH footprint. Fine mold/contact details are simplified.
  `tools/power_connectors_models.py` adds this asset and two placements to the
  retained original 24-model manifest. Both models are embedded in the PCB.
- R1-R4, R6-R8, R14, C3-C8 and J7: KiCad 6 packaged standard STEP models,
  from the [KiCad 3D library](https://gitlab.com/kicad/libraries/kicad-packages3D).
  These are package-equivalent visualizations, not exact MPN manufacturer CAD.
  Original model files retain their copyright/license headers. The license is
  CC BY-SA 4.0 with the electronic-design exception described in those headers.
- C1/C2: generated 3.2 x 1.6 x 0.85 mm nominal MLCC body and terminations for
  GRM319. L1/L2: generated 2.0 x 1.25 x 0.85 mm nominal ferrite bead body.
- U1: generated nominal RGT 3 x 3 mm, 16 pins at 0.5 mm pitch, 1 mm body height,
  exposed terminal and pin-1 marker. Reference:
  [TI THS3491 package information](https://www.ti.com/lit/ds/symlink/ths3491.pdf).
  Package visualization does not redefine the existing PCB land pattern.
- J1-J3: exact-part-number `142-0701-851` STEP distributed by
  [Pulse Research Lab](https://www.pulseresearchlab.com/pages/prl-3d-model-data).
  PRL states these component models came from manufacturer websites and are
  reference data. Original file is retained in `sources/`; the seated model
  moves its -0.127 mm seating plane to z=0 and assigns a gold display color.
- H9: **simplified** 7109DG sheet-metal/fin model, with 25.40 x 19.38 x 11.43 mm
  overall envelope from the [Boyd drawing](https://info.boydcorp.com/hubfs/Thermal/Air-Cooling/Boyd-Board-Level-Cooling-Surface-Mount-7109.pdf).
  Sheet thickness, bend details and slots are illustrative. The mounting tab
  is aligned to H9's footprint origin and the fin cage extends toward U1.

The models support assembly visualization; they are not a substitute for
vendor tolerances or a mechanical clearance/manufacturing review.

## Reproduction

`tools/build_component_models.py` runs under the installed FreeCAD 0.20 Python.
It copies standard KiCad assets, generates the nominal models, checks solid
validity and records bounding boxes. It requires the retained SMA source file.
`tools/make_3d_script.py` generates a native Altium script that inserts the
embedded models into a separate candidate PCB, saves it and verifies ownership
after closing and reopening. Its default mode refuses existing bodies;
`--add-refs J9 J10` preserves the original bodies and adds only the new inputs.
`tools/audit_3d_models.py` checks the saved binary's embedded bytes, positions,
rotations, side and component links, and binds its checks to the independent electrical-geometry audit of the same
saved PCB. Native serialization can reorder component-owned records; stream
byte differences are reported separately.
