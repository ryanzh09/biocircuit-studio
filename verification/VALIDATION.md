# Public package verification

Date: **October 9, 2026**. Scope: software behavior of the separate AI4S package using the existing V2 app and built-in illustrative data.

## Completed checks

- **4 Python workflow tests passed:** metadata and JSON round trip, missing source handling, unknown actual sample fields, invalid/legacy imports, an API request/response stub, and the Workshop's preset, edit, navigation, handoff, and reset behavior.
- **18 browser checks passed:** local generation; all output views; JSON download; Fit Lab handoff; fit/plot/export parameter agreement; active-area updates; 20-resample bootstrap completion; stale-fit invalidation; demo CSV reimport; per-spectrum metadata; fitting CSV download; malformed CSV rejection; three plot modes; JSON reload; return-to-edit; reset; absence of uncaught JavaScript errors; standalone chart operation with networking disabled.
- **7 application/dependency files match their V2 source SHA-256 digests; 1 contains four display-name replacements.** The integrity check verifies both the published Streamlit file and its exact V2 content after reversing those replacements. Functionality and demo values are preserved.

Evidence: `packaging-results.json`, `browser-test-results.json`, and `source-integrity.json`. Reusable commands are in the root README. Generated screenshots and exports are local verification artifacts in `verification/output/` and are excluded from the distribution.

## Environment

Python 3.13.5; NumPy 2.4.6; pandas 3.0.3; SciPy 1.17.1; Streamlit 1.58.0; OpenAI SDK 2.44.0; Playwright 1.62.1; local headless Chrome on macOS. The application was launched on a separate local port. It used the existing Python environment and the packaged source. A fresh dependency installation on another machine was not performed.

## Data and interpretation

The tests use the built-in demo arrays and reimport two of those spectra through the CSV interface. They do not load the private laboratory files or PDFs. Sample IDs, conditions, and schedules entered during verification are test fixtures. Uploaded data remains labelled as provenance-unverified. No numerical accuracy benchmark or biological result is reported.

Bootstrap completion and consistency between the fit, chart, and export establish software behavior. They do not establish parameter identifiability, interval coverage, correctness for a biological device, or reliable drug-response interpretation. The unseeded bootstrap can produce different values between runs.

The API request path was checked with the existing stub response. Live API generation, model access, grounding quality, hallucination rate, and AI benefit over template mode were not evaluated.

## Adaptation from earlier tests

The source-availability assertion now expects the deliberately omitted PDFs. Browser tests use demo-data CSV reimport instead of a private laboratory CSV, and their output directory is ignored by Git. The earlier private-data-dependent fitting-failure check is omitted. These adjustments change test fixtures and packaging paths; application behavior is unchanged.

## October 10 release update

Updated the project name to BioCircuit Studio. The four Streamlit display-name replacements do not change application logic. The 18 browser checks above were run before this display-only update.
