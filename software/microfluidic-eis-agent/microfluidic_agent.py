from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT.parents[1]
AREA_CM2_DEFAULT = 0.1962
DEFAULT_OPENAI_MODEL = "gpt-5.5"


@dataclass
class LiteratureSource:
    key: str
    title: str
    path: str
    role: str
    tags: list[str]
    design_use: str
    knowledge_scope: list[str]
    agent_policy: str


@dataclass
class ChipTemplate:
    key: str
    name: str
    best_for: list[str]
    cell_models: list[str]
    architecture: list[str]
    ports: list[str]
    electrodes: list[str]
    measurement: list[str]
    tuning_rules: list[str]
    source_keys: list[str]


FOUNDATIONAL_SOURCES = [
    LiteratureSource(
        key="mai_2023_endo",
        title="2023 Mai XC - Endo",
        path=str(DATA_ROOT / "2023 Mai XC - Endo.pdf"),
        role="Foundational endothelial barrier chip and EIS reference",
        tags=["endothelial", "barrier", "EIS", "open-cell", "TEER"],
        design_use=(
            "Use as the default endothelial/open-cell barrier design reference, "
            "especially when the user asks for vascular/endothelial cells, time "
            "resolved barrier maturation, or drug disruption of barrier integrity."
        ),
        knowledge_scope=[
            "endothelial barrier chip template",
            "open-cell or perfusable EIS measurement layout",
            "barrier maturation and drug-response workflow",
            "CLER/TEER-oriented fitting outputs",
        ],
        agent_policy="Always load as a foundational knowledge source; prioritize it for endothelial or vascular requests.",
    ),
    LiteratureSource(
        key="june_2023_mdck",
        title="2023 June LF MDCK MF",
        path=str(DATA_ROOT / "2023 June LF MDCK MF.pdf"),
        role="Foundational MDCK microfluidic membrane/filter chip reference",
        tags=["MDCK", "epithelial", "membrane", "microfluidic", "barrier"],
        design_use=(
            "Use as the default epithelial/transwell-like membrane design reference, "
            "especially for MDCK, apical-basal compartmentalization, permeability, "
            "or drug transport experiments."
        ),
        knowledge_scope=[
            "MDCK or epithelial barrier chip template",
            "membrane/filter-supported microfluidic architecture",
            "apical-basal drug exposure and receiver sampling",
            "EIS fitting adapted to membrane-supported monolayers",
        ],
        agent_policy="Always load as a foundational knowledge source; prioritize it for MDCK, epithelial, transport, or permeability requests.",
    ),
]


