# Data and source notes

## Built-in illustrative spectra

The public demonstration uses the `DEMO_FREQ`, `DEMO_RE`, and `DEMO_IM` arrays already present in V2's `fitlab_assets/eis_simulator_v2.html`.

- Size: 12 spectra, each containing 65 real/imaginary impedance pairs.
- Frequency range: 5 Hz to 100 kHz.
- Displayed labels: 0-33 h in 3 h increments, assigned by `loadDemoData()`.
- Provenance: illustrative demo values; experimental origin and a synthetic generating process are undocumented.
- Redistribution: the project owner explicitly authorized inclusion of these built-in spectra in the public submission on October 9, 2026.
- Ground truth: no verified electrical parameter values, biological labels, treatment effects, or sample identities accompany these arrays.
- Interpretation: suitable for demonstrating software operation. No measured biological time course or parameter-recovery accuracy is inferred from them.

Browser verification temporarily writes these same demo values to the accepted CSV format and uploads them again. That round trip tests import and metadata handling. The test leaves uploaded data marked as provenance-unverified.

## Excluded material

Laboratory CSV and spreadsheet files, previous result tables, notebooks, source PDFs, annotated presentations, user-saved choices, logs, secrets, virtual environments, and unrelated portfolio assets are excluded. No external dataset is required to run the public demo. No training dataset or model checkpoint is distributed.

## Retained reference records

The application contains two manually authored reference records with the local titles `2023 Mai XC - Endo` and `2023 June LF MDCK MF`. These are local document labels; verified bibliographic identifiers and redistribution permissions for the PDFs were not established for this package. The PDFs are omitted. The associated template definitions and short source descriptions remain within the application code.

`foundational_knowledge_base()` checks file existence and reports both records as missing. The display's source count includes these records even when the files are absent. The optional API payload includes the selected reference's title, role, and knowledge-scope summary. It contains no full PDF content, page-level retrieval, or independently verified evidence chain.

## User-supplied data

Fit Lab accepts a frequency row followed by complete four-row blocks: magnitude, real impedance, imaginary impedance, and phase. Uploaded arrays stay in the browser's embedded Fit Lab state; the fitting routine runs in JavaScript. Metadata is supplied by the user per spectrum. Selecting "Measured data" records the user's assertion of provenance; the application does not authenticate laboratory records.

The workshop runs in Streamlit and can send the entered planning context to an external API when the user enables AI generation or chat. Users should only supply material they are authorized to process and share.
