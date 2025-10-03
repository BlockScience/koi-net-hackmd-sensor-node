import threading
import signal
from .core import node, ingestion_service

def main():
    """Main entry point for the HackMD sensor node"""
    # Start ingestion service in background thread (synchronous loop)
    stop_event = threading.Event()

    def _run():
        ingestion_service.run_forever(stop_event)

    ingestion_thread = threading.Thread(target=_run, name="hackmd-ingestion", daemon=True)
    ingestion_thread.start()

    def _signal_handler(signum, frame):
        stop_event.set()

    # Attempt graceful stop on SIGINT/SIGTERM
    try:
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
    except Exception:
        pass

    # Start KOI-net server (blocking)
    node.server.run()

if __name__ == "__main__":
    main()
