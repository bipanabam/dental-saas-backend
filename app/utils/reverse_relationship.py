
from app.utils.enums import FamilyRelationshipEnum, GenderEnum


def get_reverse_relationship(
    relationship: FamilyRelationshipEnum,
    patient_gender: GenderEnum | None
) -> FamilyRelationshipEnum:
    
    match relationship:

        case FamilyRelationshipEnum.SON:
            return (
                FamilyRelationshipEnum.FATHER
                if patient_gender == GenderEnum.MALE
                else FamilyRelationshipEnum.MOTHER
            )

        case FamilyRelationshipEnum.DAUGHTER:
            return (
                FamilyRelationshipEnum.FATHER
                if patient_gender == GenderEnum.MALE
                else FamilyRelationshipEnum.MOTHER
            )

        case FamilyRelationshipEnum.FATHER:
            return FamilyRelationshipEnum.SON

        case FamilyRelationshipEnum.MOTHER:
            return FamilyRelationshipEnum.DAUGHTER

        case FamilyRelationshipEnum.HUSBAND:
            return FamilyRelationshipEnum.WIFE

        case FamilyRelationshipEnum.WIFE:
            return FamilyRelationshipEnum.HUSBAND

        case FamilyRelationshipEnum.BROTHER:
            return FamilyRelationshipEnum.BROTHER

        case FamilyRelationshipEnum.SISTER:
            return FamilyRelationshipEnum.SISTER

        case FamilyRelationshipEnum.GRANDPARENT:
            return FamilyRelationshipEnum.GRANDCHILD

        case FamilyRelationshipEnum.GRANDCHILD:
            return FamilyRelationshipEnum.GRANDPARENT

        case _:
            return FamilyRelationshipEnum.OTHER