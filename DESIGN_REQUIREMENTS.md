# QSTL Amplifier: User Design Requirements and Review Notes

Recorded: 2026-10-22

This document records the user's instructions for the THS3491 RGT amplifier project. Later corrections take precedence over earlier requests. It is a requirements record, not evidence that the existing CAD satisfies every requirement or that the board is ready for manufacture.

## 1. Deliverable and current workflow

- The schematic and PCB layout deliverables must be native Altium files. A KiCad project is not the requested final deliverable.
- The earlier layout discussion requested planning drawings without launching Altium. On 2026-10-22 the user subsequently requested follow-up work, authorizing implementation in a new Rev D, and also requested investigation of the Altium project-opening / Internal Plane warning. The Rev C originals remain unchanged.
- Show the intended arrangement clearly before implementing it: include an L1 overview, an enlarged U1 area, and an internal power-plane drawing. Distinguish planning illustrations from actual CAD screenshots or exports.
- Treat the user's annotated EVM images as placement and power-routing references, together with their accompanying text. Do not substitute a generic layout for those references.
- No fixed board outline or mounting-hole positions have been imposed. The earlier approximately 50 x 50 mm proposal was not a mandatory dimension.

## 2. Device, gain, procurement, and signal connections

- Use the THS3491 **RGT** package for the active design, its TI model for simulation, and the RGT EVM as the circuit/layout reference. Earlier DDA work is historical comparison material.
- Target a noninverting gain of approximately 20 V/V. The user permits a commercially available feedback resistor near 383 ohms; an exact 383-ohm value is not mandatory.
- The current working choice is RF = 390 ohms and RG = 20.5 ohms, giving nominal gain `1 + RF/RG = 20.02439 V/V`. This is the selected implementation value, not a new requirement to reject other suitable nearby values.
- Check JLCPCB component availability for the RGT design and the selected gain-setting values. Preserve EVM component functions when selecting substitutes.
- Screw-tightened power terminals are not required. A different SMA part is acceptable, provided its footprint and RF launch are properly adapted.
- Remove the EVM output attenuator. In the current RGT design, R9-R13 are omitted; the working output arrangement retains the 49.9-ohm series resistor and a 1-megohm load at the node labeled `output`.
- Preserve both input ports, including the inverting-input SMA and its EVM configuration positions. Do not delete the negative-input connector or permanently replace its entire network with a ground connection.
- Default assembly follows the user's explicit choice: **R2 = 0 ohms fitted, negative-input port retained; remove R2 when needed for an alternate configuration.**
- Keep the noninverting input labeled `inpt` and the loaded output labeled `output` in the simulation circuits.

## 3. TI EVM placement and RF routing

- Follow the actual TI RGT EVM drawing/source for RF component placement, orientation, and routing, especially at the input connectors and near U1.
- Preserve the EVM's curved RF routing where applicable. Do not replace it with unrelated angular routes or change component placement merely to simplify drawing generation.
- RF traces must flow through the appropriate SMD signal pads in the main signal path. Avoid a main RF line with a side branch or stub leading to a component that should sit directly in that path.
- Latest L2 requirement: clear ground copper directly beneath RF signal-component pads. Apply localized pad windows to the 18 signal pads on R1-R7, R14 and U1 I/O; retain grounded pads, the U1 exposed thermal pad, and continuity of the surrounding reference plane. The present 0.10-mm pad-window margin is a layout choice, not a validated impedance optimum.
- Give particular attention to the input termination/configuration components, feedback network, amplifier pins, and output launch.
- Design for signal integrity, power integrity, and EMC. Visual similarity to an EVM alone does not establish these properties.
- Use an actual JLCPCB four-layer stackup as the impedance-design basis. Determine the coplanar-waveguide signal width and signal-to-ground gap from the selected stackup, copper, dielectric, and manufacturing assumptions; do not use arbitrary gaps or numbers from a different stack.
- The TI layout is a placement/routing reference. Adapting it to a different layer stack still requires checking the RF return path, discontinuities, and relevant copper clearances.

## 4. Power distribution and symmetry

