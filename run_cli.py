# run_cli.py
import sys
from pdf_optimizer.cli.main import PDFOptimizerCLI

if __name__ == '__main__':
    cli = PDFOptimizerCLI()
    sys.exit(cli.run())