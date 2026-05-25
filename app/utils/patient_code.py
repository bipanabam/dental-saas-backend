def generate_patient_code(patient_id: int, tenant_name: str) -> str:
    """
    Generate patient code like:
    Bam Dental Clinic -> BDC-000123
    """
    # Take first letter of each word
    tenant_prefix = "".join(
        word[0] for word in tenant_name.split() if word
    ).upper()
    return f"{tenant_prefix}-{patient_id:06d}"