import subprocess
import time
import webbrowser
import os
import sys
from pyngrok import ngrok, conf
from dotenv import load_dotenv
from pathlib import Path


def setup_ngrok():
    """Setup ngrok with auth token from .env file"""
    # First, load environment variables from .env file
    load_dotenv(Path(__file__).parent.parent / ".env")

    # Check if NGROK_AUTH_TOKEN is set in .env file
    auth_token = os.environ.get("NGROK_AUTH_TOKEN")

    if not auth_token:
        print("\n❌ Error: NGROK_AUTH_TOKEN not found in .env file")
        print("Please add NGROK_AUTH_TOKEN=your_token_here to your .env file")
        print(
            "You can get your auth token at https://dashboard.ngrok.com/get-started/your-authtoken"
        )
        sys.exit(1)

    # Set the authtoken in ngrok configuration
    conf.get_default().auth_token = auth_token
    print("✅ Ngrok auth token configured from .env file")


# Main execution
if __name__ == "__main__":
    try:
        # Step 0: Setup ngrok with authentication
        setup_ngrok()

        # Step 1: Start the FastAPI server in a separate process
        server_process = subprocess.Popen(["python", "main.py"])
        print("✅ FastAPI server started")

        # Wait a bit for the server to initialize
        time.sleep(10)

        # Step 2: Start ngrok tunnel to the FastAPI port (8127 as seen in main.py)
        # Use the static domain "immortal-mostly-mustang.ngrok-free.app"
        static_domain = "immortal-mostly-mustang.ngrok-free.app"
        ngrok_tunnel = ngrok.connect(addr="8127", domain=static_domain)
        public_url = ngrok_tunnel.public_url

        print(f"✅ Ngrok tunnel established with static domain: {public_url}")
        print("\n🌐 Your API is now publicly accessible at:")
        print(f"📊 API Docs (Swagger): {public_url}/documentation/swagger")
        print(f"📘 API Docs (ReDoc): {public_url}/documentation/redoc")

        # Open the Swagger UI in the default browser
        webbrowser.open(f"{public_url}/documentation/swagger")

        print("\n⌨️  Press Ctrl+C to stop the server and close the tunnel...")
        # Keep the script running until interrupted
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
    finally:
        # Step 3: Clean up on exit
        try:
            ngrok.kill()
            print("✅ Ngrok tunnel closed")
        except Exception:
            pass

        try:
            server_process.terminate()
            print("✅ Server stopped")
        except Exception:
            pass
