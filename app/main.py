from fastapi import FastAPI

from app.api.routes import router
from app.middleware.error_handler import register_error_handlers
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.payload_size import PayloadSizeLimitMiddleware
from app.logging.logger import configure_logging

configure_logging()

app = FastAPI(title="URL Audit Service", version="1.0.0")

# Added in reverse-execution order: last added runs first.
app.add_middleware(PayloadSizeLimitMiddleware)
app.add_middleware(RequestIdMiddleware)

app.include_router(router)
register_error_handlers(app)
