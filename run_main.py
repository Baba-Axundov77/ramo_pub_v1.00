#!/usr/bin/env python3
# run_main.py — Safe main.py runner with error handling
import sys
import os
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('main_debug.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Safe main function with comprehensive error handling"""
    try:
        logger.info("Starting Ramo Pub Desktop Application...")
        
        # Add current directory to Python path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
            logger.debug(f"Added to path: {current_dir}")
        
        # Import main module
        logger.info("Importing main module...")
        import main
        
        # Run main function
        logger.info("Running main function...")
        main.main()
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Please check that all required modules are installed:")
        logger.error("  - PyQt6")
        logger.error("  - requests")
        logger.error("  - sqlalchemy")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error("Full traceback:")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
