from app.database import engine, SessionLocal
from app.models import Base, OMVD, CrimeCategory, IncidentInitiator
from datetime import date, time

def init_db():
    # Создаем таблицы
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Заполняем справочник OMVD
    omvd_data = [
        (1, "ГУ МВД по Херсонской области"),
        (2, "ОМВД России «Александровское»"),
        (3, "ОМВД России «Алешинское»"),
        (4, "ОМВД России «Безозерское»"),
        (5, "ОМВД России «Бериславское»"),
        (6, "ОМВД России «Великоалександровское»"),
        (7, "ОМВД России «Великолепитихское»"),
        (8, "ОМВД России «Верхнерогачинское»"),
        (9, "ОМВД России «Высокопольское»"),
        (10, "ОМВД России «Генический»"),
        (11, "ОМВД России «Голопристанское»"),
        (12, "ОМВД России «Горностаевское»"),
        (13, "ОМВД России «Ивановское»"),
        (14, "ОМВД России «Каланчакский»"),
        (15, "ОМВД России «Каховский»"),
        (16, "ОМВД России «Нижнесерогозское»"),
        (17, "ОМВД России «Нововоронцовское»"),
        (18, "ОМВД России «Новокаховский»"),
        (19, "ОМВД России «Новотроицкое»"),
        (20, "ОМВД России «Скадовский»"),
        (21, "ОМВД России «Снигиревское»"),
        (22, "ОМВД России «Чаплынское»"),
    ]
    
    for omvd_id, omvd_name in omvd_data:
        if not db.query(OMVD).filter(OMVD.id == omvd_id).first():
            db.add(OMVD(id=omvd_id, omvd_name=omvd_name))
    
    # Заполняем справочник CrimeCategory
    crime_data = [
        (1, "Кража с карты/счёта"),
        (2, "Мошенничество при покупке/услуге"),
        (3, "Мошенничество «безопасный счёт»"),
        (4, "Неправомерный доступ (ст. 272)"),
        (5, "Социальная инженерия (коды/мессенджеры)"),
        (6, "Прочие виды"),
    ]
    
    for crime_id, crime_name in crime_data:
        if not db.query(CrimeCategory).filter(CrimeCategory.id == crime_id).first():
            db.add(CrimeCategory(id=crime_id, crime_name=crime_name))
    
    # Заполняем справочник IncidentInitiator
    initiator_data = [
        (1, "ЦУКС МЧС Херсонской области (Среда)"),
    ]
    
    for init_id, init_name in initiator_data:
        if not db.query(IncidentInitiator).filter(IncidentInitiator.id == init_id).first():
            db.add(IncidentInitiator(id=init_id, initiator_name=init_name))
    
    db.commit()
    db.close()
    print("База данных инициализирована справочниками")

if __name__ == "__main__":
    init_db()