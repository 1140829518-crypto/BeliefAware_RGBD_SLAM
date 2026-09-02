# PAA publication-layout preflight

Audit date: 2026-08-29 (Asia/Shanghai)

## Scope and provenance

- Source manuscript: `/home/djn/123/ORB_SLAM2_AddSemantic/paer2/PAA-final.docx`
- Source SHA-256: `ef0acfdb2f91a14035f8e2cd009a2997ac7764cb75cb7e5d0550b01a8e89178c`
- Output manuscript: `/home/djn/123/ORB_SLAM2_AddSemantic/paer2/PAA-final-submission-layout.docx`
- Output SHA-256: `7be8481ccfe968d6880fd846b001c9415dfd3c2994655f93d9b41a5ab0d99c00`
- Requested PDF: `/home/djn/123/ORB_SLAM2_AddSemantic/paer2/PAA-final-submission-layout.pdf`
- PDF SHA-256: **N/A — PDF was not generated**
- Layout script: `/home/djn/123/ORB_SLAM2_AddSemantic/results/paa_final_layout_20260829/apply_publication_layout.py`

The source manuscript was retained unchanged. No experiments were run, and no experiment data, figures, Table 2–12 values, reference metadata, or scientific conclusions were changed.

## Automated structural checks

| Check | Status | Evidence |
|---|---|---|
| References format | PASS | References [1]–[24] share one left-aligned, 8.5-pt Times New Roman paragraph format with identical hanging indent, spacing before/after, and line spacing. Reference text was not rewritten. |
| Table 1 | PASS (structural) | Caption/introduction and six-column content match the requested text; full-width continuous section is present; horizontal rules only; 8.5-pt left-aligned cells; header, “Ours (Temporal),” and “Yes” are bold. Rendered-page fit remains unverified. |
| Fig. 5 placement | PASS (structural) | Image paragraph and caption use keep-with-next; Fig. 5 remains the final decay-sensitivity figure. Rendered pagination remains unverified. |
| Table 11 placement | PASS (structural) | Caption uses keep-with-next and all rows use do-not-split; Table 11 remains the decay-sensitivity-v2 table. Rendered pagination remains unverified. |
| Fig. 1–5 presence/order | PASS | Exactly five ordered captions and five embedded image relationships are present. |
| Table 1–12 presence/order | PASS | Exactly 12 table objects and one ordered caption for each Table 1–12 are present. Narrative mentions such as “Table 4 summarizes” were excluded from caption counting. |
| Eq. (1)–(13) presence/order | PASS | All 13 equation-number paragraphs remain ordered and all embedded equation objects are preserved. |
| 4.7 content | PASS | Exact heading “4.7 Re-observation Evaluation Protocol” occurs once and its body text is retained. Sections 4.8 and 4.9 are retained. |
| Declarations | PASS | Funding, competing interests, data availability, code availability, and ethics approval remain present. |
| Code availability exact wording | PASS | Exact sentence occurs once: “The source code developed for this study is not publicly available.” |
| Prohibited wording | PASS | “upon reasonable request” does not occur. |
| References [1]–[24] | PASS | Exactly 24 sequentially numbered reference paragraphs remain present. |
| Object conservation | PASS | Before/after: 12 tables, 5 image relationships, 50 embedded Word objects, no tracked insertions/deletions. |

## Equation audit

All equations retain their original Word/OLE objects. Their shared display paragraphs use a centered tab stop for the formula and a right tab stop for the number. No equation text or object was rebuilt.

| Equation | Page | Alignment | Number position | Overflow | Object preserved | Status |
|---|---:|---|---|---|---|---|
| Eq. (1) | UNVERIFIED | structurally normalized | structurally right-tabbed | UNVERIFIED | yes | FAIL — rendered inspection unavailable |
| Eq. (2) | UNVERIFIED | structurally normalized | structurally right-tabbed | UNVERIFIED | yes (two source OLE objects retained) | FAIL — rendered inspection unavailable |
| Eq. (3) | UNVERIFIED | structurally normalized | structurally right-tabbed | UNVERIFIED | yes | FAIL — rendered inspection unavailable |
| Eq. (4) | UNVERIFIED | structurally normalized | structurally right-tabbed | UNVERIFIED | yes | FAIL — rendered inspection unavailable |
| Eq. (5) | UNVERIFIED | structurally normalized | structurally right-tabbed | UNVERIFIED | yes | FAIL — rendered inspection unavailable |
| Eq. (6) | UNVERIFIED | structurally normalized | structurally right-tabbed | UNVERIFIED | yes | FAIL — rendered inspection unavailable |
| Eq. (7) | UNVERIFIED | structurally normalized | structurally right-tabbed | UNVERIFIED | yes | FAIL — rendered inspection unavailable |
| Eq. (8) | UNVERIFIED | structurally normalized | structurally right-tabbed | UNVERIFIED | yes | FAIL — rendered inspection unavailable |
| Eq. (9) | UNVERIFIED | structurally normalized | structurally right-tabbed | UNVERIFIED | yes | FAIL — rendered inspection unavailable |
| Eq. (10) | UNVERIFIED | structurally normalized | structurally right-tabbed | UNVERIFIED | yes | FAIL — rendered inspection unavailable |
| Eq. (11) | UNVERIFIED | structurally normalized | structurally right-tabbed | UNVERIFIED | yes | FAIL — rendered inspection unavailable |
| Eq. (12) | UNVERIFIED | structurally normalized | structurally right-tabbed | UNVERIFIED | yes | FAIL — rendered inspection unavailable |
| Eq. (13) | UNVERIFIED | structurally normalized | structurally right-tabbed | UNVERIFIED | yes | FAIL — rendered inspection unavailable |

The FAIL status above is deliberately conservative: the DOCX structure passes, but page number, visual centering, line wrapping, and overflow cannot be certified without a rendered PDF.

## PDF/visual preflight blocker

LibreOffice 6.4.7.2 was invoked twice with isolated user profiles. It produced no PDF. The environment has neither `default-jre` nor `libreoffice-java-common`, and the converter did not complete reliably. Therefore the requested first-page-to-References visual inspection could not be performed. The following remain unverified:

- exact page numbers for Eq. (1)–(13);
- Table 1 rendered width and word wrapping;
- Fig. 5/Table 11 page/column adjacency and whitespace;
- equation overflow, glyph appearance, superscripts/subscripts, and number wrapping;
- full-document column transitions, captions, page boundaries, and final font rendering.

## Final decision

**NOT READY FOR SUBMISSION**

Remaining blocker: generate the requested PDF in a working Microsoft Word or LibreOffice environment and visually inspect every page. The DOCX passes the available structural and object-conservation checks, but submission readiness cannot be certified without that render-level preflight.