- Use broad copper areas/planes for the main power distribution, including local power copper on **L1**. Do not feed the amplifier with a long, narrow L1 power trace.
- The agreed four-layer arrangement is L1 for RF/local power/GND, L2 for the GND reference, L3 for the VCC/VEE power areas, and L4 for GND/thermal support.
- Follow this supply path for each rail:

  `Power input -> local raw-supply L1 copper -> filter bead -> small filtered-supply L1 copper with parallel vias -> L3 power plane -> parallel vias immediately before U1 -> small local L1 supply copper -> U1 supply pins`

- Group the parallel supply vias inside one local copper area to reduce connection inductance. Avoid isolated vias joined by long narrow traces.
- Place the negative supply input block on the opposite side, symmetrically relative to the positive supply input block.
- In the top view, place the negative-supply input capacitor arrangement to the **left** as indicated in the user's reference image.
- Preserve the raw-input and filtered-output sides of the supply bead as distinct nets/copper areas.
- Latest input-block correction: make the raw-input and filtered-supply L1 polygons rectangular. Put C1/C2 and C3/C4 component centers on the corresponding rectangle boundaries, with GND pads outside their supply polygons. Move negative-side C2/C4 upward and adjust L2 bead to maintain straight boundaries; apply 180-degree-symmetric changes to C1/C3/L1. Remove overlapping auxiliary vias while keeping deliberate via-in-pad connections.
- Latest entry-plane/via correction: widen the filtered VEE and opposite VCC entry islands from 2.8 mm to 6.0 mm, keeping their capacitor-center boundaries and 180-degree symmetry. Add a 4-by-4 array per rail, using 0.40-mm pads, 0.20-mm drills and 0.80-mm pitch, connected to the same rail on L3. Remove the three GND stitching vias conflicting with the enlarged VEE boundary. The user wrote VSS; this is interpreted as the opposite VCC (+15 V) rail because no VSS net exists.
- Near U1, retain local supply islands rather than extending the inlet power area across the RF region.
- PD is the explicit exception to the main-supply plane-routing rule: a thin trace and a separate via are sufficient for that control pin, as detailed below.

## 5. Bypass capacitors: latest placement correction

- **Only C5 and C6 are the immediate, close-to-U1 bypass capacitors**, following the TI EVM positions and orientations. Both are 100 nF in the current design.
- Place C3/C4, the 1-uF capacitors, toward the corresponding input-filter areas. Do not retain an extra pair beside U1 merely because an earlier revision put them there.
- C5/C6 placement must follow the EVM. Do not move either away from its EVM position solely to obtain exact rotational symmetry of the complete local layout.
- Keep each bypass capacitor's GND pad outside the corresponding L1 power copper. A GND pad must not overlap or short into a VCC/VEE polygon.
- The user's latest clarification is: **make the C5-side power arrangement like the C6-side arrangement.** Use a small supply-pin-only copper area containing the capacitor's supply pad and its supply-via group.
- For C5, that local VCC area connects to VS+ pins 13/14. Do not widen it across the neighboring NC and PD pins.
- For C6, retain the corresponding small VEE area connecting its supply pad, via group, and VS- pins 7/8.

## 6. PD, NC, and ground connections

- **PD, U1 pin 16:** route a thin L1 trace to a separate via, then connect to L3 VCC. Keep the existing enabled-state electrical connection; a large L1 power island around PD is unnecessary.
- **NC, U1 pin 15, between PD and VS+:** connect it to the surrounding **L1 GND plane/pour**, as explicitly requested for this THS3491 RGT design.
- Keep a continuous GND connection from NC15 into the surrounding ground copper between the PD route and the VS+ island. Do not leave NC15 floating or trapped in an isolated ground patch inside a power island.
- Apply the NC15 instruction to this specific device/pin; it is not a blanket rule for every pin labeled NC on other components.
- Check all intended U1 ground connections, including the exposed pad and relevant ground-connected package pads. The user explicitly rejected a layout with U1 ground connections missing.
- Preserve the local supply-to-ground clearances when adding vias or repouring polygons.

## 7. Vias, pad connections, and assembly

