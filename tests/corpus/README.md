# Oscalize Golden Corpus Testing Framework

This directory contains the golden corpus test cases for validating oscalize conversion accuracy and OSCAL compliance.

## Overview

The golden corpus testing framework provides automated validation of the oscalize conversion pipeline by:

1. **Real Conversion Testing** - Running actual conversion on input files
2. **Output Comparison** - Comparing generated OSCAL with expected golden outputs  
3. **Validation Testing** - Verifying OSCAL compliance using NIST oscal-cli
4. **Regression Detection** - Catching changes that break existing functionality

## Directory Structure

```
tests/corpus/
├── README.md                    # This file
├── sample_basic_ssp/            # Example test case
│   ├── inputs/                  # Input files for conversion
│   │   └── basic_ssp.md
│   ├── expected_outputs/        # Expected OSCAL outputs (golden files)
│   │   └── ssp.json
│   └── test_config.json         # Test configuration and metadata
└── corpus_manifest.json         # Auto-generated manifest of all test cases
```

## Test Case Structure

Each test case directory contains:

- **`inputs/`** - Input files (`.md`, `.docx`, `.xlsx`) for conversion
- **`expected_outputs/`** - Expected OSCAL JSON outputs after conversion
- **`test_config.json`** - Test configuration including:
  - Test name and description
  - Input/output file mappings
  - Expected validation status
  - Metadata and test categorization

### Test Configuration Example

```json
{
  "name": "sample_basic_ssp",
  "description": "Basic SSP document test case",
  "input_files": ["inputs/basic_ssp.md"],
  "expected_outputs": ["expected_outputs/ssp.json"],
  "expected_validation_status": "COMPLIANT",
  "test_type": "golden_corpus"
}
```

## CLI Commands

### Enhanced Corpus Testing
```bash
# Run comprehensive corpus tests with validation
python tools/oscalize/cli.py test-corpus-enhanced tests/corpus/ --include-validation

# Run without validation (faster)
python tools/oscalize/cli.py test-corpus-enhanced tests/corpus/
```

### Generate Golden Test Cases
```bash
# Create golden test case from current inputs/
python tools/oscalize/cli.py create-golden-test tests/corpus/ --test-name my_test

# Generate corpus from sample files
python tools/oscalize/cli.py generate-corpus tests/corpus/ samples/
```

### Corpus Management
```bash
# Validate corpus integrity
python tools/oscalize/cli.py validate-corpus-integrity tests/corpus/
```

## Task Runner Commands

```bash
# Generate golden test from current inputs
task generate-corpus

# Run enhanced corpus testing
task test-corpus-enhanced

# Validate corpus integrity  
task validate-corpus

# Full corpus workflow
task corpus-full
```

## Creating New Test Cases

### Method 1: From Current Inputs
1. Place your input files in `inputs/`
2. Run conversion to ensure it works
3. Generate golden test case:
   ```bash
   task generate-corpus
   ```

### Method 2: Manual Creation
1. Create test case directory: `tests/corpus/my_test/`
2. Create `inputs/` and `expected_outputs/` subdirectories  
3. Add input files to `inputs/`
4. Run conversion and copy outputs to `expected_outputs/`
5. Create `test_config.json` with test metadata

### Method 3: Template-Based
```bash
python tools/oscalize/cli.py create-template tests/corpus/ my_test
```

## Test Categories

Organize test cases by category:

- **`basic_functionality`** - Core conversion features
- **`edge_cases`** - Unusual formatting or content
- **`validation_errors`** - Cases that should fail validation  
- **`fedramp_compliance`** - FedRAMP-specific requirements
- **`performance`** - Large or complex documents

## Best Practices

### Golden Output Management
- **Keep golden outputs current** - Regenerate when legitimate changes occur
- **Version control everything** - Track changes to golden outputs
- **Document changes** - Explain why golden outputs were updated

### Test Case Design
- **Focused test cases** - Each case should test specific functionality
- **Minimal but complete** - Include just enough content to test the feature
- **Clear descriptions** - Explain what each test case validates

### Validation Status
- **COMPLIANT** - Should pass NIST oscal-cli validation
- **NON_COMPLIANT** - Expected to have validation errors
- **UNKNOWN** - Validation status not determined

## Troubleshooting

### Common Issues

**"No test cases found"**
- Ensure test directories have proper structure
- Check that `test_config.json` files are valid JSON
- Verify input and output files exist

**"Conversion failed"**  
- Check input file format and content
- Verify mapping configurations are correct
- Review conversion logs for errors

**"Output mismatch"**
- Compare actual vs expected outputs manually
- Check if legitimate changes require golden output updates
- Review deep comparison logic for edge cases

**"Validation failed"**
- Run oscal-cli directly on outputs to debug
- Check OSCAL structure compliance  
- Verify expected validation status is correct

### Performance Tuning

For large corpus testing:
- Run without validation for faster feedback
- Use working directory on fast storage
- Parallelize independent test cases
- Cache conversion results when possible

## Integration with CI/CD

The corpus testing framework integrates with continuous integration:

```yaml
# Example CI configuration
- name: Run Corpus Testing
  run: |
    task test-corpus-enhanced
    task validate-corpus
```

## Extending the Framework

The framework supports custom test types and validation logic:

- **Custom comparisons** - Extend deep comparison for specific OSCAL elements
- **Test categories** - Add new test categorization schemes  
- **Validation modes** - Support different validation profiles
- **Performance metrics** - Track conversion performance over time

## References

- [NIST OSCAL v1.1.3](https://pages.nist.gov/OSCAL-Reference/)
- [FedRAMP Requirements](https://www.fedramp.gov/)
- [Oscalize Documentation](../../../CLAUDE.md)