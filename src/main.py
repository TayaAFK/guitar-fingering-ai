import logging
import os

import uvicorn

from src.app import create_app

if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    # In-memory storage => a single process only.
    uvicorn.run(create_app())