- Use via-in-pad where requested for the local power/bypass and ground connections. Maintain compact groups of supply vias within the associated copper island.
- The later PD instruction permits a separate via reached by a thin trace; it does not require placing that via on the small PD pin pad.
- Include deliberate thermal-relief/thermal-gap treatment for pad-to-plane connections. Do not leave this unspecified or assume every pad can simply merge into a plane without considering solderability.
- Any direct-connect exception needed for high-frequency bypass, exposed-pad grounding, or heat flow must be explicit and justified in the implementation notes; it must not silently replace the thermal-relief requirement for all pads.
- Confirm the manufacturing treatment of via-in-pad locations and assembly constraints when producing fabrication data. A drawing of a via in a pad is not itself a fabrication-process definition.

## 8. TEMP access and requested explanations

- Provide the requested **2.54-mm-pitch** pin access for TEMP and GND so jumper leads can be used. Keep it out of the critical RF path.
- The current working interpretation is a two-pin measurement header: pin 1 TEMP, pin 2 GND. It is not a request to short TEMP to GND with a jumper cap.
- Explain the TEMP pin's role alongside the design. Its purpose is temperature observation; do not treat it as part of the RF gain-setting network.
- Explain the functions of EVM R9/R10/R11 and show them highlighted on the EVM schematic when documenting the attenuator removal. Distinguish the output loading/attenuation network from the amplifier feedback gain resistors.
- Do not silently remove the requested TEMP access based on the earlier ambiguous question about whether a feature was needed; retain the explicitly requested access unless the user specifies its removal.

## 9. Simulation conditions and comparison records

- Obtain the amplifier models from TI and use the package-appropriate model and EVM circuit.
- Simulate input pulses with the requested **3.33-ns rise time** and amplitudes of **100, 200, 300, 400, 500, 600, 700, and 800 mV**. The original text "800 V" was explicitly corrected to "800 mV."
- The source output impedance is **50 ohms**.
- The stated 100-800 mV amplitudes mean the voltage obtained when that source drives a **1-megohm load**. They are not the voltage already present at the EVM's approximately 50-ohm input termination. Include source/loading effects consistently and identify the plotted node.
- State the rise-time convention used. Existing simulations interpreted 3.33 ns as the 10%-90% rise time; this convention must not be silently changed between comparisons.
- Retain comparisons with THS4021 and the requested THS3491 gain cases: G = 10 V/V with RF = 499 ohms, and G = 20 V/V with RF = 383 ohms. Derive RG for the specified gain and distinguish exact-gain simulations from standard-value BOM approximations.
- Re-evaluate the RGT circuit and selected stock resistor values rather than assuming DDA results are interchangeable.
- Provide comparison plots and LTspice circuit drawings with their assumptions. Do not present ideal/macromodel transient results as validation of PCB SI, PI, EMC, or thermal performance.

## 10. Superseded choices and implementation status

The following later instructions override earlier suggestions or revisions:

| Earlier request or implementation | Governing correction |
| --- | --- |
| KiCad as the main editable deliverable | Native Altium schematic and layout are required. |
| Negative-input port removed or permanently grounded as a whole | Retain the EVM negative-input port and configuration network; fit R2 = 0 ohms by default. |
| C3/C5 or two capacitor pairs placed immediately beside U1 | Use only C5/C6 immediately beside U1, in the EVM positions; move C3/C4 toward the input filters. |
| Exact symmetry applied to every local bypass position | Preserve C5/C6 EVM positions; apply the requested symmetry to the supply-input blocks. |
| Broad VCC island extending across PD16 and NC15 | C5-style island limited to VS+13/14; PD16 uses its own trace/via, NC15 joins surrounding GND. |
| Plane-only treatment assumed for every VCC connection | PD16 has an explicit thin-trace/separate-via exception. |
| Continue editing or launching Altium during the latest discussion | Produce planning drawings only until the user asks to apply them. |

The latest capacitor and PD/NC corrections were first represented in planning drawings. They have now been applied to the native **Altium Rev D** PCB. They have **not** been applied to the historical Rev C documents. Older Rev C descriptions and images therefore describe superseded geometry.

## 11. Follow-up implementation: Rev D (2026-10-22)

