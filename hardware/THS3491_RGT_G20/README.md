# THS3491 RGT, approximately 20 V/V

## Current Altium CAD snapshot: Rev D

- [Altium project](altium_revD/QSTL_THS3491_RGT_G20_RevD.PrjPcb)
- [Schematic](altium_revD/QSTL_THS3491_RGT_G20_RevD.SchDoc)
- [PCB layout](altium_revD/QSTL_THS3491_RGT_G20_RevD.PcbDoc)
- [Rev D changes, validation and compatibility limits](altium_revD/README.md)
- [L1](altium_revD/review/layout_L1.png), [core](altium_revD/review/layout_core.png),
  [PD/NC detail](altium_revD/review/layout_PD_NC.png), [L3](altium_revD/review/layout_L3.png)

The latest capacitor and PD/NC corrections are applied to the native Rev D PCB.
Rev D also reconciles inherited two-layer-flex V8 metadata with its four-layer
rigid V9 stack. Independent copper DRC has zero errors and zero unconnected pads;
Altium 25.8.1 open/save/reopen is verified. Track extended-layer offsets and pad
layer IDs are repaired; all 84 pads load on their intended layers. Native ERC,
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
