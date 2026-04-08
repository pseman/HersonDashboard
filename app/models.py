from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Time, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class OMVD(Base):
    __tablename__ = "omvd"
    
    id = Column(Integer, primary_key=True, index=True)
    omvd_name = Column(String, nullable=False)
    
    # Связь с CriminalSituation (если нужна)
    # criminal_situations = relationship("CriminalSituation", back_populates="omvd")


class CrimeCategory(Base):
    __tablename__ = "crime_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    crime_name = Column(String, nullable=False)
    
    # Связь с CriminalSituation (если нужна)
    # criminal_situations = relationship("CriminalSituation", back_populates="crime_category")


class CriminalSituation(Base):
    __tablename__ = "criminal_situations"
    
    id = Column(Integer, primary_key=True, index=True)
    omvd_name = Column(String, nullable=False)  # текстовое поле
    crime_date = Column(Date, nullable=False)
    registration_place = Column(String)
    registration_number = Column(Integer)
    registration_date = Column(Date)
    crime_article = Column(String)
    fraud_type = Column(String)
    victim_gender = Column(Integer)  # 1 - мужской, 2 - женский
    victim_birthday = Column(Date)
    crime_category_name = Column(String, nullable=False)  # текстовое поле
    sum_damage = Column(Float)
    
    # Связи остаются
    # omvd = relationship("OMVD", back_populates="criminal_situations")
    # crime_category = relationship("CrimeCategory", back_populates="criminal_situations")



class IncidentInitiator(Base):
    __tablename__ = "incident_initiators"
    
    id = Column(Integer, primary_key=True, index=True)
    initiator_name = Column(String, nullable=False)
    
    military_situations = relationship("MilitarySituation", back_populates="incident_initiator")


class MilitarySituation(Base):
    __tablename__ = "military_situations"
    
    id = Column(Integer, primary_key=True, index=True)
    incident_date = Column(Date, nullable=False)
    incident_time = Column(Time)
    incident_name = Column(String)
    employe_action = Column(String)
    time_cancel_incident = Column(Time)
    incident_effect = Column(String)
    victim_count = Column(Integer, default=0)
    victim_death = Column(Integer, default=0)
    drone_count = Column(Integer, default=0)
    initiator_name = Column(String, nullable=True)  # ДОБАВИТЬ ЭТУ СТРОКУ
    incident_initiator_id = Column(Integer, ForeignKey("incident_initiators.id"))
    
    incident_initiator = relationship("IncidentInitiator", back_populates="military_situations")