- C5/C6 retain their recorded TI EVM coordinates and orientations; C3/C4 move to the input filters.
- C5 and C6 use compact local supply islands. PD16 uses a 0.15-mm L1 route and a separate via. NC15 has continuous surrounding L1 GND copper, checked on the filled geometry.
- TEMP escape routing is adjusted to clear C6. The input rectangle correction removes overlapping entry-via rows and stitching vias; deliberate capacitor/bead via-in-pad connections remain.
- Rev D reconciles contradictory inherited V8 two-layer-flex metadata with the actual V9 four-layer rigid stack. The actual `Tracks6 / Creating InternalPlaneLayer(0)` exception was caused by writing extended layer IDs at byte 40 instead of 41. All track IDs are repaired, and pad extended IDs now agree with their legacy layers (66 top, 7 bottom, 11 multilayer). Legacy inactive Internal Plane slots remain outside the active copper stack.
- Native-file re-import checks 4 copper layers, 35 components, 84 pads, 650 vias and 3 preserved RF arcs. Independent DRC reports zero errors and zero unconnected pads, with one inherited auxiliary-arc endpoint warning.
- The user's final shape correction requires all 21 target pads (R14: 2, R15: 2, U1: 17) to be sharp rectangles with zero corner radius, superseding the earlier rounded-rectangle restoration. Apply Altium's native Rectangle shape and verify zero radius after save and reopen; refill surrounding copper for the changed corners. The redundant C7 VCC/VEE surface polygons are removed; both via-in-pad supply connections remain. All 84 pad shapes are independently audited.
- Altium 25.8.1 open/save/reopen is verified through its native scripting API. The delivered file was saved by Altium, which regenerated the missing file-version information; reopening created no new conversion report. Native ERC, repour and DRC, and SI/PI/EMC/thermal/manufacturing validation remain pending. See [Rev D notes](hardware/THS3491_RGT_G20/altium_revD/README.md) and its validation records.

Reference identifiers used in this work: TI THS3491 RGT EVM guide SLOU483, TI HSP006A design source, and the user's annotated EVM images. Stackup dimensions, procurement availability, and completed validation must be documented from the actual implementation rather than inferred from this requirements record.

## 12. Output and assembly follow-up (2026-10-27)

- Remove R15, the physical 1-Mohm output load, from schematic, PCB, BOM and placement data. Preserve R14 and the main output route. This does not change the simulation source-amplitude convention in section 9.
- Remove the two explanatory board silk notes (`TI RF geometry / JLC 4L adaptation` and `QSTL / THS3491 RGT / REV D`); retain functional power/header labels.
- Embed 3D models for all 24 fitted components. DNP R5, bare solder/test pads and bare mounting holes have no body. Standard package and simplified mechanical models must be identified.
- Current counts supersede section 11: 34 PCB components, 82 pads (64 top, 7 bottom, 11 multilayer), 650 vias, 19 sharp target pads and 18 RF-pad L2 windows. Native save/reopen, 24 embedded model placements and 121 checks passed. Independent DRC: zero errors, zero unconnected pads, one inherited RF-arc warning. Altium screenshot, native ERC/DRC and manufacturing review are not claimed.

## 13. Adapter-only supply inputs (2026-10-28)

- The latest user instruction cancels banana sockets: fit two DC barrel inputs only.
- J9 is the +15 V input (center VIN_P, sleeve GND); J10 is the -15 V input (center VIN_N, sleeve GND). Their third switched-sleeve terminals are NC. Mark voltage and polarity on the top silkscreen. No voltage or polarity conversion is implemented.
- Use Same Sky PJ-102AH, 5.5/2.1 mm mating plug, connector rating 24 VDC / 5 A. Specify manual THT assembly and exact manufacturer MPN; JLC stocked supply is not verified.
- Remove obsolete J4/J5/J6/J8 wire pads from PCB, schematic and BOM. Connect the new inputs before existing ferrite filters. Keep the original 41.65601 x 68.58 mm outline, mounting holes, RF circuit, rectangular supply islands, filtered via arrays and L2 RF-pad windows.
- Remove only the eight GND stitching vias overlapping new pads or power routes. Current counts supersede section 12: 32 PCB components, 84 pads (64 top, 7 bottom, 13 multilayer), 642 vias, 42 signal tracks, 3 RF arcs and 26 embedded models (11 assets).
- Altium save/reopen and 123 design checks passed. Independent copper DRC has zero errors and zero unconnected pads, with the same inherited RF-arc warning. Nominal model clearance is at least 3.92 mm for J9 and 5.1352 mm for J10 against the other fitted bodies and a 6 mm mounting-screw envelope. Native ERC/DRC, direct app screenshots and manufacturing approval are not claimed.

