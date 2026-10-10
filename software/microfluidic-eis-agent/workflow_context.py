"""V2 planning metadata and backward-compatible Workshop/Fit Lab handoff."""
from __future__ import annotations

import math
from typing import Any

PLAN_FIELDS = (
    "research_question", "planned_comparison", "control_condition", "baseline_plan",
    "measurement_schedule", "measurement_settings", "export_plan", "metadata_plan",
)

PRESET_PLANS = {
    "Custom": {},
    "Endothelial drug-response barrier assay": {
        "research_question": "How does a test compound affect endothelial barrier function over time?",
        "planned_comparison": "Compare treated samples with vehicle controls at matched time points, accounting for each sample’s baseline.",
        "control_condition": "Vehicle control",
    },
    "MDCK apical-basal transport assay": {
        "research_question": "How does the selected experimental condition affect transport across an MDCK epithelial barrier over time?",
        "planned_comparison": "Compare samples under the selected condition with a defined control at matched time points, accounting for each sample’s baseline.",
    },
    "Barrier maturation time-course": {
        "research_question": "How do barrier-related electrical properties change during culture maturation?",
        "planned_comparison": "Compare repeated measurements with each sample’s initial biological baseline and a separately defined reference condition.",
    },
}


def clean_plan(values: dict[str, Any]) -> dict[str, str]:
    return {key: str(values.get(key, "") or "").strip() for key in PLAN_FIELDS}


def experiment_checklist(cells: list, conditions: list, readouts: list, plan: dict) -> list[tuple[str, bool]]:
    return [
        ("Biological model selected", bool(cells)),
        ("Control condition defined", bool(plan.get("control_condition"))),
        ("Experimental condition or perturbation defined", bool(conditions)),
        ("Measurement readout selected", bool(readouts)),
        ("Baseline and time points defined", bool(plan.get("baseline_plan") and plan.get("measurement_schedule"))),
        ("Data export and experimental metadata specified", bool(plan.get("export_plan") and plan.get("metadata_plan"))),
    ]


def valid_area(value: Any) -> float | None:
    if value is None or value == "":
        return None
    area = float(value)
    if not math.isfinite(area) or area <= 0 or area > 20:
        raise ValueError("Active sensing area must be a finite number greater than 0 and at most 20 cm².")
    return area


def build_fit_lab_template(package: dict, area_cm2: float | None) -> dict:
    selected = package.get("selected_template", {})
    req = package.get("requirement", {})
    theory = package.get("theory_and_fitting", {})
    return {
        "schema_version": 2,
        "source": "Chip Design Workshop V2",
        "template_key": selected.get("key", "custom"),
        "template_name": selected.get("name", "Custom chip design"),
        "active_area_cm2": valid_area(area_cm2),
        "cells": req.get("cells", []),
        "drugs": req.get("drugs", []),
        "readouts": req.get("electrical", []),
        **clean_plan(req),
        "sample_context": {"sample_id": "", "sample_condition": "", "time_point": "", "biological_replicate": "", "chip_id": "", "operator_date": ""},
        "workflow_status": "draft awaiting researcher review",
        "equivalent_circuit": theory.get("equivalent_circuit", "Z(w) = Z_CPE(A,n) + R_bulk + Z_cell(CLER,CLEC)"),
        "parameter_bounds": theory.get("parameter_bounds", {}),
    }


def load_fit_lab_template_from_package(package: dict) -> dict:
    if not isinstance(package, dict) or not isinstance(package.get("selected_template"), dict):
        raise ValueError("Select a Workshop JSON package with a selected_template object.")
    req = package.get("requirement", {})
    if not isinstance(req, dict):
        raise ValueError("The workflow requirement must be an object.")
    template = build_fit_lab_template(package, req.get("active_area_cm2"))
    embedded = package.get("fit_lab_template")
    if embedded is not None:
        if not isinstance(embedded, dict):
            raise ValueError("The Fit Lab template must be an object.")
        template.update(embedded)
    template["active_area_cm2"] = valid_area(template.get("active_area_cm2"))
    for key in ("cells", "drugs", "readouts"):
        if not isinstance(template.get(key), list):
            raise ValueError(f"The template {key} field must be a list.")
    if not isinstance(template.get("sample_context"), dict):
        raise ValueError("The sample context must be an object.")
    return template
