import os
from dotenv import load_dotenv

load_dotenv()

HOST = "127.0.0.1"
PORT = 8002
URL = f"http://{HOST}:{PORT}/koi-net"

FIRST_CONTACT = "http://127.0.0.1:8000/koi-net"

HACKMD_API_TOKEN = os.environ["HACKMD_API_TOKEN"]