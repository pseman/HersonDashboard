from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.models import CriminalSituation, MilitarySituation, OMVD, CrimeCategory
from datetime import datetime, timedelta

def get_crime_trends(db: Session, days: int = 30):
    """Динамика преступлений за последние N дней"""
    start_date = datetime.now().date() - timedelta(days=days)
    
    trends = db.query(
        func.date(CriminalSituation.crime_date).label("date"),
        func.count(CriminalSituation.id).label("count")
    ).filter(CriminalSituation.crime_date >= start_date).group_by(
        func.date(CriminalSituation.crime_date)
    ).order_by("date").all()
    
    return {
        "dates": [t[0] for t in trends],
        "counts": [t[1] for t in trends]
    }

def get_damage_by_omvd(db: Session):
    """Ущерб по территориальным подразделениям"""
    damage = db.query(
        OMVD.omvd_name,
        func.sum(CriminalSituation.sum_damage).label("total_damage")
    ).join(CriminalSituation).group_by(OMVD.omvd_name).order_by(
        func.sum(CriminalSituation.sum_damage).desc()
    ).all()
    
    return [{"omvd": d[0], "damage": float(d[1] or 0)} for d in damage]

def get_monthly_stats(db: Session):
    """Месячная статистика преступлений"""
    current_year = datetime.now().year
    
    monthly = db.query(
        extract('month', CriminalSituation.crime_date).label("month"),
        func.count(CriminalSituation.id).label("count")
    ).filter(extract('year', CriminalSituation.crime_date) == current_year).group_by(
        extract('month', CriminalSituation.crime_date)
    ).all()
    
    return [{"month": int(m[0]), "count": m[1]} for m in monthly]