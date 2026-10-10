# Third-party software notices

The application distributes Chart.js as a bundled JavaScript asset. Its MIT license and copyright notice are preserved in `software/microfluidic-eis-agent/fitlab_assets/Chart.js-LICENSE.md`. The bundled file identifies itself as Chart.js 4.4.1.

The Python packages below are installed through `requirements.txt`; their source distributions and wheels include their complete licenses and third-party notices. Names and versions match the local packaging environment.

| Component | Version | Role | Main license / source |
| --- | --- | --- | --- |
| NumPy | 2.4.6 | Numerical arrays | BSD-3-Clause with bundled third-party terms; https://numpy.org/ |
| pandas | 3.0.3 | Tables and CSV handling | BSD-3-Clause; https://pandas.pydata.org/ |
| SciPy | 1.17.1 | Auxiliary Python fitting routine | BSD-3-Clause with bundled third-party terms; https://scipy.org/ |
| Streamlit | 1.58.0 | Python interface | Apache-2.0; https://streamlit.io/ |
| OpenAI Python SDK | 2.44.0 | Optional external AI requests | Apache-2.0; https://github.com/openai/openai-python |
| Chart.js | 4.4.1 | Fit Lab plots | MIT; https://www.chartjs.org/ |

The full installed dependency snapshot is retained as `software/microfluidic-eis-agent/requirements-tested.txt`. It records the source project's environment; installation from that full snapshot has not been independently tested on a fresh machine.

Playwright is an optional development dependency for browser checks (Apache-2.0, https://playwright.dev/). Its browser downloads carry their own notices. No browser binaries are included.

OpenAI-hosted model access is optional and governed by the provider's service terms. Model weights are not redistributed. The existing application default is the string `gpt-5.5`; live model availability and output quality were not verified in this submission preparation.