CHIP_TEMPLATES = [
    ChipTemplate(
        key="endo_open_eis",
        name="Endothelial open-cell EIS barrier chip",
        best_for=[
            "iPSC-derived endothelial cells, primary endothelial cells, vascular barrier models",
            "drug-induced barrier disruption or recovery",
            "dense longitudinal EIS and TEER monitoring",
        ],
        cell_models=["endo", "endothelial", "hbmec", "huvec", "vascular", "ips"],
        architecture=[
            "Open culture chamber above a patterned electrode region",
            "Perfusable medium path with low dead volume around the sensing zone",
            "Cell layer grown directly over the EIS-sensitive region or membrane support",
            "Separate cell-free reference from the biological vehicle-control comparison; review any correction method",
        ],
        ports=[
            "Inlet: culture medium or drug solution",
            "Outlet: waste and optional time-point fraction collection",
            "EIS port pair: working/counter or four-wire-compatible measurement pads",
            "Optional bubble trap upstream of the cell chamber",
        ],
        electrodes=[
            "Planar electrodes aligned under the cell barrier region",
            "Gold, platinum, ITO, or carbon electrodes depending on fabrication route",
            "Geometry should keep the active electrode area constant across conditions",
            "Include blank electrodes for medium/background impedance subtraction",
        ],
        measurement=[
            "Frequency sweep: 5 Hz to 100 kHz as the default range",
            "Small-signal AC amplitude: 5-20 mV rms, below stimulation thresholds",
            "Cell-free reference before seeding; biological sample baseline after stabilization and before the selected condition; proposed repeated measurements thereafter",
            "Analyze CLER/Rbarrier, cell-layer capacitance, CPE exponent, and Rbulk",
        ],
        tuning_rules=[
            "Increase channel width or chamber area when low-noise TEER is prioritized",
            "Use parallel replicate lanes when comparing more than three drug conditions",
            "Use lower shear for fragile endothelial monolayers during early attachment",
            "Add a no-cell channel when medium conductivity or electrode drift may change",
        ],
        source_keys=["mai_2023_endo"],
    ),
    ChipTemplate(
        key="mdck_membrane_filter",
        name="MDCK membrane-filter microfluidic barrier chip",
        best_for=[
            "MDCK and epithelial monolayers",
            "apical-basal drug exposure or permeability workflows",
            "barrier models that require porous membrane support",
        ],
        cell_models=["mdck", "epithelial", "caco", "kidney", "transport", "permeability"],
        architecture=[
            "Two-compartment microfluidic design separated by a porous membrane/filter",
            "Apical channel for epithelial culture and drug exposure",
            "Basal channel for receiver medium, sampling, or counter exposure",
            "Membrane region registered to electrode or measurement windows",
        ],
        ports=[
            "Apical inlet/outlet for cell seeding, washing, and drug dosing",
            "Basal inlet/outlet for receiver medium or counter-gradient dosing",
            "Electrical pads routed away from wet connections",
            "Optional sampling port for permeability assays",
        ],
        electrodes=[
            "Electrodes placed to sense across the membrane-supported monolayer",
            "Stable geometry across apical and basal compartments",
            "Blank membrane channel for filter/background correction",
            "Guard against bubble contact at electrode surfaces",
        ],
        measurement=[
            "Frequency sweep: 5 Hz to 100 kHz, with emphasis on mid-frequency barrier arc",
            "Record a cell-free membrane/filter reference, then a biological sample baseline after stabilization and before the experimental condition",
            "Fit barrier resistance, membrane/cell capacitance, Rbulk, and electrode CPE",
            "Pair EIS with permeability readout when drug transport is part of the question",
        ],
        tuning_rules=[
            "Choose this template when apical-basal polarity is central to the biology",
            "Tune membrane pore size and coating to the target epithelial phenotype",
            "Use matched flow rates in apical and basal channels to avoid pressure-driven leakage",
            "Add receiver sampling when the drug readout includes transport or permeability",
        ],
        source_keys=["june_2023_mdck"],
    ),
]


def source_inventory() -> pd.DataFrame:
    rows = []
    for src in FOUNDATIONAL_SOURCES:
        path = Path(src.path)
        rows.append(
            {
                "key": src.key,
                "title": src.title,
                "available": path.exists(),
                "file": path.name,
                "role": src.role,
                "knowledge_scope": "; ".join(src.knowledge_scope),
                "policy": src.agent_policy,
            }
        )
    return pd.DataFrame(rows)


def foundational_knowledge_base() -> list[dict[str, Any]]:
    """Return the fixed local paper knowledge base used by every agent run."""
    kb = []
    for src in FOUNDATIONAL_SOURCES:
        item = asdict(src)
        item["available"] = Path(src.path).exists()
        item["file_name"] = Path(src.path).name
        item["status"] = "active_foundational_source" if item["available"] else "missing_file"
        kb.append(item)
    return kb


