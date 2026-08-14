# Document Import Runtime Third-Party Notices

This file covers the libraries used to read and normalize uploaded screenplay
documents. It is not a substitute for the license files shipped by the Python
packages in the runtime image.

| Component | Fixed version/reference | License | Upstream source | Local use |
| --- | --- | --- | --- | --- |
| python-docx | `1.2.0` | MIT | <https://github.com/python-openxml/python-docx> | Read body paragraphs and tables after the project's OOXML safety checks. |
| markdown-it-py | `4.2.0` | MIT | <https://github.com/executablebooks/markdown-it-py> | Produce bounded report previews without enabling raw uploaded markup. |
| pypdf | `6.16.0`, commit `2b60c99973df8d7f959cd46658604d881be3de3a` | BSD-3-Clause | <https://github.com/py-pdf/pypdf> | Parse unencrypted, passive PDFs and extract existing text; OCR is not included. |

No source files, examples, or scripts from these projects are vendored into
this repository. Dependency updates require lock regeneration, fixture tests,
license review, and a real document-import canary.
