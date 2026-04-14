"""
routes/__init__.py
All Blueprints registered in one place.
"""

from .main               import main_bp          # noqa: F401
from .auth_routes        import auth_bp          # noqa: F401
from .patient_routes     import patient_bp       # noqa: F401
from .pregnancy_routes   import pregnancy_bp     # noqa: F401
from .vitals_routes      import vitals_bp        # noqa: F401
from .lab_routes         import lab_bp           # noqa: F401
from .appointment_routes import appointment_bp   # noqa: F401
from .report_routes      import report_bp        # noqa: F401

BLUEPRINTS = [
    main_bp,
    auth_bp,
    patient_bp,
    pregnancy_bp,
    vitals_bp,
    lab_bp,
    appointment_bp,
    report_bp,
]
