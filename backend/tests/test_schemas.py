"""
Teste pentru validatorii Pydantic (PatientCreate, UserCreate).
Teste pure unitare — nu necesită DB sau HTTP.
"""
import pytest
from pydantic import ValidationError
from app.schemas.patient import PatientCreate, PatientBase
from app.schemas.user import UserCreate
from app.models.user import UserRole


class TestPatientCreateValidation:
    """PatientCreate trebuie să valideze strict câmpurile sensibile."""

    # ── CNP ──────────────────────────────────────────────────────────────────
    def test_valid_cnp_13_digits(self):
        p = PatientCreate(cnp="1900101123456")
        assert p.cnp == "1900101123456"

    def test_cnp_too_short_raises(self):
        with pytest.raises(ValidationError) as exc:
            PatientCreate(cnp="123456")
        assert "13 cifre" in str(exc.value)

    def test_cnp_too_long_raises(self):
        with pytest.raises(ValidationError) as exc:
            PatientCreate(cnp="12345678901234")  # 14 cifre
        assert "13 cifre" in str(exc.value)

    def test_cnp_with_letters_raises(self):
        with pytest.raises(ValidationError) as exc:
            PatientCreate(cnp="190010112345X")
        assert "13 cifre" in str(exc.value)

    def test_cnp_empty_string_passes(self):
        """CNP gol este permis (câmp opțional)."""
        p = PatientCreate(cnp="")
        assert p.cnp == ""

    def test_cnp_none_passes(self):
        """CNP None este permis."""
        p = PatientCreate(cnp=None)
        assert p.cnp is None

    # ── Blood type ────────────────────────────────────────────────────────────
    def test_valid_blood_type_a_plus(self):
        p = PatientCreate(blood_type="A+")
        assert p.blood_type == "A+"

    def test_valid_blood_type_ab_minus(self):
        p = PatientCreate(blood_type="AB-")
        assert p.blood_type == "AB-"

    def test_invalid_blood_type_raises(self):
        with pytest.raises(ValidationError) as exc:
            PatientCreate(blood_type="XY")
        assert "Grupa sangvina invalida" in str(exc.value)

    def test_empty_blood_type_becomes_none(self):
        """Șirul gol pentru blood_type este convertit la None."""
        p = PatientCreate(blood_type="")
        assert p.blood_type is None

    def test_blood_type_none_passes(self):
        p = PatientCreate(blood_type=None)
        assert p.blood_type is None

    # ── Gender ────────────────────────────────────────────────────────────────
    def test_valid_gender_masculin(self):
        p = PatientCreate(gender="Masculin")
        assert p.gender == "Masculin"

    def test_valid_gender_feminin(self):
        p = PatientCreate(gender="Feminin")
        assert p.gender == "Feminin"

    def test_valid_gender_m(self):
        p = PatientCreate(gender="M")
        assert p.gender == "M"

    def test_invalid_gender_raises(self):
        with pytest.raises(ValidationError) as exc:
            PatientCreate(gender="unknown")
        assert "Gen invalid" in str(exc.value)

    def test_empty_gender_becomes_none(self):
        """Șirul gol pentru gen este convertit la None."""
        p = PatientCreate(gender="")
        assert p.gender is None

    # ── Emergency phone ───────────────────────────────────────────────────────
    def test_valid_phone(self):
        p = PatientCreate(emergency_phone="0722123456")
        assert p.emergency_phone == "0722123456"

    def test_valid_phone_with_spaces(self):
        p = PatientCreate(emergency_phone="0722 123 456")
        assert p.emergency_phone == "0722 123 456"

    def test_invalid_phone_too_short_raises(self):
        with pytest.raises(ValidationError):
            PatientCreate(emergency_phone="123")  # sub 7 caractere

    def test_empty_phone_becomes_none(self):
        p = PatientCreate(emergency_phone="")
        assert p.emergency_phone is None


class TestPatientBaseNoValidation:
    """PatientBase NU trebuie să valideze — e folosit pentru response (citire din DB)."""

    def test_any_blood_type_accepted(self):
        """DB-ul vechi poate conține valori nestandard — nu se ridică eroare."""
        p = PatientBase(blood_type="necunoscut")
        assert p.blood_type == "necunoscut"

    def test_any_gender_accepted(self):
        """Genul din DB (format vechi) nu ridică eroare."""
        p = PatientBase(gender="masculin")  # lowercase din date vechi
        assert p.gender == "masculin"

    def test_any_cnp_format_accepted(self):
        """CNP din DB (inclusiv valori incomplete) nu ridică eroare."""
        p = PatientBase(cnp="12345")
        assert p.cnp == "12345"


class TestUserCreatePasswordValidation:
    """Validarea parolei la înregistrare."""

    def test_valid_password(self):
        u = UserCreate(email="test@test.com", password="Admin123!", role=UserRole.patient)
        assert u.password == "Admin123!"

    def test_password_too_short_raises(self):
        with pytest.raises(ValidationError) as exc:
            UserCreate(email="test@test.com", password="Ab1!", role=UserRole.patient)
        assert "8 caractere" in str(exc.value)

    def test_password_no_uppercase_raises(self):
        with pytest.raises(ValidationError) as exc:
            UserCreate(email="test@test.com", password="admin123!", role=UserRole.patient)
        assert "literă mare" in str(exc.value)

    def test_password_no_digit_raises(self):
        with pytest.raises(ValidationError) as exc:
            UserCreate(email="test@test.com", password="AdminPass!", role=UserRole.patient)
        assert "cifră" in str(exc.value)

    def test_password_exactly_8_chars_passes(self):
        u = UserCreate(email="test@test.com", password="Admin12!", role=UserRole.patient)
        assert u.password == "Admin12!"
