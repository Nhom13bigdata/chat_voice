import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class InsuranceService:
    """Mock insurance verification service"""

    def __init__(self):
        # Mock insurance providers
        self.providers = {
            "aetna": "Aetna",
            "bcbs": "Blue Cross Blue Shield",
            "cigna": "Cigna",
            "uhc": "UnitedHealthcare",
            "kaiser": "Kaiser Permanente",
        }

    async def verify_coverage(self, member_id: str, provider: str) -> Dict:
        await asyncio.sleep(0.2)

        is_active = True
        provider_normalized = provider.lower().replace(" ", "")

        provider_name = self.providers.get(provider_normalized, provider.title())

        logger.info(f"Verified insurance: {provider_name} - {member_id}")

        return {
            "status": "active" if is_active else "inactive",
            "member_id": member_id,
            "provider": provider_name,
            "coverage_type": "PPO",
            "copay": "$25",
            "deductible": "$1,500",
            "deductible_met": "$450",
            "out_of_pocket_max": "$6,000",
            "effective_date": "2024-01-01",
            "termination_date": None,
            "verified_at": datetime.now().isoformat(),
        }

    async def check_eligibility(
        self, member_id: str, provider: str, service_type: str = "medical"
    ) -> Dict:
        await asyncio.sleep(0.2)

        logger.info(f"Checking eligibility: {service_type} for {member_id}")

        return {
            "status": "eligible",
            "member_id": member_id,
            "provider": provider,
            "service_type": service_type,
            "prior_authorization_required": False,
            "referral_required": False,
            "in_network": True,
            "coverage_percentage": 80,
            "checked_at": datetime.now().isoformat(),
        }

    async def get_benefits(self, member_id: str, provider: str) -> Dict:
        await asyncio.sleep(0.2)

        logger.info(f"Retrieved benefits for: {member_id}")

        return {
            "member_id": member_id,
            "provider": provider,
            "benefits": {
                "office_visit": {"copay": "$25", "coverage": "80%"},
                "specialist_visit": {"copay": "$50", "coverage": "80%"},
                "emergency_room": {"copay": "$250", "coverage": "80%"},
                "urgent_care": {"copay": "$75", "coverage": "80%"},
                "lab_work": {"copay": "$0", "coverage": "100%"},
                "prescription": {"tier1": "$10", "tier2": "$30", "tier3": "$60"},
            },
            "retrieved_at": datetime.now().isoformat(),
        }

    async def submit_pre_authorization(
        self, member_id: str, provider: str, procedure_code: str, diagnosis_code: str
    ) -> Dict:
        await asyncio.sleep(0.3)

        auth_number = f"AUTH-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        logger.info(f"Pre-authorization submitted: {auth_number}")

        return {
            "status": "approved",
            "authorization_number": auth_number,
            "member_id": member_id,
            "provider": provider,
            "procedure_code": procedure_code,
            "diagnosis_code": diagnosis_code,
            "approved_units": 1,
            "valid_from": datetime.now().isoformat(),
            "valid_until": (datetime.now() + timedelta(days=90)).isoformat(),
            "submitted_at": datetime.now().isoformat(),
        }


# Singleton instance
insurance_service = InsuranceService()