## 14. Positive input plane outline (2026-10-28 follow-up)

- The user clarified the blue annotation as a VIN_P copper-outline change, not a connector-pin relocation. Expand only L1_POSITIVE_INPUT into the marked L shape. Keep C1/L1 centered on the existing filter-region boundaries. This supersedes the raw positive-input rectangle while retaining the filtered rectangular islands.
- Preserve all pins, components, tracks, vias, mounting holes, models, negative input and schematic connectivity. J9 pin 1 is center/VIN_P, pin 2 sleeve/GND, pin 3 unused sleeve switch. The switch closes 2 to 3 without a plug and opens on insertion; no PCB trace is connected to pin 3.
- The saved outline area is 99.47 mm² (previously 46.00 mm²). VIN_P clearance is at least 0.2055 mm from pad 2 and 1.10 mm from pad 3. Pad 2 remains connected to L2 and bottom GND. Altium save/reopen and 125 checks passed; independent DRC remains zero errors, zero unconnected pads, one inherited warning.

## 15. Apply the input plane expansion to both rails (2026-10-28)

- The user's follow-up explicitly extends section 14 to both inputs. Retain the expanded VIN_P and also expand VIN_N into an L-shaped connection between its existing input filter and J10. Keep all connector pin positions, components, tracks, vias and RF geometry unchanged.
- Both rails have at least 0.2055 mm clearance to their GND pad 2 and 1.10 mm to their unused switch pad 3. Retain pad 2 GND connections on L2 and bottom copper; pin 3 has no PCB net. The respective polygon-outline areas are 99.47 and 143.26192 mm².
- The delivered board passed Altium save/reopen, 26 embedded-model placement checks and 127 design checks. Independent DRC remains zero errors, zero unconnected pads and one inherited RF-arc warning.

## 16. L2-only RF cutouts, VIN_P vias and broad bottom GND exposure (2026-10-28)

- Remove the six inherited RF cutout objects on L3 and L4. Preserve L2's 18 pad-specific and three local windows, the top-layer local clearances, and the existing L3 separation between supply planes. These are copper voids, not physical drilled holes.
- Remove the 12 GND stitching vias whose copper/clearance clips the VIN_P outline. Preserve all other vias, including filtered supply arrays and thermal vias. This supersedes the via-preservation constraint of section 15; the new total is 630.
- The user explicitly selected broad bottom GND exposure, with component and connector pin vicinity protected by solder mask. Expose about 2350.23 mm2 of actual bottom GND, leaving at least 0.30 mm around pin projections and non-GND vias and approximately 0.50 mm at the board perimeter. The central U1 EP underside must be exposed. Existing pad mask/paste settings, including the separate H9 heatsink solder pad, stay unchanged.
- Preserve schematic connectivity, all components/pads/tracks/arcs, board outline and mounting holes, and all 26 embedded models. Validate the final native Altium save/reopen, actual saved mask contours, pin protection, copper geometry and independent DRC. Do not claim direct application screenshot verification.

## 17. Local L3 supply corridors with GND elsewhere (2026-10-28)

- Follow the user's annotated routes: localize filtered VCC/VEE from their input via arrays to the amplifier and fill the remaining L3 area with GND. Preserve every supply via connection, including C7 outside the main paths through 0.30 mm branches.
- Remove seven GND stitching vias that otherwise disconnect the VCC corridor; retain a verified 0.80 mm bridge. All other vias remain, for 623 total. This supersedes section 16's blanket preservation of other vias only for these seven listed positions.
- Preserve components, pads, tracks, RF arcs, mounting holes, models and schematic connectivity; preserve L1/L2/L4 copper and the broad bottom GND mask. Actual saved L3 copper areas are about VCC 77.60 mm2, VEE 74.76 mm2 and GND 2463.59 mm2, with power-to-ground clearance above 0.204 mm.
- Check Altium save/reopen, all 47 power-via connections, continuous VCC and VEE, C7 connectivity, the narrow bridge, remaining GND fill, and independent copper DRC. Exact design and evidence are in `l3_local_power_intent.json` and `review/l3_local_power_check.json`.