def parse_requirement(text: str, cells: list[str], drugs: list[str], electrical: list[str]) -> dict[str, Any]:
    combined = " ".join([text, " ".join(cells), " ".join(drugs), " ".join(electrical)]).lower()
    tokens = set(combined.replace(",", " ").replace(";", " ").split())
    return {
        "raw_text": text.strip(),
        "cells": [c.strip() for c in cells if c.strip()],
        "drugs": [d.strip() for d in drugs if d.strip()],
        "electrical": [e.strip() for e in electrical if e.strip()],
        "keywords": sorted(tokens),
        "needs_membrane": any(k in combined for k in ["mdck", "epithelial", "apical", "basal", "permeability", "transport", "filter", "membrane"]),
        "needs_endo": any(k in combined for k in ["endo", "endothelial", "vascular", "huvec", "hbmec", "ips"]),
        "needs_longitudinal": any(k in combined for k in ["time", "longitudinal", "kinetic", "maturation", "recovery", "washout", "时间", "动态"]),
        "needs_drug": bool(drugs) or any(k in combined for k in ["drug", "dose", "compound", "药", "给药"]),
    }


def select_template(req: dict[str, Any]) -> tuple[ChipTemplate, list[str]]:
    scores: dict[str, int] = {}
    reasons: dict[str, list[str]] = {}
    text = " ".join(req["keywords"])
    for template in CHIP_TEMPLATES:
        score = 0
        why = []
        if any(model in text for model in template.cell_models):
            score += 4
            why.append("cell model keywords match this template")
        if template.key == "mdck_membrane_filter" and req["needs_membrane"]:
            score += 3
            why.append("request suggests membrane, apical-basal, transport, or epithelial workflow")
        if template.key == "endo_open_eis" and req["needs_endo"]:
            score += 3
            why.append("request suggests endothelial or vascular barrier workflow")
        if req["needs_longitudinal"]:
            score += 1
            why.append("longitudinal EIS can be supported with repeated sweeps")
        if req["needs_drug"]:
            score += 1
            why.append("drug perturbation can be mapped to dosing ports and time points")
        scores[template.key] = score
        reasons[template.key] = why
    selected = max(CHIP_TEMPLATES, key=lambda t: scores[t.key])
    if scores[selected.key] == 0:
        selected = CHIP_TEMPLATES[0]
        reasons[selected.key].append("no strong biological keyword detected; endothelial EIS template used as conservative default")
    return selected, reasons[selected.key]


