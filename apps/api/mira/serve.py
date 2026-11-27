"""CLI entrypoint to launch the Mira FastAPI server with structured logging.

Configures Mira's JSON/structured logger before handing off to Uvicorn with
Uvicorn's default access/log config disabled so all logs flow uniformly.
"""
from argparse import ArgumentParser

import uvicorn

from .observability import configure


def main():
    """Parse ``--host``/``--port`` CLI flags, configure logging, and run Uvicorn."""
    parser = ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    configure()
    # Disable uvicorn's built-in logging so Mira's observability formatter owns all output.
    uvicorn.run("mira.main:app", host=args.host, port=args.port, access_log=False, log_config=None)


if __name__ == "__main__":
    main()
