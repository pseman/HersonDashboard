from pydantic import BaseModel
from datetime import date, time
from typing import Optional

# Схемы для CriminalSituation
class CriminalSituationBase(BaseModel):
    omvd_name: str
    crime_date: date
    registration_place: Optional[str] = None
    registration_number: Optional[int] = None
    registration_date: Optional[date] = None
    crime_article: Optional[str] = None
    fraud_type: Optional[str] = None
    victim_gender: Optional[int] = None
    victim_birthday: Optional[date] = None
    crime_category_name: str
    sum_damage: Optional[float] = None

class CriminalSituationCreate(CriminalSituationBase):
    pass

class CriminalSituation(CriminalSituationBase):
    id: int
    
    class Config:
        from_attributes = True


# Схемы для MilitarySituation
class MilitarySituationBase(BaseModel):
    incident_date: date
    incident_time: Optional[time] = None
    incident_name: Optional[str] = None
    employe_action: Optional[str] = None
    time_cancel_incident: Optional[time] = None
    incident_effect: Optional[str] = None
    victim_count: Optional[int] = 0
    victim_death: Optional[int] = 0
    drone_count: Optional[int] = 0
    incident_initiator_id: Optional[int] = None

class MilitarySituationCreate(MilitarySituationBase):
    pass

class MilitarySituation(MilitarySituationBase):
    id: int
    
    class Config:
        from_attributes = True


# Схемы для OMVD (для ручного ввода)
class OMVDBase(BaseModel):
    omvd_name: str

class OMVD(OMVDBase):
    id: int
    
    class Config:
        from_attributes = True


# Схемы для CrimeCategory (для ручного ввода)
class CrimeCategoryBase(BaseModel):
    crime_name: str

class CrimeCategory(CrimeCategoryBase):
    id: int
    
    class Config:
        from_attributes = True


# Схемы для IncidentInitiator
class IncidentInitiatorBase(BaseModel):
    initiator_name: str

class IncidentInitiator(IncidentInitiatorBase):
    id: int
    
    class Config:
        from_attributes = True