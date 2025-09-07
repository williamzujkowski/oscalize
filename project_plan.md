---

# Project Plan — “oscalize” (LLM-free local converter)

## Mission (what we’re building)

A **single Dockerized CLI** that converts **`.docx` + `.md`** SSP content and **`.xlsx`** appendices (POA\&M, Integrated Inventory, CIS/CRM) into **OSCAL v1.1.3 JSON** artifacts (SSP, POA\&M; optional SAP/SAR, component-definition, profile), **validates** them with **NIST `oscal-cli`**, and emits a signed, reproducible bundle. No network calls; no LLMs in conversion/validation. Anchors: **OSCAL v1.1.3**; **OMB M-24-15** automation deadlines; **SP 800-53 Release 5.2.0**; **SP 800-171 r3**; **SP 800-18 r1 (track r2-IPD)**. ([NIST Pages][1], [The White House][2], [NIST Computer Security Resource Center][3])

## Scope (FedRAMP Low/Moderate ATO packages)

We cover the **full Initial Authorization Package**: SSP **plus required attachments**, **POA\&M**, **CIS/CRM**, and **Integrated Inventory Workbook**. Use the **Initial Authorization Package Checklist** to drive completeness; enforce POA\&M v3.0 semantics; use the FedRAMP **Integrated Inventory Workbook** as the authoritative inventory spreadsheet. ([FedRAMP][4], [FedRamp Help][5])

### What’s in / out

* **IN (v1):** `.docx` and `.md` for SSP body and narrative appendices; `.xlsx` for POA\&M, IIW (inventory), CIS/CRM.
* **OUT (v1):** PDFs and OCR; add later if needed.

## Architecture (deterministic, offline)

### A) Ingestion

* **DOCX/MD → canonical** via **Pandoc** (to Markdown + Pandoc JSON AST). Stable, scriptable, cross-platform. ([Pandoc][6])
* **XLSX (POA\&M, IIW, CIS/CRM)** via **pandas + openpyxl**; normalize to typed records. (FedRAMP’s POA\&M is explicitly an Excel template; IIW is an SSP Attachment.) ([FedRamp Help][5], [FedRAMP][7])

### B) Canonical Intermediate Representation (CIR)

A JSON schema you check into `/schemas/`:

* `doc.sections[]` — `{id, title, level, text, tables[]}`
* `poam.rows[]` — `{poam_id, title, description, severity, status, scheduled_date, completion_date, control_ids[], asset_ids[], origin, comments, source{file,sheet,row,col}}`
* `inventory.assets[]` — `{asset_id, type, name, env, service, links[], tags[], owner, criticality, ip, vlan, public, virtual, source{…}}`
* `cis.controls[]` — `{control_id, responsibility, impl_status, notes, source{…}}`
* `fips199`, `ptapia`, `sod_matrix[]`, and plan metadata (`irp/cmp/iscp/rob/policies`) with owners/dates/versions.
  **Every record carries source coordinates** for auditability (exact Excel cell/paragraph).

### C) Mapping (CIR → OSCAL v1.1.3)

* **SSP**: `metadata`, `system-characteristics` (map **FIPS-199 CIA** → `security-impact-level`), `system-implementation/components`, `control-implementation.implemented-requirements[]`. Use NIST’s v1.1.3 model references to stay honest. ([NIST Pages][1])
* **Inventory (IIW)**: **model** assets as inventory items/components in SSP; also attach the original workbook with hash in `back-matter`. ([FedRAMP][7])
* **POA\&M (v3.0)**: each row → `poam.poam-items[*]` (status/severity/dates via `props`, UUIDs, links to findings/risks). Enforce the guide’s required fields; attach the workbook (hashed). ([FedRamp Help][5])
* **CIS/CRM**: attach workbook; surface **per-control responsibility** and status as control-level `props` for filtering. (Attachment is still the source of truth.)
* **SAP/SAR (if provided)**: attach narrative/appendices under **Assessment Plan/Results**; map test scope and risk exposure table where feasible.
* **Evidence** for **SP 800-53 rel. 5.2.0** (software update/patch rigor): store SBOM/signature/attestation references in `assessment-results` or `back-matter`. ([NIST Computer Security Resource Center][3])

### D) Validation & Packaging

* Validate every artifact with **NIST `oscal-cli`** (schema validation; profile resolution; JSON↔XML sanity). Keep the tool pinned from its official repo/Maven. ([GitHub][8], [Maven Central][9])
* Emit `/dist/oscal/` with: `ssp.json`, `poam.json`, optional `assessment-plan.json`, `assessment-results.json`, validation logs, and a **manifest (hashes, timestamps)**.

