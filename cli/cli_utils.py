from ingestion.factory import get_registered_providers

def setup_cli_parser(parser):
    """Add ingestor-related arguments to CLI parser."""
    parser.add_argument('--provider', 
                      choices=get_registered_providers() + ['auto'],
                      default='auto',
                      help='CI provider for the log file (default: auto-detect)')