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
    RESCHEDULED = "RESCHEDULED"


class AppointmentStatusEnum(str, Enum):
    BOOKED = "BOOKED"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
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
    
class AppointmentCancellationReasonEnum(str, Enum):
    PATIENT_CANCELLED = "PATIENT_CANCELLED"
    DOCTOR_UNAVAILABLE = "DOCTOR_UNAVAILABLE"
    NO_SHOW = "NO_SHOW"
    RESCHEDULED = "RESCHEDULED"
    DUPLICATE_BOOKING = "DUPLICATE_BOOKING"
    EMERGENCY = "EMERGENCY"
    OTHER = "OTHER"
    
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
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"
    CANCELLED = "CANCELLED"
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
    
    

class EncounterStatusEnum(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"
    VOID = "VOID"  # cancelled mid-session

class TreatmentPlanStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"  # all items done
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    DEFERRED = "DEFERRED"
    CANCELLED = "CANCELLED"


class TreatmentPlanItemStatusEnum(str, Enum):
    PENDING = "PENDING"      # scheduled for a future visit
    DONE = "DONE"            # performed → Procedure created
    DEFERRED = "DEFERRED"    # postponed, still on the plan
    CANCELLED = "CANCELLED"  # removed from plan
    CHANGED = "CHANGED"      # doctor changed approach, replaced by different procedure


class InvestigationStatusEnum(str, Enum):
    REQUESTED = "REQUESTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"