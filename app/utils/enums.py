from enum import Enum

class RoleEnum(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    DOCTOR = "doctor"
    RECEPTIONIST = "receptionist"

class GenderEnum(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    
class BloodGroupEnum(str, Enum):
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"


class PatientStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLACKLISTED = "BLACKLISTED"
    
class PatientCategoryEnum(str, Enum):
    REGULAR = "REGULAR"
    VIP = "VIP"
    INSURANCE = "INSURANCE"
    NEW = "NEW"
    CHILD = "CHILD"
    SENIOR = "SENIOR"


class FamilyRelationshipEnum(str, Enum):
    SPOUSE = "SPOUSE"
    HUSBAND = "HUSBAND"
    WIFE = "WIFE"

    FATHER = "FATHER"
    MOTHER = "MOTHER"

    SON = "SON"
    DAUGHTER = "DAUGHTER"

    BROTHER = "BROTHER"
    SISTER = "SISTER"

    GRANDPARENT = "GRANDPARENT"
    GRANDCHILD = "GRANDCHILD"

    OTHER = "OTHER"
    
# Appointment
class AppointmentTypeEnum(str, Enum):
    BOOKED = "BOOKED"
    WALK_IN = "WALK_IN"
    FOLLOW_UP = "FOLLOW_UP"


class AppointmentStatusEnum(str, Enum):
    BOOKED = "BOOKED"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"
    CANCELLED = "CANCELLED"

class AppointmentSourceEnum(str, Enum):
    ONLINE = "ONLINE"
    PHONE = "PHONE"
    WALK_IN = "WALK_IN"
    WHATSAPP = "WHATSAPP"
    INSTAGRAM = "INSTAGRAM"
    FRONT_DESK = "FRONT_DESK"
    
class AppointmentProcedureStatusEnum(str, Enum):
    PLANNED = "planned"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class PaymentStatusEnum(str, Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    REFUNDED = "REFUNDED"


class QueueStatusEnum(str, Enum):
    WAITING = "WAITING"
    CALLED = "CALLED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    SKIPPED = "SKIPPED"

class ProcedureStatusEnum(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    BILLED = "BILLED"
    
class ProcedureCategoryEnum(str, Enum):
    DIAGNOSTIC = "DIAGNOSTIC"
    PREVENTIVE = "PREVENTIVE"
    RESTORATIVE = "RESTORATIVE"
    SURGICAL = "SURGICAL"
    COSMETIC = "COSMETIC"
    ORTHODONTIC = "ORTHODONTIC"
    ENDODONTIC = "ENDODONTIC"
    PERIODONTIC = "PERIODONTIC"
    PROSTHODONTIC = "PROSTHODONTIC"
    OTHER = "OTHER"