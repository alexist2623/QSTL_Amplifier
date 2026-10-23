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
- Latest L2 requirement: clear ground copper directly beneath RF signal-component pads. Apply localized pad windows to the 19 signal pads on R1-R7, R14/R15 and U1 I/O; retain grounded pads, the U1 exposed thermal pad, and continuity of the surrounding reference plane. The present 0.10-mm pad-window margin is a layout choice, not a validated impedance optimum.
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
