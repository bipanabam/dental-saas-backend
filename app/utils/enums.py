from enum import Enum


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


class FamilyRelationEnum(str, Enum):
    SELF = "SELF"
    SPOUSE = "SPOUSE"
    CHILD = "CHILD"
    PARENT = "PARENT"
    OTHER = "OTHER"