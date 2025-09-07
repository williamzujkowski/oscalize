#!/usr/bin/env python3
"""
oscalize CLI - LLM-free local converter for OSCAL compliance documents

Converts .docx/.md SSP content and .xlsx appendices (POA&M, Integrated Inventory, CIS/CRM)
into OSCAL v1.1.3 JSON artifacts, validates with NIST oscal-cli, and emits signed bundles.

Anchors: OSCAL v1.1.3, OMB M-24-15, SP 800-53 Release 5.2.0, SP 800-171 r3, SP 800-18 r1
"""

import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import our modules - handle both direct execution and module import
try:
    from .readers import DocumentReader, POAMReader, InventoryReader
    from .mappers import SSPMapper, POAMMapper, InventoryMapper, AssessmentMapper
    from .cir import CIRValidator, CIRProcessor
    from .validation import OSCALValidator, ValidationReporter
    from .packaging import BundleCreator, ManifestGenerator
except ImportError:
    # If relative imports fail, try absolute imports (when run directly)
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from oscalize.readers import DocumentReader, POAMReader, InventoryReader
    from oscalize.mappers import SSPMapper, POAMMapper, InventoryMapper, AssessmentMapper
    from oscalize.cir import CIRValidator, CIRProcessor
    from oscalize.validation import OSCALValidator, ValidationReporter
    from oscalize.packaging import BundleCreator, ManifestGenerator

# Set up console and logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, show_time=False, show_path=False)]
)
logger = logging.getLogger("oscalize")

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-error output')
@click.pass_context
def cli(ctx, verbose: bool, quiet: bool):
    """oscalize - LLM-free local OSCAL converter for FedRAMP compliance documents"""
    ctx.ensure_object(dict)
    
    if quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet


@cli.command()
@click.argument('inputs', nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), 
              default=Path('dist/oscal'), help='Output directory for OSCAL artifacts')
@click.option('--mapping-dir', type=click.Path(exists=True, path_type=Path),
              default=Path('mappings'), help='Directory containing mapping configurations')
@click.option('--schema-dir', type=click.Path(exists=True, path_type=Path),
              default=Path('schemas'), help='Directory containing CIR JSON schemas')
@click.pass_context
def convert(ctx, inputs: List[Path], output: Path, mapping_dir: Path, schema_dir: Path):
    """Convert input documents to OSCAL artifacts
    
    Accepts .docx/.md files for SSP content and .xlsx files for appendices
    (POA&M, Integrated Inventory Workbook, CIS/CRM).
    """
    if not inputs:
        logger.error("No input files specified")
        sys.exit(1)
    
    output.mkdir(parents=True, exist_ok=True)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Phase 1: Read and validate inputs
        read_task = progress.add_task("Reading input documents...", total=None)
        cir_data = {}
        
        for input_path in inputs:
            try:
                if input_path.suffix.lower() in ['.docx', '.md']:
                    reader = DocumentReader(input_path)
                    cir_data['document'] = reader.to_cir()
                elif input_path.name.lower().startswith('poam') and input_path.suffix.lower() == '.xlsx':
                    reader = POAMReader(input_path)
                    cir_data['poam'] = reader.to_cir()
                elif input_path.name.lower().startswith('inventory') and input_path.suffix.lower() == '.xlsx':
                    reader = InventoryReader(input_path)
                    cir_data['inventory'] = reader.to_cir()
                else:
                    logger.warning(f"Unsupported file type: {input_path}")
            except Exception as e:
                logger.error(f"Failed to read {input_path}: {e}")
                if ctx.obj['verbose']:
                    logger.exception(e)
                sys.exit(1)
        
        progress.update(read_task, description="Validating CIR data...")
        
        # Phase 2: Validate CIR against schemas
        validator = CIRValidator(schema_dir)
        processor = CIRProcessor()
        
        for data_type, data in cir_data.items():
            if not validator.validate(data, f"cir_{data_type}.json"):
                logger.error(f"CIR validation failed for {data_type}")
                sys.exit(1)
            
            # Process and normalize CIR data
            cir_data[data_type] = processor.process(data, data_type)
        
        # Phase 3: Map CIR to OSCAL
        progress.update(read_task, description="Mapping to OSCAL...")
        
        oscal_artifacts = {}
        
        if 'document' in cir_data:
            ssp_mapper = SSPMapper(mapping_dir)
            oscal_artifacts['ssp'] = ssp_mapper.map(cir_data)
        
        if 'poam' in cir_data:
            poam_mapper = POAMMapper(mapping_dir)
            oscal_artifacts['poam'] = poam_mapper.map(cir_data['poam'])
        
        if 'inventory' in cir_data:
            inventory_mapper = InventoryMapper(mapping_dir)
            # Integrate inventory into SSP
            if 'ssp' in oscal_artifacts:
                ssp_mapper.integrate_inventory(oscal_artifacts['ssp'], cir_data['inventory'])
        
        # Phase 4: Write OSCAL outputs
        progress.update(read_task, description="Writing OSCAL artifacts...")
        
        for artifact_type, artifact_data in oscal_artifacts.items():
            output_path = output / f"{artifact_type}.json"
            with open(output_path, 'w') as f:
                json.dump(artifact_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Generated: {output_path}")
    
    logger.info(f"Conversion completed. Outputs in: {output}")


@cli.command()
@click.argument('validation_dir', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path),
              help='Output file for validation summary')
