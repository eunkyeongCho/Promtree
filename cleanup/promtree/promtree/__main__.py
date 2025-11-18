from .promtree import PromTree
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(
        description='Convert PDF to Markdown using promtree',
        prog='promtree'
    )
    
    parser.add_argument(
        'pdf_path',
        type=str,
        help='Path to the PDF file to convert'
    )
    
    parser.add_argument(
        '--output-md',
        type=str,
        default=None,
        help='Output markdown file path (optional)'
    )
    
    parser.add_argument(
        '--cleanup',
        action='store_true',
        default=False,
        help='Enable cleanup mode (default: False)'
    )
        
    args = parser.parse_args()
    
    try:
        result = PromTree(
            pdf_path=args.pdf_path,
            output_md=args.output_md,
            cleanup=args.cleanup
        )
        print(f"Successfully converted: {result}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