## Inputs (contracts you enforce)

* **SSP DOCX/MD** must follow the FedRAMP SSP template sectioning (soft synonyms allowed, but required sections missing → fail). The template and checklist are your authoritative structure. ([FedRAMP][4])
* **POA\&M XLSX** must match v3.0 columns; any drift → clear error with sheet/column coordinates. ([FedRamp Help][5])
* **IIW XLSX** (Attachment 13) must match the published workbook structure; drift → fail with exact cell diagnostics. ([FedRAMP][7])
* **CIS/CRM XLSX**: treat as attach + structured summary (responsibility/status) into `props`.

## Multi-arch Docker (Intel/ARM)

* Use **Docker Buildx** to build and run for **`linux/amd64`** and **`linux/arm64`**. Official Docker docs show how to build multi-platform images and force platform at runtime on Apple Silicon. ([Docker Documentation][10])

### Dockerfile (pin real versions in your repo)

```dockerfile
FROM python:3.11-slim

# Pandoc + Java runtime (for oscal-cli)
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc default-jre ca-certificates curl unzip gpg && \
    rm -rf /var/lib/apt/lists/*

# Install NIST oscal-cli (from official sources)
# (Pin exact version in your repo; verify signature if you wish.)
RUN mkdir -p /opt/oscal-cli && cd /opt/oscal-cli && \
    curl -sSLO https://repo1.maven.org/maven2/gov/nist/secauto/oscal/tools/oscal-cli/cli-core/1.0.1/cli-core-1.0.1-oscal-cli.zip && \
    unzip cli-core-1.0.1-oscal-cli.zip
ENV PATH="/opt/oscal-cli/bin:${PATH}"

# Python deps (deterministic)
RUN pip install --no-cache-dir pandas openpyxl

# App
WORKDIR /app
COPY tools/oscalize /app/tools/oscalize
COPY mappings /app/mappings
COPY schemas /app/schemas
COPY Taskfile.yml Makefile /app/

ENTRYPOINT ["bash","-lc"]
```

### Build & Run (works on Intel and Apple Silicon)

* **Build multi-arch image:**
  `docker buildx build --platform linux/amd64,linux/arm64 -t oscalize:latest .` ([Docker Documentation][10])
* **Force Intel on Apple Silicon (emulation):**
  `docker run --rm -it --platform linux/amd64 -v "$PWD":/work -w /work oscalize:latest` ([Docker Documentation][10])

## Taskfile Targets (local parity)

* `task oscalize`: run readers → CIR → OSCAL outputs in `dist/oscal/`
* `task validate`: run **oscal-cli** on all outputs; fail on errors ([GitHub][8])
* `task bundle`: zip signed bundle + manifest
* `task diff`: deep diff of CIR/OSCAL vs last run
* `task clean`: purge `dist/`

## Runbook (operator)

1. Put inputs under `inputs/` (e.g., `ssp.docx`, `poam.xlsx`, `inventory.xlsx`, `cis_crm.xlsx`).
2. Build image (multi-arch) and run `task oscalize inputs/*`.
3. Run `task validate` to gate on schema/profile. (Uses **oscal-cli**.) ([GitHub][8])
4. Inspect `/dist/oscal/validation/*.log`.
5. **Optional**: open a **GUI LLM** and paste the “Validation Summary Prompt” from `CLAUDE.md` to get a Must-Fix checklist (no changes to artifacts).
6. Handoff the `/dist/oscal/` bundle + manifest.

## Tests & QA

* **Golden corpus**: anonymized `.docx/.md/.xlsx` + expected OSCAL JSON + validator logs.
* **Contract tests**: reject non-conforming POA\&M/IIW with pinpointed errors (sheet/column). ([FedRamp Help][5], [FedRAMP][7])
* **Round-trip smoke**: JSON↔XML via **oscal-cli** to catch format drift. ([GitHub][8])

## Compliance mapping (what you can honestly claim)

* **M-24-15**: You produce machine-readable OSCAL artifacts suitable for automated intake/ingest; timelines (18/24 months) drive urgency, not runtime requirements. ([The White House][2])
* **SP 800-53 rel. 5.2.0**: pipeline can capture software update/patch integrity evidence in `assessment-results`/`back-matter`. ([NIST Computer Security Resource Center][3])
* **SP 800-171 r3**: if CUI applies, the outputs can link findings/risks/ODPs coherently (via POA\&M and results). ([NIST Publications][11])
* **SP 800-18 r2-IPD**: track deltas; keep SSP structured per r1 for now. ([NIST Computer Security Resource Center][12])
