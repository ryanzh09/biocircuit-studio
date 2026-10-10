# AI4S packaging record

Prepared October 9, 2026, from the existing local V2 project.

## Preserved

The three application Python files, Fit Lab HTML, bundled Chart.js, chart license, and existing dependency files were initially copied unchanged. `verification/source-integrity.json` records their SHA-256 digests. `verification/check_integrity.py` checks the release files against those digests, allowing only the four documented display-name replacements.

The folder topology `software/microfluidic-eis-agent/` is preserved so that existing relative resource paths work. Source-file existence checks report the excluded PDFs as missing. Logs created at runtime remain local and are ignored by Git.

## Added for submission

- Repository setup and demonstration instructions.
- Technical report, data/source notes, and third-party notices.
- Root dependency file, optional browser-test configuration, and a Git ignore file.
- Streamlit configuration disabling anonymous usage statistics for this package.
- Portable integrity check and compact verification record.

## Adapted verification

The four existing Python workflow tests were retained. Their source-availability assertion now expects the private PDFs to be absent, and their file-writing fixture was removed.

The existing browser checks now accept a configurable local server and browser executable. They reuse two built-in demo spectra for CSV import instead of loading a laboratory CSV. Uploaded demo data remains provenance-unverified. The original data-specific out-of-range check was omitted because its private fixture is excluded. Generated screenshots and exports are written to an ignored output directory.

No new scientific experiment, benchmark, model, feature, fitting method, biological claim, or API evaluation was added. The original V2 project remains separate.

## October 10, 2026

Renamed the public release BioCircuit Studio. Updated documentation, PDF metadata, package name, and four Streamlit display strings. Removed internal submission-preparation prose. Original algorithms, templates, demo spectra, dependencies, and input/output behavior are preserved.
