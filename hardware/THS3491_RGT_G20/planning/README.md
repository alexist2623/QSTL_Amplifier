# Latest power and bypass placement plan

The subsequent [native Rev D review snapshot](../altium_revD/README.md) now
implements these corrections. These planning drawings remain the original intent record.

These are planning illustrations, created without launching Altium or modifying the native Rev C schematic/PCB. They represent later corrections to the [Rev C snapshot](../altium_revC/README.md).

- [L1 overview](power_plan_L1.png)
- [U1, C5, and C6 detail](power_plan_core.png)
- [PD16, NC15, and VS+13/14 detail](power_plan_PD_NC.png)
- [L3 power-plane plan](power_plan_L3.png)

Editable SVGs, the drawing script, and `power_plan_intent.json` accompany the PNGs.

The intended changes are:

1. Preserve the TI EVM positions and orientations of C5/C6 beside U1; move C3/C4 toward the input filters.
2. Make the C5 supply island like the C6 island: a compact local supply area containing the capacitor supply pad, parallel vias, and the appropriate supply pins.
3. Route PD16 through a thin L1 trace and a separate via to L3 VCC.
4. Connect NC15 directly to the surrounding L1 GND copper, maintaining a ground connection between the PD route and the VS+ island.
5. Feed both local U1 supply areas from the internal power planes through nearby via groups. Keep capacitor GND pads outside the supply copper.

The drawings show connection and placement intent. Final polygon clearances, via geometry, manufacturing constraints, and CAD DRC have not been established by these illustrations. See [DESIGN_REQUIREMENTS.md](../../../DESIGN_REQUIREMENTS.md) for the complete requirements and precedence of later corrections.