## 18. RF 3W shield vias (2026-10-28)

- Add GND shield vias around the RF input curves, output route and RF component perimeter. Apply 3W as copper-edge clearance, W=0.3058 mm and minimum gap=0.9174 mm. This is the stated implementation assumption; a center-to-center definition would be a different design.
- Add 98 vias (0.40 mm copper / 0.20 mm drill), reuse 29 existing qualified fence vias, and preserve every existing via. The resulting total is 721. Use 0.90 mm nominal pitch with local outward adjustments and 17 obstructed/protected sample locations omitted; do not claim a closed enclosure or uniform maximum pitch.
- New vias must sit entirely within GND on all four layers, clear pins and holes, and preserve the L2 RF windows, L3 power corridors/bridge, broad bottom mask, component/pad placement, RF traces/arcs, schematic and 26 embedded models. Verify the actual native saved file and independent DRC.
- Correct the stale `RunShapeRepair` entry-point error. Current commands use `ShapeRepair`; the generator supports both names. Legacy candidate projects must not apply stale edits to the current board.

## 19. Circular via rings around mechanical mounting holes (2026-10-28)

- Place 24 GND vias around each of H1/H2/H3/H4 at radius 3.40 mm and 15-degree intervals. Use 0.40 mm copper / 0.20 mm drills, yielding about 0.888 mm adjacent-center pitch. Add exactly 96 vias, preserving all previous 721, for 817 total.
- Preserve the four original 3.175 mm NPTH mounting holes and their positions, the board outline, existing RF fence, all component/pad/trace/arc geometry, copper outlines/cutouts, bottom mask, schematic and 26 embedded models. Connect each added via to GND on all four copper layers without perforating power corridors.
- The ring lies outside the existing nominal 6 mm screw-head review envelope with 0.20 mm copper clearance. Keep that nominal assumption distinct from validation of a particular screw or washer.
- Verify complete circular placement, native save/reopen, original-hole preservation, via drilling clearances and independent DRC; record coordinates and evidence in `mount_hole_ring_intent.json` and `review/mount_hole_ring_check.json`.

## 20. Board-edge GND via fence (2026-10-28)

- Add a perimeter row on all four edges. Use 1.00 mm center inset, 1.00 mm nominal pitch, and 0.40 mm copper / 0.20 mm drill. New via copper remains 0.80 mm inside the board edge.
- Add 148 vias and reuse 50 existing vias at perimeter targets. Omit 16 targets around RF connector pads to preserve pin clearances and 3W copper-edge spacing. Total vias: 965. Do not interpret nominal pitch as the maximum gap around connectors.
- Connect new vias to GND on all four copper layers. Preserve all previous 817 vias, including mounting-hole rings and RF fencing, and all holes, component/pad placement, tracks/arcs, copper outlines/cutouts, bottom mask, schematic and 26 embedded models.
- Validate native save/reopen, exact via placement, all-layer GND coverage, edge/pad/RF/drill clearances and independent DRC. Record coordinates in `edge_via_intent.json` and results in `review/edge_via_check.json`.

## 21. Remove the isolated TP1 GND test point (2026-10-28)

- Remove TP1 at (31.49601, 21.8948) mm from the board top origin. Remove its 1.4779 mm pad and 0.9779 mm plated hole, the schematic test-point component and its private GND branch/label, and its BOM entry.
- Restore GND copper on all four layers and remove only its obsolete bottom-mask protection island. Restrict copper/mask changes to radius 1.10 mm around the former TP1 center.
- Preserve every other component, pad, track, arc, outline, copper boundary/cutout, schematic object and all 965 vias and 26 embedded models. Current counts: 31 PCB components, 83 pads.
- Verify native PCB/schematic save and reopen, complete native import and DRC, and exact comparison to the immediately preceding 168-check baseline. Record the new 49-check proof separately; do not relabel historical feature audits as rerun against the new file.
