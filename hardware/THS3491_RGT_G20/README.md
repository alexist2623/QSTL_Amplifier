# THS3491 RGT, approximately 20 V/V

## Current Altium CAD snapshot: Rev D

- [Altium project](altium_revD/QSTL_THS3491_RGT_G20_RevD.PrjPcb)
- [Schematic](altium_revD/QSTL_THS3491_RGT_G20_RevD.SchDoc)
- [PCB layout](altium_revD/QSTL_THS3491_RGT_G20_RevD.PcbDoc)
- [Rev D changes, validation and compatibility limits](altium_revD/README.md)
- [L1](altium_revD/review/layout_L1.png), [core](altium_revD/review/layout_core.png),
  [PD/NC detail](altium_revD/review/layout_PD_NC.png), [L3](altium_revD/review/layout_L3.png)

The latest capacitor and PD/NC corrections are applied to the native Rev D PCB.
R15 (1 Mohm output load) and the bottom explanatory silk notes have been removed.
The isolated TP1 GND test point above the output connector is also removed from
the PCB, schematic and BOM, with its copper and bottom mask restored to GND.
[TP1 removal comparison](altium_revD/review/TP1_removed.png).
Two PJ-102AH DC barrel inputs replace the four wire pads; banana sockets are cancelled.
J9 center is +15 V, J10 center is -15 V, and both sleeves are GND.
The PCB embeds 3D STEP bodies for 26 fitted components. The original board size and mounting holes are retained.
[DC input layout and polarity](altium_revD/review/dc_input_layout.png).
Both raw supply pours are expanded around their DC jack pads; see the
[positive/negative input comparison](altium_revD/review/dc_planes_both.png).
RF copper cutouts remain on L2; six inherited L3/L4 cutouts are removed.
Twelve GND vias clipping VIN_P and seven blocking the new L3 VCC corridor were removed; 98 RF shield vias, 96 mounting-hole ring vias and 148 perimeter vias are subsequently added (965 vias total). Bottom GND is broadly
exposed while preserving mask around component/connector pins and the central U1
thermal opening; see [bottom mask and via changes](altium_revD/review/bottom_ground_mask_and_vias.png)
and [L2/L3/L4 comparison](altium_revD/review/RF_layers_L2_L3_L4.png).
L3 now uses local VCC/VEE corridors and GND elsewhere, retaining short C7 branches;
see [L3 before/after](altium_revD/review/L3_local_power_before_after.png).
[RF shield vias](altium_revD/review/RF_3W_shield_vias.png) use a minimum 3W copper-edge
gap (0.9174 mm for the 0.3058 mm RF lines), with existing RF geometry retained.
Each mounting hole now has a 24-via GND ring at a 3.40 mm radius;
see the [mounting-hole ring diagram](altium_revD/review/mechanical_hole_via_rings.png).
The [board-edge GND via row](altium_revD/review/board_edge_vias.png) has a 1.00 mm
center inset and nominal pitch, preserving clearance around RF connector pads.
Rev D also reconciles inherited two-layer-flex V8 metadata with its four-layer
rigid V9 stack. Independent copper DRC has zero errors and zero unconnected pads;
Altium 25.8.1 open/save/reopen is verified. Track extended-layer offsets and pad
layer IDs are repaired; all 83 remaining pads load on their intended layers. Native ERC,
repour and DRC remain pending. Keep the three project files together.

## Historical Altium CAD snapshot: Rev C

- [Altium project](altium_revC/QSTL_THS3491_RGT_G20_RevC.PrjPcb)
- [Schematic](altium_revC/QSTL_THS3491_RGT_G20_RevC.SchDoc)
- [PCB layout](altium_revC/QSTL_THS3491_RGT_G20_RevC.PcbDoc)
- [Rev C notes and existing validation records](altium_revC/README.md)
- [BOM](altium_revC/assembly/BOM_REVIEW.csv) and [SMT placement data](altium_revC/assembly/CPL_SMT_REVIEW.csv)

Keep the project, schematic, and PCB documents together. These are native Altium review files, not a manufacturing release.

## Latest layout intent

[Design requirements](../../DESIGN_REQUIREMENTS.md) and [planning drawings](planning/README.md) record the subsequent user corrections. Those corrections are now implemented in Rev D; the native Rev C snapshot remains unchanged. The planning drawings were created without launching Altium.

The dated [JLCPCB availability record](jlcpcb_availability_2026-10-22.json) records earlier procurement research; it is not a live stock check or an order.
