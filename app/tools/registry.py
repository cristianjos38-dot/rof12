from types import MappingProxyType


AUTHORIZED_TOOLS = MappingProxyType({"refund_service": "refund_service"})


def is_registered(tool_name: str) -> bool:
    return tool_name in AUTHORIZED_TOOLS

