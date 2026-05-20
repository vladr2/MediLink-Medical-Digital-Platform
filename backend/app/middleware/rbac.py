from app.models.user import UserRole
from app.middleware.auth import require_roles, get_current_user

# Role dependencies - folosite ca Depends() în routere
require_admin = require_roles(UserRole.admin)

require_doctor = require_roles(UserRole.doctor)

require_assistant = require_roles(UserRole.assistant)

require_patient = require_roles(UserRole.patient)

require_medical_staff = require_roles(
    UserRole.admin,
    UserRole.doctor,
    UserRole.assistant,
)

require_doctor_or_admin = require_roles(
    UserRole.admin,
    UserRole.doctor,
)