@click.pass_context
def validation_summary(ctx, validation_dir: Path, output: Optional[Path]):
    """Generate validation summary from oscal-cli logs"""
    reporter = ValidationReporter(validation_dir)
    summary = reporter.generate_summary()
    
    if output:
        with open(output, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Validation summary written to: {output}")
    else:
        console.print_json(data=summary)


@cli.command()
@click.argument('oscal_dir', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path),
              help='Output bundle file')
@click.pass_context
def bundle(ctx, oscal_dir: Path, output: Optional[Path]):
    """Create signed deployment bundle with manifest"""
    if not output:
        output = Path('dist') / 'oscalize-bundle.tar.gz'
    
    output.parent.mkdir(parents=True, exist_ok=True)
    
    creator = BundleCreator()
    bundle_path = creator.create_bundle(oscal_dir, output)
    
    logger.info(f"Bundle created: {bundle_path}")


@cli.command()
@click.argument('oscal_dir', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path),
              help='Output manifest file')
@click.pass_context
def manifest(ctx, oscal_dir: Path, output: Optional[Path]):
    """Generate manifest with hashes and timestamps"""
    if not output:
        output = oscal_dir / 'manifest.json'
    
    generator = ManifestGenerator()
    manifest_data = generator.generate(oscal_dir)
    
    with open(output, 'w') as f:
        json.dump(manifest_data, f, indent=2)
    
    logger.info(f"Manifest generated: {output}")


@cli.command()
@click.argument('corpus_dir', type=click.Path(exists=True, path_type=Path))
@click.pass_context
def test_corpus(ctx, corpus_dir: Path):
    """Test conversion against corpus of known inputs/outputs"""
    from .testing import CorpusTester
    
    tester = CorpusTester(corpus_dir)
    results = tester.run_tests()
    
    if results['passed'] == results['total']:
        logger.info(f"All {results['total']} corpus tests passed")
    else:
        logger.error(f"{results['failed']} of {results['total']} corpus tests failed")
        sys.exit(1)


@cli.command()
@click.argument('oscal_dir', type=click.Path(exists=True, path_type=Path))
@click.pass_context
def compliance_check(ctx, oscal_dir: Path):
    """Check compliance with M-24-15 and FedRAMP requirements"""
    from .compliance import ComplianceChecker
    
    checker = ComplianceChecker()
    results = checker.check_directory(oscal_dir)
    
    console.print_json(data=results)
    
    if not results['compliant']:
        logger.error("Compliance check failed")
        sys.exit(1)


@cli.command()
@click.option('--check-deps', is_flag=True, help='Check required dependencies')
@click.option('--check-oscal-cli', is_flag=True, help='Check NIST oscal-cli availability')
def doctor(check_deps: bool, check_oscal_cli: bool):
    """Diagnostic tool for oscalize installation"""
    if check_deps or not (check_deps or check_oscal_cli):
        _check_python_deps()
    
    if check_oscal_cli or not (check_deps or check_oscal_cli):
        _check_oscal_cli()


def _check_python_deps():
    """Check Python dependencies"""
    required = ['pandas', 'openpyxl', 'pypandoc', 'jsonschema', 'click', 'rich']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        logger.error(f"Missing Python dependencies: {', '.join(missing)}")
        logger.info("Run: pip install -r requirements.txt")
    else:
        logger.info("All Python dependencies satisfied")


def _check_oscal_cli():
    """Check NIST oscal-cli availability"""
    import subprocess
    
    try:
        result = subprocess.run(['oscal-cli', '--version'], 
                              capture_output=True, text=True, check=True)
        logger.info(f"oscal-cli found: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("oscal-cli not found or not working")
        logger.info("Install with: task install-oscal-cli")


if __name__ == '__main__':
    cli()