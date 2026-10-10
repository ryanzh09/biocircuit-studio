# BioCircuit Studio

**A researcher-guided workspace for organ-on-chip planning and electrical impedance spectroscopy (EIS) analysis.**

Submission category: **Tool & Platform** · AI4S Open Innovation: AI for Life Science, 2026

BioCircuit Studio links an editable experiment plan to an interactive EIS fitting workspace. Chip Design Workshop organizes the research question, biological model, experimental condition, control, baseline, proposed schedule, and measurement settings. Fit Lab carries that context into spectrum inspection, equivalent-circuit fitting, and CSV export.

This repository packages the existing V2 prototype. The application retains the existing functionality and fitting algorithm; display names have been updated for this release. The public package excludes laboratory datasets, private source PDFs, personal configuration, and earlier exports. Its built-in illustrative spectra are available for a complete local demonstration.

## Start here

**No API key, paid service, or experimental dataset is required for the local template workflow and Fit Lab.** The optional AI generation and chat features require the user's own OpenAI API access and may incur charges. Local mode uses deterministic templates; it does not reproduce language-model generation.

### Install and run

Use Python **3.13**. The packaging checks used Python **3.13.5** and the dependency versions in `requirements.txt`. A new installation on another machine has not yet been verified.

From the repository root on macOS or Linux:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run software/microfluidic-eis-agent/streamlit_app.py
```

On Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run software/microfluidic-eis-agent/streamlit_app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`. Installation requires internet access; the template workflow and Fit Lab can then operate locally. Chart.js is bundled. Stop the server with Ctrl+C.

### Reproduce the existing demonstration

1. Open **Chip Design Workshop** and choose **Endothelial drug-response barrier assay**.
2. Leave the API key empty. Review the preset research question and vehicle control. Enter a proposed baseline and schedule, for example "before the selected condition" and "baseline, 24 h, 48 h". These entries describe a demonstration plan.
3. Enter an active sensing area if known; the existing demo default is 0.1962 cm². Enter planned settings, an export plan, and the metadata you would record.
4. Select **Generate Workflow Draft**. Inspect Assay Summary, Build View, Operate View, Analyze View, and Export. Download the workflow JSON.
5. Select **Open Workflow in Fit Lab**. Confirm that the planning fields have carried over. Keep **Demo data** selected; the 12 built-in spectrum labels are illustrative.
6. Run **Auto-fit** on the selected demo spectrum. Inspect Bode magnitude, Bode phase, and Nyquist plots and the residual summaries. Optionally run the bootstrap; its random resampling is unseeded.
7. Download the fitting CSV before navigating away. The embedded Fit Lab session resets when leaving the page or loading another dataset.

You can also open `software/microfluidic-eis-agent/fitlab_assets/eis_simulator_v2.html` directly in a browser for the standalone Fit Lab. Keep `chart.umd.js` beside it. This route demonstrates analysis without the Python app or workshop handoff.

## What is implemented

| Component | Existing behavior |
| --- | --- |
| Workshop | Editable experimental context; two chip templates; three assay presets plus Custom; checklist of entered information |
| Local planning | Keyword-based template selection and structured workflow draft generation |
| Optional AI | Template-conditioned draft generation and section-specific chat through the OpenAI API |
| Handoff | Workflow JSON export/import and direct transfer of planning context to Fit Lab |
| Fit Lab | Built-in demo spectra, matrix CSV upload, parameter sliders, multi-start fitting, three plot modes, residual summaries, residual bootstrap |
| Traceability | Per-spectrum metadata and user-selected provenance; fitting results and metadata exported together |

The analysis plan mentions possible downstream outputs such as a parameter time course, a design report, and baseline comparisons. Those are suggested workflow deliverables; this version exports workflow JSON and fitting CSV. Automatic fit-quality classification is marked as proposed in the interface. Researcher review is guidance without a sign-off mechanism.

## Input and output

**Workshop input:** research question, biological model, condition, separate control, baseline, proposed schedule, settings, and available components. Its JSON output preserves the plan and a Fit Lab context object.