def build_design_package(req: dict[str, Any]) -> dict[str, Any]:
    template, reasons = select_template(req)
    drugs = req["drugs"] or ["experimental condition to be defined"]
    cells = req["cells"] or ["target barrier-forming cell type"]
    electrical = req["electrical"] or ["EIS", "TEER", "barrier resistance", "cell-layer capacitance"]
    knowledge_base = foundational_knowledge_base()
    sources = [src for src in knowledge_base if src["key"] in template.source_keys]
    background_sources = [src for src in knowledge_base if src["key"] not in template.source_keys]

    dosing = [
        "Record a separate cell-free reference measurement before cell seeding to characterize the device and medium.",
        "Seed cells under static or low-flow conditions until attachment is stable.",
        "Record maturation EIS sweeps until barrier parameters reach a plateau.",
        f"Experimental condition: {', '.join(drugs)}. Compare with the specified control: {req.get('control_condition') or 'to be defined'}. Define an appropriate biological replication plan.",
        f"Biological sample pretreatment baseline: {req.get('baseline_plan') or 'to be defined after culture stabilization, before applying the experimental condition'}.",
        f"Proposed measurement schedule (requires researcher review): {req.get('measurement_schedule') or 'not specified'}.",
        f"Measurement settings: {req.get('measurement_settings') or 'to be defined and checked'}.",
        "Use washout/recovery time points when reversible barrier disruption is expected.",
    ]
    if req["drugs"] == ["Culture maturation (no added perturbation)"]:
        dosing[-1] = "Continue the selected culture conditions; no added perturbation or washout is planned."
    elif template.key == "mdck_membrane_filter":
        dosing.insert(3, "Dose from the apical side by default; use basal dosing only when the biology requires counter-exposure.")
    else:
        dosing.insert(3, "Dose through the perfusion inlet after a stable pre-dose baseline is collected.")

    analysis = {
        "input_ports": [
            "Metadata: biological_model, experimental_condition, control_condition, sample_id, chip_id, sample_condition, time_point, biological_replicate, active_area_cm2, measurement_settings",
            "eis_spectra.csv or matrix CSV: frequency_hz, z_real_ohm, z_imag_ohm, condition labels",
            "optional_qc.csv: flow rate, temperature, medium conductivity, microscopy score",
        ],
        "outputs": [
            "fit_params.csv with Rbulk, Rbarrier/CLER, CLEC, CPE_A, CPE_n, chi2_red",
            "derived_metrics.csv with TEER_ohm_cm2, characteristic_frequency_hz, percent_change_vs_baseline",
            "plots: Nyquist, Bode magnitude/phase, residuals, parameter time course",
            "design_report.md with chip choice, protocol, model, fitting assumptions, and citations",
        ],
        "qc_rules": [
            "Reject spectra with missing frequency columns or non-monotonic frequency axis.",
            "Review the cell-free reference separately from the biological sample’s pretreatment baseline; define and validate any exclusion criteria.",
            "Fit real and imaginary components jointly with 1/|Z| weighting.",
            "Inspect residual structure before interpreting drug effects.",
            "Report confidence intervals for Rbarrier/TEER and capacitance when comparing groups.",
        ],
    }

    theory = {
        "equivalent_circuit": "Z(w) = Z_CPE(A,n) + R_bulk + Z_cell(CLER,CLEC)",
        "terms": [
            "Z_CPE = 1 / (A * (j*w)^n), representing non-ideal electrode/electrolyte polarization.",
            "Z_cell = CLER / (1 + j*w*CLEC*CLER), representing the cell barrier as parallel resistance-capacitance.",
            "TEER = CLER * active_area_cm2.",
            "f_char = 1 / (2*pi*CLER*CLEC).",
        ],
        "fitting": [
            "Use bounded nonlinear least squares on concatenated Re(Z) and Im(Z).",
            "Weight residuals by inverse impedance magnitude to balance frequency decades.",
            "Use several biologically plausible starts to reduce local-minimum dependence.",
            "Bootstrap residuals or use replicate-level mixed summaries for uncertainty.",
        ],
        "parameter_bounds": {
            "R_bulk_ohm": [0.1, 2000],
            "CLER_ohm": [0.1, 100000],
            "CLEC_uF": [0.001, 100],
            "CPE_n": [0.35, 1.0],
            "CPE_A_log10": [-11, -2],
        },
    }

    literature_queries = [
        f"{' '.join(cells)} organ-on-chip EIS barrier impedance",
        f"{' '.join(cells)} {', '.join(drugs)} TEER impedance",
        f"{template.name} equivalent circuit fitting cell barrier",
    ]

    return {
        "schema_version": 2,
        "workflow_status": "draft awaiting researcher review",
        "requirement": req,
        "selected_template": asdict(template),
        "selection_reasons": reasons,
        "knowledge_base": knowledge_base,
        "foundational_sources": knowledge_base,
        "selected_evidence": sources,
        "background_evidence": background_sources,
        "chip_design": {
            "cells": cells,
            "target_readouts": electrical,
            "architecture": template.architecture,
            "ports": template.ports,
            "electrodes": template.electrodes,
            "tuning": template.tuning_rules,
        },
        "assembly_instruction": [
            "Fabricate or prepare the microfluidic body and electrode substrate with verified alignment marks.",
            "Sterilize wet-contact parts using a material-compatible protocol.",
            "Prime all channels with bubble-free medium before introducing cells.",
            "Coat the sensing/membrane region with ECM matched to the selected cell type.",
            "Seed cells at a density high enough to form a confluent barrier over the active sensing area.",
            "Connect EIS pads after visual inspection confirms no trapped bubbles over electrodes.",
        ],
        "measurement_protocol": template.measurement + dosing,
        "data_analysis": analysis,
        "theory_and_fitting": theory,
        "literature_queries": literature_queries,
        "views": {
            "assay_summary": {
                "goal": req["raw_text"] or "Custom assay request",
                "cells": cells,
                "drugs": drugs,
                "readouts": electrical,
                "template_name": template.name,
                "source_titles": [src["title"] for src in sources] or [src["title"] for src in knowledge_base],
            },
            "build_view": {
                "title": "Build View",
                "architecture": template.architecture,
                "ports": template.ports,
                "electrodes": template.electrodes,
                "tuning": template.tuning_rules,
            },
            "operate_view": {
                "title": "Operate View",
                "assembly": [
                    "Fabricate or prepare the microfluidic body and electrode substrate with verified alignment marks.",
                    "Sterilize wet-contact parts using a material-compatible protocol.",
                    "Prime all channels with bubble-free medium before introducing cells.",
                    "Coat the sensing/membrane region with ECM matched to the selected cell type.",
                    "Seed cells at a density high enough to form a confluent barrier over the active sensing area.",
                    "Connect EIS pads after visual inspection confirms no trapped bubbles over electrodes.",
                ],
                "measurement": template.measurement + dosing,
            },
            "analyze_view": {
                "title": "Analyze View",
                "input_ports": analysis["input_ports"],
                "outputs": analysis["outputs"],
                "qc_rules": analysis["qc_rules"],
                "equivalent_circuit": theory["equivalent_circuit"],
                "terms": theory["terms"],
                "fitting": theory["fitting"],
                "parameter_bounds": theory["parameter_bounds"],
            },
        },
    }


