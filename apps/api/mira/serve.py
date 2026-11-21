"""Launch the API with Mira's logging configuration."""
from argparse import ArgumentParser

import uvicorn

from .observability import configure


def main():
    parser = ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    configure()
    uvicorn.run("mira.main:app", host=args.host, port=args.port, access_log=False, log_config=None)


if __name__ == "__main__":
    main()
