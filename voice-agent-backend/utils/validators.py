"""
Custom validators for medical intake data
"""

import re
from typing import Optional, Tuple
from datetime import datetime


def validate_phone_number(phone: str) -> Tuple[bool, Optional[str]]:
    """Validate and format US phone numbers"""
    if not phone:
        return False, "Phone number is required"

    # Remove separators
    cleaned = re.sub(r"[\s\-\(\)\.]", "", phone)

    if not cleaned.isdigit():
        return False, "Phone must contain only digits"

    # Format as (XXX) XXX-XXXX
    if len(cleaned) == 10:
        formatted = f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
        return True, formatted
    elif len(cleaned) == 11 and cleaned[0] == "1":
        formatted = f"+1 ({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:]}"
        return True, formatted

    return False, "Phone must be 10 digits (or 11 with country code)"


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """Validate email format"""
    if not email:
        return False, "Email is required"

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False, "Invalid email format"

    return True, None


def validate_date_of_birth(dob: str) -> Tuple[bool, Optional[str]]:
    """Validate DOB with age checks"""
    if not dob:
        return False, "Date of birth is required"

    # Try multiple formats
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"]:
        try:
            birth_date = datetime.strptime(dob, fmt)
            break
        except ValueError:
            continue
    else:
        return False, "Invalid date format. Use YYYY-MM-DD or MM/DD/YYYY"

    # Future date check
    if birth_date > datetime.now():
        return False, "Date of birth cannot be in the future"

    # Realistic age check (< 120 years)
    age_years = (datetime.now() - birth_date).days / 365.25
    if age_years > 120:
        return False, "Date of birth is unrealistic"

    return True, None


def validate_allergy_severity(severity: str) -> Tuple[bool, Optional[str]]:
    """Enforce severity levels for allergies"""
    valid_levels = ["mild", "moderate", "serious", "life-threatening"]

    if not severity:
        return False, "Severity is required"

    if severity.lower() not in valid_levels:
        return False, f"Severity must be one of: {', '.join(valid_levels)}"

    return True, None


def sanitize_text_input(text: str, max_length: int = 500) -> str:
    """Remove control characters and limit length"""
    if not text:
        return ""

    # Remove control characters
    cleaned = re.sub(r"[\x00-\x1F\x7F]", "", text)

    # Trim whitespace
    cleaned = cleaned.strip()

    # Enforce max length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned


def validate_medication_name(medication: str) -> Tuple[bool, Optional[str]]:
    """Validate medication name"""
    if not medication:
        return False, "Medication name is required"

    if len(medication) < 2:
        return False, "Medication name too short"

    if len(medication) > 100:
        return False, "Medication name too long"

    # Check for valid characters (letters, numbers, spaces, hyphens)
    if not re.match(r"^[a-zA-Z0-9\s\-]+$", medication):
        return False, "Medication name contains invalid characters"

    return True, None


def validate_symptom_severity(severity: str) -> Tuple[bool, Optional[str]]:
    """Validate symptom severity (1-10 scale)"""
    if not severity:
        return False, "Severity is required"

    # Try to extract number from string
    numbers = re.findall(r"\d+", str(severity))

    if not numbers:
        return False, "Severity must include a number (1-10)"

    level = int(numbers[0])

    if level < 1 or level > 10:
        return False, "Severity must be between 1 and 10"

    return True, str(level)


def validate_insurance_member_id(member_id: str) -> Tuple[bool, Optional[str]]:
    """Validate insurance member ID"""
    if not member_id:
        return False, "Member ID is required"

    # Remove spaces and hyphens
    cleaned = re.sub(r"[\s\-]", "", member_id)

    # Check if alphanumeric
    if not cleaned.isalnum():
        return False, "Member ID must be alphanumeric"

    # Check length (6-20 characters)
    if len(cleaned) < 6 or len(cleaned) > 20:
        return False, "Member ID must be 6-20 characters"

    return True, cleaned.upper()


def validate_medical_record_completeness(intake_data: dict) -> Tuple[bool, list]:
    """Check if required fields are present"""
    required_fields = ["patient_info", "present_illness", "allergies"]
    missing_fields = []

    for field in required_fields:
        if field not in intake_data or not intake_data[field]:
            missing_fields.append(field)

    is_complete = len(missing_fields) == 0
    return is_complete, missing_fields


def validate_critical_allergies(allergies: list) -> Tuple[bool, Optional[str]]:
    """Validate critical allergy entries"""
    if not allergies:
        return True, None  # No allergies is valid

    for idx, allergy in enumerate(allergies):
        if not isinstance(allergy, dict):
            return False, f"Allergy {idx + 1} must be a dictionary"

        # Check required fields
        if "allergen" not in allergy or not allergy["allergen"]:
            return False, f"Allergy {idx + 1} missing allergen"

        if "reaction" not in allergy or not allergy["reaction"]:
            return False, f"Allergy {idx + 1} missing reaction"

        if "severity" not in allergy or not allergy["severity"]:
            return False, f"Allergy {idx + 1} missing severity"

        # Validate severity
        is_valid, error = validate_allergy_severity(allergy["severity"])
        if not is_valid:
            return False, f"Allergy {idx + 1}: {error}"

    return True, None