def _strip_json_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def _normalize_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized = []
    for value in values:
        text = str(value).strip()
        if text:
            normalized.append(text)
    return normalized


def _merge_ai_views(base_package: dict[str, Any], ai_views: dict[str, Any], model: str) -> dict[str, Any]:
    merged = json.loads(json.dumps(base_package))
    views = merged.setdefault("views", {})

    summary = ai_views.get("assay_summary", {}) if isinstance(ai_views.get("assay_summary"), dict) else {}
    build = ai_views.get("build_view", {}) if isinstance(ai_views.get("build_view"), dict) else {}
    operate = ai_views.get("operate_view", {}) if isinstance(ai_views.get("operate_view"), dict) else {}
    analyze = ai_views.get("analyze_view", {}) if isinstance(ai_views.get("analyze_view"), dict) else {}

    views["assay_summary"].update(
        {
            "agent_summary": str(summary.get("agent_summary", "")).strip(),
            "design_focus": _normalize_string_list(summary.get("design_focus")),
            "risk_flags": _normalize_string_list(summary.get("risk_flags")),
        }
    )
    views["build_view"].update(
        {
            "overview": str(build.get("overview", "")).strip(),
            "architecture": _normalize_string_list(build.get("architecture")) or views["build_view"].get("architecture", []),
            "layer_stack": _normalize_string_list(build.get("layer_stack")),
            "ports": _normalize_string_list(build.get("ports")) or views["build_view"].get("ports", []),
            "electrodes": _normalize_string_list(build.get("electrodes")) or views["build_view"].get("electrodes", []),
            "design_decisions": _normalize_string_list(build.get("design_decisions")),
        }
    )
    views["operate_view"].update(
        {
            "overview": str(operate.get("overview", "")).strip(),
            "flow_path": _normalize_string_list(operate.get("flow_path")),
            "assembly": _normalize_string_list(operate.get("assembly")) or views["operate_view"].get("assembly", []),
            "measurement": _normalize_string_list(operate.get("measurement")) or views["operate_view"].get("measurement", []),
            "timeline_focus": _normalize_string_list(operate.get("timeline_focus")),
        }
    )
    views["analyze_view"].update(
        {
            "overview": str(analyze.get("overview", "")).strip(),
            "sensing_strategy": _normalize_string_list(analyze.get("sensing_strategy")),
            "input_ports": _normalize_string_list(analyze.get("input_ports")) or views["analyze_view"].get("input_ports", []),
            "outputs": _normalize_string_list(analyze.get("outputs")) or views["analyze_view"].get("outputs", []),
            "qc_rules": _normalize_string_list(analyze.get("qc_rules")) or views["analyze_view"].get("qc_rules", []),
            "fitting_focus": _normalize_string_list(analyze.get("fitting_focus")),
        }
    )
    merged["generation"] = {
        "mode": "openai_api",
        "model": model,
    }
    return merged


