# oscalize

> LLM-free local OSCAL converter for FedRAMP compliance documents

**oscalize** is a Docker-containerized CLI tool that converts `.docx/.md` SSP content and `.xlsx` appendices (POA&M, Integrated Inventory, CIS/CRM) into **OSCAL v1.1.3 JSON** artifacts. It provides deterministic, offline conversion with no LLMs, multi-arch Docker support, and validation using NIST oscal-cli.

## Features

- **🚫 LLM-Free**: Deterministic, offline conversion using Pandoc and structured data processing
- **🐳 Multi-Arch Docker**: Supports `linux/amd64` and `linux/arm64` (Intel & Apple Silicon)
- **✅ NIST Validation**: Validates outputs with official NIST `oscal-cli` 
- **📊 FedRAMP Ready**: Supports FedRAMP v3.0 POA&M and Integrated Inventory Workbook
- **🔍 Source Attribution**: Every output includes source coordinates for auditability
- **📦 Signed Bundles**: Creates reproducible bundles with integrity manifests

## Quick Start

```bash
# Build multi-arch image
docker buildx build --platform linux/amd64,linux/arm64 -t oscalize:latest .

# Convert documents (Intel/ARM compatible)
docker run --rm -it -v "$PWD:/work" -w /work oscalize:latest 'task oscalize inputs/*'

# Validate OSCAL outputs  
docker run --rm -it -v "$PWD:/work" -w /work oscalize:latest 'task validate'

# Create deployment bundle
docker run --rm -it -v "$PWD:/work" -w /work oscalize:latest 'task bundle'
```

## Architecture

```
Inputs (DOCX/MD/XLSX) → Readers → CIR → Mappers → OSCAL JSON → Validation → Bundle
```

### Canonical Intermediate Representation (CIR)

oscalize uses CIR as a bridge between input formats and OSCAL:

- **Document CIR**: Sections, tables, and metadata from DOCX/MD files
- **POA&M CIR**: Structured POA&M data with FedRAMP v3.0 compliance
- **Inventory CIR**: Asset data from FedRAMP Integrated Inventory Workbook
- **Source Attribution**: Every field includes exact source coordinates

### Supported Inputs

| Input Type | Formats | Purpose |
|------------|---------|---------|
| **SSP Documents** | `.docx`, `.md` | System Security Plan content |
| **POA&M** | `.xlsx` | FedRAMP POA&M v3.0 template |
| **Inventory** | `.xlsx` | FedRAMP Integrated Inventory Workbook |
| **CIS/CRM** | `.xlsx` | Customer Responsibility Matrix |

### Generated Outputs

| OSCAL Artifact | Description |
|----------------|-------------|
| **`ssp.json`** | System Security Plan with control implementations |
| **`poam.json`** | Plan of Action and Milestones |
| **`component-definition.json`** | Component definitions from inventory |
| **Validation Logs** | NIST oscal-cli validation results |
| **Manifest** | File integrity with SHA-256 hashes |

## Installation

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone <repository-url>
cd oscalize

# Build image
docker buildx build --platform linux/amd64,linux/arm64 -t oscalize:latest .

# Force Intel on Apple Silicon if needed
docker run --platform linux/amd64 --rm -it -v "$PWD:/work" -w /work oscalize:latest
```

### Option 2: Local Development

```bash
# Install dependencies
python -m pip install -r requirements.txt

# Install NIST oscal-cli
task install-oscal-cli

# Install Task runner
curl -sL https://taskfile.dev/install.sh | sh

