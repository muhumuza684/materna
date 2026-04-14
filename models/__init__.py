"""
models/__init__.py
Central import registry — ensures db.create_all() sees every table.
"""

from .patient      import Patient       # noqa: F401
from .pregnancy    import Pregnancy     # noqa: F401
from .vitals       import VitalSigns    # noqa: F401
from .labs         import LabResult     # noqa: F401
from .appointments import Appointment   # noqa: F401
from .user         import User, Role    # noqa: F401

__all__ = ["Patient", "Pregnancy", "VitalSigns", "LabResult", "Appointment", "User", "Role"]