def generate_openai_design_package(req: dict[str, Any], api_key: str, model: str = DEFAULT_OPENAI_MODEL) -> dict[str, Any]:
    base_package = build_design_package(req)
    if OpenAI is None:
        raise ImportError("The OpenAI Python SDK is not installed. Add `openai` to requirements and reinstall dependencies.")
    if not api_key.strip():
        raise ValueError("An OpenAI API key is required for API-backed generation.")

    client = OpenAI(api_key=api_key.strip())
    payload = {
        "requirement": base_package["requirement"],
        "selected_template": base_package["selected_template"],
        "selection_reasons": base_package["selection_reasons"],
        "chip_design": base_package["chip_design"],
        "assembly_instruction": base_package["assembly_instruction"],
        "measurement_protocol": base_package["measurement_protocol"],
        "data_analysis": base_package["data_analysis"],
        "theory_and_fitting": base_package["theory_and_fitting"],
        "selected_evidence": [
            {
                "title": src["title"],
                "role": src["role"],
                "knowledge_scope": src["knowledge_scope"],
            }
            for src in base_package["selected_evidence"]
        ],
    }
    instructions = (
        "You are a microfluidic chip design copilot. "
        "Use the provided assay request, selected template, and local source summary to produce a concise chip-design package. "
        "Return only valid JSON with this exact top-level structure: "
        "{"
        "\"assay_summary\": {\"agent_summary\": string, \"design_focus\": [string], \"risk_flags\": [string]}, "
        "\"build_view\": {\"overview\": string, \"architecture\": [string], \"layer_stack\": [string], \"ports\": [string], \"electrodes\": [string], \"design_decisions\": [string]}, "
        "\"operate_view\": {\"overview\": string, \"flow_path\": [string], \"assembly\": [string], \"measurement\": [string], \"timeline_focus\": [string]}, "
        "\"analyze_view\": {\"overview\": string, \"sensing_strategy\": [string], \"input_ports\": [string], \"outputs\": [string], \"qc_rules\": [string], \"fitting_focus\": [string]}"
        "}. "
        "Keep recommendations grounded in the provided template and source summary. "
        "Do not invent exact fabrication dimensions or unsupported biological claims. "
        "If something depends on calibration or pilot testing, say so explicitly. "
        "Treat every output as a workflow draft requiring researcher review. "
        "Preserve the separate experimental condition, control, biological pretreatment baseline, and proposed measurement schedule. "
        "Distinguish a cell-free reference from the biological sample baseline. "
        "Do not invent sample identifiers, actual time points, measured settings, or numerical fit-quality acceptance thresholds. "
        "Respect explicitly stated no-perturbation maturation experiments. "
        "Interpret model-derived parameters together with fit quality and the assumptions of the electrical model."
    )
    response = client.responses.create(
        model=model,
        reasoning={"effort": "low"},
        instructions=instructions,
        input=json.dumps(payload, ensure_ascii=False, indent=2),
    )
    text = _strip_json_fence(response.output_text)
    if not text:
        raise ValueError("OpenAI returned an empty response.")
    try:
        ai_views = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OpenAI response was not valid JSON: {exc}") from exc
    return _merge_ai_views(base_package, ai_views, model)


