import logging
import os

def get_logger(name: str = "xungungo") -> logging.Logger:
    logger = logging.getLogger(name)
    level = logging.DEBUG if os.getenv("XUNGUNGO_DEBUG") == "1" else logging.INFO
    if logger.level != level:
        logger.setLevel(level)
    if logger.handlers:
        return logger
    h = logging.StreamHandler()
    h.setLevel(level)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    h.setFormatter(fmt)
    logger.addHandler(h)
    return logger
