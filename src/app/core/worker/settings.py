from ...core.config import settings
from .functions import sample_background_task, shutdown, startup

class WorkerSettings:
    functions = [sample_background_task]
    on_startup = startup
    on_shutdown = shutdown
    handle_signals = False