# Run locally
task oscalize inputs/*
```

## Usage

### Basic Workflow

1. **Prepare inputs** in `inputs/` directory:
   ```
   inputs/
   ├── ssp.docx           # System Security Plan
   ├── poam.xlsx          # FedRAMP POA&M v3.0
   ├── inventory.xlsx     # FedRAMP Integrated Inventory
   └── cis_crm.xlsx       # Customer Responsibility Matrix
   ```

2. **Convert to OSCAL**:
   ```bash
   task oscalize
   # Outputs to dist/oscal/
   ```

3. **Validate artifacts**:
   ```bash
   task validate
   # Creates dist/oscal/validation/*.log
   ```

4. **Create bundle**:
   ```bash
   task bundle
   # Creates dist/oscalize-bundle.tar.gz
   ```

### Advanced Usage

```bash
# Custom input/output directories
python tools/oscalize/cli.py convert /path/to/inputs --output /path/to/outputs

# Validation summary
python tools/oscalize/cli.py validation-summary dist/oscal/validation

# Compliance check
python tools/oscalize/cli.py compliance-check dist/oscal

# Test against corpus
python tools/oscalize/cli.py test-corpus tests/corpus

# Bundle operations
python tools/oscalize/cli.py bundle dist/oscal --output release.tar.gz
python tools/oscalize/cli.py manifest dist/oscal
```

## Configuration

### Mapping Configuration

Customize conversion behavior via JSON configuration files in `mappings/`:

- **`ssp_sections.json`**: Document section to OSCAL mapping
- **`control_mappings.json`**: Control implementation patterns  
- **`poam_mappings.json`**: POA&M column mappings and validation
- **`inventory_mappings.json`**: Inventory workbook structure

### Example: Custom Section Mapping

```json
{
  "section_mappings": {
    "system_identification": {
      "keywords": ["system name", "system identification"],
      "oscal_target": "system-characteristics.system-name",
      "required": true
    }
  }
}
```

## Compliance

### Standards Supported

- **NIST OSCAL v1.1.3**: All artifacts conform to NIST specifications
- **OMB M-24-15**: Supports automation requirements and deadlines
- **FedRAMP**: Initial Authorization Package artifacts
- **NIST SP 800-53 Rev 5**: Control implementation mapping
- **NIST SP 800-171 r3**: CUI control requirements

### FedRAMP Compliance

oscalize specifically supports FedRAMP Initial Authorization Package requirements:

- ✅ System Security Plan (OSCAL SSP)
- ✅ Plan of Action and Milestones v3.0 (OSCAL POA&M)
- ✅ Integrated Inventory Workbook (OSCAL components)
- ✅ Customer Responsibility Matrix (attached with mappings)
- ✅ FIPS-199 categorization (mapped to security-impact-level)

## Quality Assurance

### Validation Pipeline

1. **CIR Schema Validation**: JSON Schema validation of intermediate data
2. **OSCAL Format Validation**: NIST oscal-cli schema validation
3. **Content Validation**: Control ID validation, data consistency
4. **Compliance Checking**: M-24-15, FedRAMP, SP 800-53 requirements
5. **Integrity Verification**: SHA-256 manifests and signed bundles

### Testing

```bash
# Run full test suite
task test

# Test against known corpus
task test-corpus

# Code quality checks
task lint

# Format code
task format
```

## GUI LLM Integration (Optional)

While oscalize itself is LLM-free, it supports optional GUI LLM integration for validation summaries. See [`CLAUDE.md`](CLAUDE.md) for the complete GUI LLM operator playbook.

### Validation Summary with GUI LLM

```bash
# Generate validation logs
task validate

# Copy this prompt to your GUI LLM:
```

> Read this validation output and produce:
> 1) Must-Fix (schema/profile errors that block submission)
> 2) Nice-to-Have (format/style warnings)  
> 3) Missing appendices vs FedRAMP Initial Authorization Package Checklist
> 4) Gaps vs M-24-15 (machine-readable artifacts)
> 5) Evidence notes for SP 800-53 Release 5.2.0

## Development

### Project Structure

```
.
├── CLAUDE.md                 # GUI LLM operator playbook
├── Dockerfile                # Multi-arch container
├── Taskfile.yml             # Automation tasks
├── tools/oscalize/          # Main application
│   ├── readers/             # Input format readers
│   ├── cir/                 # CIR processing
│   ├── mappers/             # CIR to OSCAL conversion
│   ├── validation/          # OSCAL validation
│   └── packaging/           # Bundle creation
├── mappings/                # Configuration files
├── schemas/                 # CIR JSON schemas
├── tests/corpus/            # Test cases
└── dist/oscal/              # Generated outputs
```

### Contributing

1. **Follow existing patterns** in readers/mappers/validators
2. **Add tests** for new functionality in `tests/`
3. **Update schemas** in `schemas/` if CIR structure changes
4. **Test multi-arch** on both Intel and ARM platforms
5. **Validate compliance** with `task compliance-check`

### Architecture Decisions

- **No LLMs**: Ensures deterministic, auditable results
- **CIR Bridge**: Enables testing and validation at each stage  
- **Docker-First**: Consistent execution across platforms
- **Source Attribution**: Full traceability to source documents
- **NIST Tooling**: Uses official NIST oscal-cli for validation

## Troubleshooting

### Common Issues

**Docker Build Fails on Apple Silicon**
```bash
# Force Intel emulation
docker buildx build --platform linux/amd64 -t oscalize:dev .
```

**OSCAL Validation Errors**
```bash
# Check validation logs
cat dist/oscal/validation/*.log

# Use GUI LLM for summary (see CLAUDE.md)
task validation-summary
```

**Missing Dependencies**
```bash
# Check installation
task check-deps

# Install missing tools
task install-oscal-cli
```

**POA&M Template Issues**
```bash
# Verify FedRAMP POA&M v3.0 format
# Check column mappings in mappings/poam_mappings.json
python tools/oscalize/cli.py doctor --check-deps
```

### Getting Help

1. **Check validation logs** in `dist/oscal/validation/`
2. **Review manifest** for file integrity issues
3. **Run compliance check** for standards gaps
4. **Use corpus tests** to verify against known good inputs

## License

Apache License 2.0 - see LICENSE file for details.

## References

- [NIST OSCAL](https://pages.nist.gov/OSCAL/) - Open Security Controls Assessment Language
- [OMB M-24-15](https://www.whitehouse.gov/wp-content/uploads/2024/07/M-24-15-Modernizing-the-Federal-Risk-and-Authorization-Management-Program.pdf) - Federal automation requirements  
- [FedRAMP](https://www.fedramp.gov/) - Federal Risk and Authorization Management Program
- [NIST SP 800-53](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final) - Security and Privacy Controls
- [NIST oscal-cli](https://github.com/usnistgov/oscal-cli) - Official OSCAL command-line tool

---

**oscalize** - Making compliance documentation machine-readable, one conversion at a time. 🤖