def ask_openai_design_agent(
    package: dict[str, Any],
    section_key: str,
    user_message: str,
    api_key: str,
    model: str = DEFAULT_OPENAI_MODEL,
    chat_history: list[dict[str, str]] | None = None,
) -> str:
    if OpenAI is None:
        raise ImportError("The OpenAI Python SDK is not installed.")
    if not api_key.strip():
        raise ValueError("Add an OpenAI API key on the home page to use the design-agent chat.")
    if not user_message.strip():
        raise ValueError("Please enter a message for the design agent.")

    client = OpenAI(api_key=api_key.strip())
    history = chat_history or []
    trimmed_history = history[-8:]
    payload = {
        "current_section": section_key,
        "package_summary": {
            "requirement": package.get("requirement", {}),
            "selected_template": package.get("selected_template", {}),
            "selection_reasons": package.get("selection_reasons", []),
            "views": package.get("views", {}),
            "chip_design": package.get("chip_design", {}),
            "measurement_protocol": package.get("measurement_protocol", []),
            "data_analysis": package.get("data_analysis", {}),
            "theory_and_fitting": package.get("theory_and_fitting", {}),
        },
        "chat_history": trimmed_history,
        "user_message": user_message.strip(),
    }
    instructions = (
        "You are the side-panel design assistant inside a microfluidic chip design workshop app. "
        "Answer questions about the current assay package, explain design choices, and suggest concrete changes to the chip, protocol, or analysis plan. "
        "Stay grounded in the provided package. If the user asks for a change, describe what should be changed and why, but do not claim the saved package was already modified. "
        "Be concise, practical, and clear for a research user. "
        "If the current package lacks enough information, say exactly what is missing."
    )
    response = client.responses.create(
        model=model,
        reasoning={"effort": "low"},
        instructions=instructions,
        input=json.dumps(payload, ensure_ascii=False, indent=2),
    )
    text = (response.output_text or "").strip()
    if not text:
        raise ValueError("The design-agent chat returned an empty response.")
    return text


def _cpe_impedance(freq_hz: np.ndarray, a_log10: float, n: float) -> np.ndarray:
    omega = 2 * np.pi * freq_hz
    a = 10**a_log10
    return 1 / (a * np.power(1j * omega, n))


def model_impedance(freq_hz: np.ndarray, r_bulk: float, cler: float, clec_uF: float, n: float, a_log10: float) -> np.ndarray:
    omega = 2 * np.pi * freq_hz
    clec_f = clec_uF * 1e-6
    z_cell = cler / (1 + 1j * omega * clec_f * cler)
    return r_bulk + _cpe_impedance(freq_hz, a_log10, n) + z_cell


def parse_matrix_csv(file_or_path: Any) -> dict[str, Any]:
    df = pd.read_csv(file_or_path, header=None)
    numeric = df.apply(pd.to_numeric, errors="coerce").dropna(how="all").dropna(axis=1, how="all")
    if numeric.shape[0] < 4 or numeric.shape[1] < 5:
        raise ValueError("CSV does not look like the supported EIS matrix format.")
    freq = numeric.iloc[0].to_numpy(dtype=float)
    spectra = []
    for base in range(1, numeric.shape[0] - 2, 4):
        zmag = numeric.iloc[base].to_numpy(dtype=float)
        zre = numeric.iloc[base + 1].to_numpy(dtype=float)
        zim = -np.abs(numeric.iloc[base + 2].to_numpy(dtype=float))
        if np.nanmax(zmag) > 100000:
            continue
        n = min(len(freq), len(zre), len(zim))
        spectra.append(
            {
                "label": f"t{len(spectra):03d}",
                "frequency_hz": freq[:n],
                "z_real_ohm": zre[:n],
                "z_imag_ohm": zim[:n],
            }
        )
    if not spectra:
        raise ValueError("No usable spectra found. Blank spectra may have been skipped.")
    return {"frequency_hz": freq, "spectra": spectra}


def initial_guess(freq_hz: np.ndarray, z_real: np.ndarray, z_imag: np.ndarray) -> np.ndarray:
    high_freq = freq_hz > np.nanpercentile(freq_hz, 80)
    r_bulk = float(np.nanmedian(z_real[high_freq])) if np.any(high_freq) else float(np.nanmin(z_real))
    low_band = freq_hz < np.nanpercentile(freq_hz, 30)
    plateau = float(np.nanmedian(z_real[low_band])) if np.any(low_band) else float(np.nanmax(z_real))
    cler = max(plateau - r_bulk, 10.0)
    clec_uF = max(1 / (2 * np.pi * 500 * cler) * 1e6, 0.05)
    return np.array([max(r_bulk, 1.0), cler, min(clec_uF, 20.0), 0.8, -6.0], dtype=float)


