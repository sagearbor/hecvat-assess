"""Pytest configuration and shared fixtures for HECVAT testing."""

import json
import os
import pytest
from pathlib import Path


# Path constants — SKILL_ROOT points to skills/hecvat-assess/ (2 levels up from tests/)
SKILL_ROOT = Path(__file__).parent.parent.parent
HECVAT_XLSX = SKILL_ROOT / "HECVAT414.xlsx"
SCRIPTS_DIR = SKILL_ROOT / "scripts"


@pytest.fixture
def hecvat_xlsx_path():
    """Absolute path to the real HECVAT414.xlsx file.

    This fixture provides the actual HECVAT file for integration tests.
    Tests can use this to validate parsing against real data.
    """
    assert HECVAT_XLSX.exists(), f"HECVAT414.xlsx not found at {HECVAT_XLSX}"
    return str(HECVAT_XLSX)


@pytest.fixture
def sample_assessment_data():
    """Sample assessment JSON data with known answers for testing report generation.

    Includes a variety of answer types:
    - Simple answers without evidence
    - Answers with additional_info
    - Answers with evidence
    - Answers with both additional_info and evidence

    This lets us test all code paths for filling the xlsx report.
    """
    return {
        "assessment_metadata": {
            "vendor": "Test Vendor Inc",
            "product": "Test Product",
            "assessed_at": "2026-02-13T12:00:00Z",
            "assessed_by": "Test Assessor"
        },
        "answers": {
            "GNRL-01": {
                "answer": "Test Vendor Inc",
                "additional_info": "",
                "evidence": ""
            },
            "GNRL-02": {
                "answer": "Test Product",
                "additional_info": "Cloud-based SaaS solution",
                "evidence": ""
            },
            "AAAI-01": {
                "answer": "Yes",
                "additional_info": "Multi-factor authentication implemented",
                "evidence": "auth/mfa.py lines 45-67"
            },
            "AAAI-02": {
                "answer": "Yes",
                "additional_info": "",
                "evidence": "Uses bcrypt with salt rounds=12"
            },
            "COMP-01": {
                "answer": "No",
                "additional_info": "Company has 50-100 employees",
                "evidence": ""
            },
            "DOCU-05": {
                "answer": "Yes",
                "additional_info": "",
                "evidence": "docs/architecture/ contains system diagrams"
            },
            "THRD-01": {
                "answer": "Yes",
                "additional_info": "All dependencies tracked in package.json and requirements.txt",
                "evidence": "See package.json:dependencies"
            }
        }
    }


@pytest.fixture
def empty_assessment_data():
    """Empty assessment with no answers.

    Tests that report generation handles empty/new assessments gracefully
    without crashing or corrupting the template.
    """
    return {
        "assessment_metadata": {
            "vendor": "Empty Test",
            "product": "Unanswered Assessment"
        },
        "answers": {}
    }


@pytest.fixture
def assessment_with_invalid_ids():
    """Assessment containing question IDs that don't exist in the template.

    Tests that generate_report.py silently skips non-existent IDs
    rather than crashing. This simulates scenarios where:
    - Assessment was created for a different HECVAT version
    - Question IDs were mistyped
    - Custom questions were added
    """
    return {
        "assessment_metadata": {
            "vendor": "Test Vendor"
        },
        "answers": {
            "GNRL-01": {
                "answer": "Valid Answer",
                "additional_info": "",
                "evidence": ""
            },
            "FAKE-99": {
                "answer": "This ID doesn't exist",
                "additional_info": "Should be skipped",
                "evidence": ""
            },
            "INVALID-ID": {
                "answer": "Also invalid",
                "additional_info": "",
                "evidence": ""
            }
        }
    }