**Fit Lab CSV input:** a numeric frequency row followed by one or more complete four-row spectrum blocks: magnitude, real impedance, imaginary impedance, and phase. Each row must have the same length; frequencies must be positive and strictly increasing or decreasing. The parser uses real and imaginary rows and converts imaginary values to `-abs(value)`. Positive inductive behavior cannot be represented faithfully by this parser. Spectrum group labels from uploads are row identifiers; actual time points are entered separately.

**Fit Lab output:** resistance, capacitance, CPE parameters, area-normalized derived values, characteristic frequency, optional bootstrap summaries, source filename, spectrum index, and entered sample context. Unknown metadata remains empty. The app retains uploaded spectra for user selection, including possible cell-free references.

## Data, sources, and scientific scope

The built-in data contains **12 spectra × 65 frequencies**, from **5 Hz to 100 kHz**. Its displayed labels run from 0 to 33 h in 3 h steps. These labels and values are illustrative; experimental provenance, a generating process, and ground-truth parameters are undocumented. The project owner authorized redistribution of the built-in spectra for this submission on October 9, 2026. No real experimental validation is claimed.

Two local PDF reference records remain in the source. Their PDFs are excluded, so exported source records report `available: false` and `status: missing_file`. The local workflow still runs using the existing hand-authored templates. The optional AI receives selected source titles, roles, and scope descriptions; it does not read the complete PDFs or perform document retrieval. A source title in the interface is a retained reference record, not evidence that the PDF was retrieved.

Read [Data and source notes](docs/DATA_AND_SOURCES.md), [Technical report](docs/TECHNICAL_REPORT.md), and [Verification](verification/VALIDATION.md). Biological interpretation requires appropriate experimental evidence. No claim is made about drug efficacy, validated TEER measurement, improved researcher productivity, or superiority to another AI system.

## Optional AI configuration

Enter your own API key in the application's API-key field and select or enter a model available to your account. The existing default model string is `gpt-5.5`; it is an application setting, and current account availability has not been checked. No model weights are bundled and no training is performed.

The app sends entered experimental context, template content, source descriptions, and relevant chat context to the configured API. Use information you are authorized to send. Credentials are held in the Streamlit session and are excluded from this package. Live API calls were not made during packaging; the request/response path was exercised with the existing stub test.

## Verification

After installing the Python dependencies:

```bash
python verification/test_workshop.py
python verification/check_integrity.py
```

For optional browser regression checks, install Node.js and the development dependency:

```bash
npm install
npx playwright install chromium
python -m streamlit run software/microfluidic-eis-agent/streamlit_app.py --server.port 8517 --server.headless true
```

In a second terminal at the repository root:

```bash
npm run test:browser
```

The browser checks create screenshots and test exports in `verification/output/`, which is ignored by Git. They reuse the built-in demo data. `APP_URL` can override the test server address. `CHROME_PATH` can select an installed Chrome executable. Test results establish software behavior in the stated environment; they do not establish biological validity or statistical interval coverage.

## Repository layout

```text
software/microfluidic-eis-agent/    Application and bundled chart library
docs/                             Technical report, data notes, package change record
verification/                     Reusable checks and compact packaging evidence
requirements.txt                  Pinned direct Python dependencies
package.json                      Optional browser-test dependency
THIRD_PARTY_NOTICES.md             Dependency and chart-license notes
```

## License and attribution

No additional license for the original project code is granted in this repository. The bundled Chart.js license is retained in `software/microfluidic-eis-agent/fitlab_assets/Chart.js-LICENSE.md`. Installed dependencies retain their respective licenses; see `THIRD_PARTY_NOTICES.md`. Public availability alone does not grant a blanket license over third-party material.

## Packaging changelog

**2026-10-09:** Prepared a separate AI4S repository from V2. Preserved application code, bundled demo values, and fitting behavior; excluded private files and machine-specific launchers; added portable setup instructions, submission documentation, and adapted existing verification checks to use the public package. See [Package changes](docs/PACKAGING_CHANGES.md).

**2026-10-10:** Renamed the public release BioCircuit Studio, updated four display strings and documentation, and recorded the exact display-only changes in the integrity manifest.