def fit_spectrum(freq_hz: np.ndarray, z_real: np.ndarray, z_imag: np.ndarray, area_cm2: float = AREA_CM2_DEFAULT) -> dict[str, Any]:
    freq_hz = np.asarray(freq_hz, dtype=float)
    z_real = np.asarray(z_real, dtype=float)
    z_imag = np.asarray(z_imag, dtype=float)
    valid = np.isfinite(freq_hz) & np.isfinite(z_real) & np.isfinite(z_imag) & (freq_hz > 0)
    freq_hz, z_real, z_imag = freq_hz[valid], z_real[valid], z_imag[valid]
    if len(freq_hz) < 8:
        raise ValueError("Need at least 8 valid frequency points to fit.")

    z_exp = z_real + 1j * z_imag
    scale = np.maximum(np.abs(z_exp), 1e-9)
    bounds = ([0.1, 0.1, 0.001, 0.35, -11.0], [2000.0, 100000.0, 100.0, 1.0, -2.0])
    starts = [
        initial_guess(freq_hz, z_real, z_imag),
        initial_guess(freq_hz, z_real, z_imag) * np.array([1.1, 0.7, 1.4, 1.0, 1.0]),
        initial_guess(freq_hz, z_real, z_imag) * np.array([0.9, 1.4, 0.6, 1.0, 1.0]),
    ]
    starts[1][3] = 0.72
    starts[2][3] = 0.9

    def residual(params: np.ndarray) -> np.ndarray:
        z_mod = model_impedance(freq_hz, *params)
        diff = (z_mod - z_exp) / scale
        return np.concatenate([diff.real, diff.imag])

    best = None
    for start in starts:
        x0 = np.minimum(np.maximum(start, bounds[0]), bounds[1])
        result = least_squares(residual, x0=x0, bounds=bounds, max_nfev=3000)
        if best is None or result.cost < best.cost:
            best = result
    if best is None:
        raise RuntimeError("Fit failed.")
    r_bulk, cler, clec_uF, cpe_n, cpe_a_log10 = best.x
    z_model = model_impedance(freq_hz, *best.x)
    dof = max(1, 2 * len(freq_hz) - len(best.x))
    chi2_red = float(np.sum(residual(best.x) ** 2) / dof)
    return {
        "params": {
            "Rbulk_Ohm": float(r_bulk),
            "CLER_Ohm": float(cler),
            "CLEC_uF": float(clec_uF),
            "n_CPE": float(cpe_n),
            "A_CPE_log10": float(cpe_a_log10),
            "TEER_Ohm_cm2": float(cler * area_cm2),
            "Ccl_uF_cm2": float(clec_uF / area_cm2),
            "fchar_Hz": float(1 / (2 * np.pi * cler * clec_uF * 1e-6)),
            "chi2_red": chi2_red,
        },
        "fit_curve": pd.DataFrame(
            {
                "frequency_hz": freq_hz,
                "Zexp_real": z_real,
                "Zexp_imag": z_imag,
                "Zmodel_real": z_model.real,
                "Zmodel_imag": z_model.imag,
                "Zexp_abs": np.abs(z_exp),
                "Zmodel_abs": np.abs(z_model),
            }
        ),
    }


def summarize_existing_results(path: Path = DATA_ROOT / "eis_output" / "results_table.csv") -> dict[str, Any] | None:
    if not path.exists():
        return None
    df = pd.read_csv(path)
    summary_cols = [c for c in ["TEER_Ohm_cm2", "CLER_Ohm", "CLEC_uF", "Rbulk_Ohm", "n_CPE", "chi2_red"] if c in df.columns]
    if not summary_cols:
        return None
    return {
        "path": str(path),
        "rows": len(df),
        "columns": summary_cols,
        "summary": df[summary_cols].describe().round(4),
        "table": df,
    }
