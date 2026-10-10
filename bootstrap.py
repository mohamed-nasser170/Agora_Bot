"""
bootstrap.py
════════════════════════════════════════════════════════════════
Agora — builds the application components. Shared by the web
server (server.py) and the CLI (main.py).
════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv(override=False)  # real environment variables win over .env (good for hosting)

from chains.chat_chain import AgoraChatChain  # noqa: E402
from graph.flow import AgoraFlow  # noqa: E402
from utils.helpers import get_logger  # noqa: E402

logger = get_logger("agora.bootstrap")


class ConfigError(RuntimeError):
    """Raised when required configuration (e.g. the API key) is missing."""


def build_flow() -> AgoraFlow:
    try:
        chain = AgoraChatChain()
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
    flow = AgoraFlow(chain)
    logger.info("Agora ready · model=%s", chain.model_name)
    return flow
