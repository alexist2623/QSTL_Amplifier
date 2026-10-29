"""Explicit later changes applied to historical preservation baselines."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def l3_intent():
    p=ROOT/'l3_local_power_intent.json'
    return json.loads(p.read_text()) if p.exists() else {}
def l3_zones(zones):
    intent=l3_intent()
    if not intent:return zones
    replace={q['name']:q['new_zone'] for q in intent['planes']}
    return [replace.get(z['name'],z) for z in zones]+[intent['added_ground_zone']]
def rf_intent():
    p=ROOT/'rf_fence_intent.json'
    return json.loads(p.read_text()) if p.exists() else {}
def before_rf_vias(vias):
    added=rf_intent().get('added_ground_vias',[])
    return [v for v in before_mount_vias(vias) if v not in added]
def mount_intent():
    p=ROOT/'mount_hole_ring_intent.json'
    return json.loads(p.read_text()) if p.exists() else {}
def before_mount_vias(vias):
    added=mount_intent().get('added_ground_vias',[])
    return [v for v in before_edge_vias(vias) if v not in added]

def edge_intent():
    p=ROOT/'edge_via_intent.json'
    return json.loads(p.read_text()) if p.exists() else {}

def before_edge_vias(vias):
    added=edge_intent().get('added_ground_vias',[])
    return [v for v in vias if v not in added]
