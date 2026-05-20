from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.middleware.rbac import require_admin, require_medical_staff, require_assistant
from app.models.user import User, UserRole
from app.models.doctor import Doctor
from app.models.doctor_patient import DoctorPatient
from app.models.patient import Patient
from app.schemas.doctor import DoctorCreate, DoctorResponse, DoctorWithUser
from app.schemas.patient import PatientWithUser

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("/", response_model=List[DoctorWithUser])
def list_doctors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doctors = db.query(Doctor).join(Doctor.user).all()
    result = []
    for d in doctors:
        data = DoctorWithUser(
            id=d.id,
            user_id=d.user_id,
            specialization=d.specialization,
            license_number=d.license_number,
            department=d.department,
            bio=d.bio,
            phone_cabinet=d.phone_cabinet,
            schedule=d.schedule,
            email=d.user.email,
            is_active=d.user.is_active,
            first_name=d.user.first_name,
            last_name=d.user.last_name,
        )
        result.append(data)
    return result


@router.post("/", response_model=DoctorResponse)
def create_doctor_profile(
    data: DoctorCreate,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = (
        db.query(User).filter(User.id == user_id, User.role == UserRole.doctor).first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Doctor user not found")

    existing = db.query(Doctor).filter(Doctor.user_id == user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Doctor profile already exists")

    doctor = Doctor(
        user_id=user_id,
        specialization=data.specialization,
        license_number=data.license_number,
        department=data.department,
        bio=data.bio,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


@router.get("/me", response_model=DoctorResponse)
def get_my_doctor_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    return doctor


@router.put("/me", response_model=DoctorResponse)
def update_my_doctor_profile(
    data: DoctorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.doctor:
        raise HTTPException(status_code=403, detail="Access denied")

    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(doctor, field, value)

    db.commit()
    db.refresh(doctor)
    return doctor


@router.get("/specialization/{specialization}", response_model=List[DoctorWithUser])
def get_doctors_by_specialization(
    specialization: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doctors = (
        db.query(Doctor)
        .join(Doctor.user)
        .filter(Doctor.specialization.ilike(f"%{specialization}%"))
        .all()
    )
    result = []
    for d in doctors:
        data = DoctorWithUser(
            id=d.id,
            user_id=d.user_id,
            specialization=d.specialization,
            license_number=d.license_number,
            department=d.department,
            bio=d.bio,
            phone_cabinet=d.phone_cabinet,
            schedule=d.schedule,
            email=d.user.email,
            is_active=d.user.is_active,
            first_name=d.user.first_name,
            last_name=d.user.last_name,
        )
        result.append(data)
    return result


@router.get("/by-user/{user_id}", response_model=DoctorWithUser)
def get_doctor_by_user_id(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Profil public doctor — accesat de pacienți la selectarea doctorului."""
    doctor = db.query(Doctor).join(Doctor.user).filter(Doctor.user_id == user_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return DoctorWithUser(
        id=doctor.id,
        user_id=doctor.user_id,
        specialization=doctor.specialization,
        license_number=doctor.license_number,
        department=doctor.department,
        bio=doctor.bio,
        phone_cabinet=doctor.phone_cabinet,
        schedule=doctor.schedule,
        email=doctor.user.email,
        is_active=doctor.user.is_active,
        first_name=doctor.user.first_name,
        last_name=doctor.user.last_name,
    )


@router.get("/my-patients", response_model=List[PatientWithUser])
def get_my_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.doctor:
        raise HTTPException(status_code=403, detail="Access denied")

    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    doctor_patients = (
        db.query(DoctorPatient).filter(DoctorPatient.doctor_id == doctor.id).all()
    )
    patient_ids = [dp.patient_id for dp in doctor_patients]

    if not patient_ids:
        return []

    patients = (
        db.query(Patient).join(Patient.user).filter(Patient.id.in_(patient_ids)).all()
    )
    result = []
    for p in patients:
        data = PatientWithUser(
            id=p.id,
            user_id=p.user_id,
            blood_type=p.blood_type,
            allergies=p.allergies,
            chronic_conditions=p.chronic_conditions,
            emergency_contact=p.emergency_contact,
            emergency_phone=p.emergency_phone,
            cnp=p.cnp,
            gender=p.gender,
            gdpr_consent_at=p.gdpr_consent_at,
            created_at=p.created_at,
            email=p.user.email,
            is_active=p.user.is_active,
            first_name=p.user.first_name,
            last_name=p.user.last_name,
        )
        result.append(data)
    return result


@router.post("/assign-patient/{patient_id}")
def assign_patient_to_doctor(
    patient_id: UUID,
    doctor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_assistant),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    existing = (
        db.query(DoctorPatient)
        .filter(
            DoctorPatient.doctor_id == doctor_id,
            DoctorPatient.patient_id == patient_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Patient already assigned to this doctor"
        )

    assignment = DoctorPatient(doctor_id=doctor_id, patient_id=patient_id)
    db.add(assignment)
    db.commit()
    return {"message": "Patient assigned successfully"}
