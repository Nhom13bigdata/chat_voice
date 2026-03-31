"""
Electronic Medical Records (EMR) Service
Mock implementation - replace with your actual EMR API
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class EMRService:
    """Mock EMR service for storing patient data"""

    def __init__(self):
        # In-memory storage (replace with real database)
        self.records = {}

    async def save_intake(self, intake_data: Dict) -> Dict:
        """
        Save medical intake data to EMR

        Args:
            intake_data: Extracted medical data from conversation

        Returns:
            Dict with record_id and status
        """
        # Simulate API delay
        await asyncio.sleep(0.15)

        # Generate record ID
        record_id = f"EMR-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Store record
        self.records[record_id] = {
            "record_id": record_id,
            "data": intake_data,
            "created_at": datetime.now().isoformat(),
            "status": "active",
        }

        logger.info(f"Saved intake to EMR: {record_id}")

        return {
            "success": True,
            "record_id": record_id,
            "message": "Medical intake saved successfully",
        }

    async def get_patient_history(self, patient_id: str) -> Optional[Dict]:
        """
        Retrieve patient medical history

        Args:
            patient_id: Patient identifier

        Returns:
            Patient history dict or None
        """
        await asyncio.sleep(0.1)

        # Mock patient history
        history = {
            "patient_id": patient_id,
            "previous_visits": [],
            "chronic_conditions": [],
            "last_visit": None,
        }

        return history

    async def update_patient_record(self, record_id: str, updates: Dict) -> Dict:
        """
        Update existing patient record

        Args:
            record_id: EMR record identifier
            updates: Fields to update

        Returns:
            Dict with update status
        """
        await asyncio.sleep(0.1)

        if record_id in self.records:
            self.records[record_id]["data"].update(updates)
            self.records[record_id]["updated_at"] = datetime.now().isoformat()

            logger.info(f"Updated EMR record: {record_id}")

            return {
                "status": "success",
                "record_id": record_id,
                "message": "Record updated successfully",
            }
        else:
            logger.warning(f"Record not found: {record_id}")

            return {
                "status": "error",
                "record_id": record_id,
                "message": "Record not found",
            }

    async def search_patient(
        self,
        name: Optional[str] = None,
        dob: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Dict:
        """
        Search for patient records

        Args:
            name: Patient name
            dob: Date of birth
            phone: Phone number

        Returns:
            Dict with search results
        """
        await asyncio.sleep(0.2)

        # Mock search results
        results = [
            {
                "patient_id": "PAT-123456",
                "name": name or "John Doe",
                "dob": dob or "1980-01-15",
                "phone": phone or "555-0123",
            }
        ]

        logger.info(f"Patient search: {len(results)} results")

        return {"status": "success", "count": len(results), "results": results}


# Singleton instance
emr_service = EMRService()
