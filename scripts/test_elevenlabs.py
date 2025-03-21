#!/usr/bin/env python
"""
Test script for ElevenLabs integration
This script attempts to get a signed URL from ElevenLabs, which is the
first step in establishing a WebSocket connection.
"""

import sys
import os
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_elevenlabs_integration(api_key=None, agent_id=None):
    """Test connecting to ElevenLabs"""

    # First, try to import required modules
    try:
        from src.wrappers.elevenlabs.toolbox import get_signed_url

        # This import checks if the elevenlabs package is installed properly
        import elevenlabs

        logger.info(f"Found elevenlabs package, version: {elevenlabs.__version__}")
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        logger.error(
            "Make sure elevenlabs package is installed: 'pip install elevenlabs'"
        )
        return False

    # Use environment variables if not provided
    if not api_key:
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        logger.info("Using API key from environment variable")

    if not agent_id:
        agent_id = os.environ.get("ELEVENLABS_AGENT_ID")
        logger.info("Using agent ID from environment variable")

    # Check if we have the required values
    if not api_key:
        logger.error("No API key provided")
        return False

    if not agent_id:
        logger.error("No agent ID provided")
        return False

    # Try to get a signed URL
    try:
        logger.info(f"Getting signed URL for agent ID: {agent_id}")
        signed_url = get_signed_url(api_key, agent_id)
        logger.info(
            f"Successfully got signed URL: {signed_url[:20]}...{signed_url[-20:]}"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to get signed URL: {e}")
        logger.exception("Stack trace:")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test ElevenLabs integration")
    parser.add_argument("--api-key", help="ElevenLabs API key")
    parser.add_argument("--agent-id", help="ElevenLabs agent ID")

    args = parser.parse_args()

    success = test_elevenlabs_integration(args.api_key, args.agent_id)

    if success:
        logger.info("✅ ElevenLabs integration test passed")
        sys.exit(0)
    else:
        logger.error("❌ ElevenLabs integration test failed")
        sys.exit(1)
