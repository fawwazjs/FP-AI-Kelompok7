from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Data permintaan tidak valid. Periksa kembali format, tipe, dan batas panjang input.",
                "errors": [
                    {
                        "loc": list(error.get("loc", [])),
                        "msg": _translate_validation_message(str(error.get("msg", "Input tidak valid."))),
                        "type": str(error.get("type", "value_error")),
                    }
                    for error in exc.errors()
                ],
            },
        )


def _translate_validation_message(message: str) -> str:
    if message.startswith("Value error, "):
        return message.removeprefix("Value error, ")
    if message == "Field required":
        return "Field wajib diisi."
    if message.startswith("Input should be"):
        return "Nilai input tidak sesuai dengan pilihan yang didukung."
    return message
