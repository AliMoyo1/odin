from fastapi import Header

_VALID = {"web", "whatsapp", "terminal", "system"}


async def get_origin(x_interface_origin: str | None = Header(default=None)) -> str:
    if x_interface_origin and x_interface_origin in _VALID:
        return x_interface_origin
    return "web"
