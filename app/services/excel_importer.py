import pandas as pd
from io import BytesIO
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import CriminalSituation, MilitarySituation

class ExcelImporter:
    def __init__(self, db: Session):
        self.db = db

    def import_criminal_situations(self, file_content: bytes) -> dict:
        """Импорт криминальных ситуаций из Excel - только текстовые поля"""
        try:
            df = pd.read_excel(BytesIO(file_content))
            
            print(f"📊 Всего строк в файле: {len(df)}")
            print(f"📋 Колонки: {list(df.columns)}")
            
            success_count = 0
            error_rows = []
            crimes_to_add = []
            
            for index, row in df.iterrows():
                try:
                    if row.isnull().all():
                        continue
                    
                    omvd_name = str(row['omvd_name']).strip() if pd.notna(row['omvd_name']) else None
                    if not omvd_name:
                        error_rows.append(f"Строка {index + 2}: Пустое поле omvd_name")
                        continue
                    
                    crime_category_name = str(row['crime_category_name']).strip() if pd.notna(row['crime_category_name']) else None
                    if not crime_category_name:
                        error_rows.append(f"Строка {index + 2}: Пустое поле crime_category_name")
                        continue
                    
                    # Обработка даты
                    crime_date = None
                    if pd.notna(row['crime_date']):
                        try:
                            date_str = str(row['crime_date']).strip()
                            if ' ' in date_str:
                                date_str = date_str.split(' ')[0]
                            if '.' in date_str:
                                crime_date = datetime.strptime(date_str, '%d.%m.%Y').date()
                            elif '-' in date_str:
                                crime_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        except:
                            error_rows.append(f"Строка {index + 2}: Ошибка даты crime_date")
                            continue
                    
                    registration_date = None
                    if pd.notna(row['registration_date']):
                        try:
                            date_str = str(row['registration_date']).strip()
                            if ' ' in date_str:
                                date_str = date_str.split(' ')[0]
                            if '.' in date_str:
                                registration_date = datetime.strptime(date_str, '%d.%m.%Y').date()
                        except:
                            pass
                    
                    victim_birthday = None
                    if pd.notna(row['victim_birthday']):
                        try:
                            date_str = str(row['victim_birthday']).strip()
                            if ' ' in date_str:
                                date_str = date_str.split(' ')[0]
                            if '.' in date_str:
                                victim_birthday = datetime.strptime(date_str, '%d.%m.%Y').date()
                        except:
                            pass
                    
                    registration_number = int(row['registration_number']) if pd.notna(row['registration_number']) else None
                    victim_gender = int(row['victim_gender']) if pd.notna(row['victim_gender']) else None
                    sum_damage = float(row['sum_damage']) if pd.notna(row['sum_damage']) else None
                    
                    crime = CriminalSituation(
                        omvd_name=omvd_name,
                        crime_date=crime_date,
                        registration_place=str(row['registration_place']) if pd.notna(row['registration_place']) else None,
                        registration_number=registration_number,
                        registration_date=registration_date,
                        crime_article=str(row['crime_article']) if pd.notna(row['crime_article']) else None,
                        fraud_type=str(row['fraud_type']) if pd.notna(row['fraud_type']) else None,
                        victim_gender=victim_gender,
                        victim_birthday=victim_birthday,
                        crime_category_name=crime_category_name,
                        sum_damage=sum_damage
                    )
                    crimes_to_add.append(crime)
                    success_count += 1
                    
                except Exception as e:
                    error_rows.append(f"Строка {index + 2}: {str(e)}")
            
            if crimes_to_add:
                self.db.bulk_save_objects(crimes_to_add)
                self.db.commit()
            
            return {
                'success': True,
                'imported': success_count,
                'errors': error_rows
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def import_military_situations(self, file_content: bytes) -> dict:
        """Импорт военных инцидентов из Excel"""
        try:
            df = pd.read_excel(BytesIO(file_content))
            
            print(f"📊 Всего строк в файле: {len(df)}")
            print(f"📋 Колонки: {list(df.columns)}")
            
            success_count = 0
            error_rows = []
            incidents_to_add = []
            
            for index, row in df.iterrows():
                try:
                    if row.isnull().all():
                        continue
                    
                    # Функция для преобразования даты
                    def parse_date(date_str):
                        if pd.isna(date_str) or not date_str:
                            return None
                        try:
                            date_str = str(date_str).strip()
                            if ' ' in date_str:
                                date_str = date_str.split(' ')[0]
                            if '.' in date_str:
                                return datetime.strptime(date_str, '%d.%m.%Y').date()
                            elif '-' in date_str:
                                return datetime.strptime(date_str, '%Y-%m-%d').date()
                            else:
                                return pd.to_datetime(date_str).date()
                        except:
                            return None
                    
                    # Функция для преобразования времени
                    def parse_time(time_str):
                        if pd.isna(time_str) or not time_str:
                            return None
                        try:
                            time_str = str(time_str).strip()
                            if ':' in time_str:
                                return datetime.strptime(time_str, '%H:%M:%S').time()
                            else:
                                return pd.to_datetime(time_str).time()
                        except:
                            return None
                    
                    incident_date = parse_date(row['incident_date']) if 'incident_date' in df.columns else None
                    incident_time = parse_time(row['incident_time']) if 'incident_time' in df.columns else None
                    time_cancel = parse_time(row['time_cancel_incident']) if 'time_cancel_incident' in df.columns else None
                    
                    if not incident_date:
                        error_rows.append(f"Строка {index + 2}: Некорректная дата incident_date")
                        continue
                    
                    victim_count = int(row['victim_count']) if 'victim_count' in df.columns and pd.notna(row['victim_count']) else 0
                    victim_death = int(row['victim_death']) if 'victim_death' in df.columns and pd.notna(row['victim_death']) else 0
                    drone_count = int(row['drone_count']) if 'drone_count' in df.columns and pd.notna(row['drone_count']) else 0
                    
                    incident_name = str(row['incident_name']).strip() if 'incident_name' in df.columns and pd.notna(row['incident_name']) else None
                    employe_action = str(row['employe_action']).strip() if 'employe_action' in df.columns and pd.notna(row['employe_action']) else None
                    incident_effect = str(row['incident_effect']).strip() if 'incident_effect' in df.columns and pd.notna(row['incident_effect']) else None
                    initiator_name = str(row['initiator_name']).strip() if 'initiator_name' in df.columns and pd.notna(row['initiator_name']) else None
                    
                    incident = MilitarySituation(
                        incident_date=incident_date,
                        incident_time=incident_time,
                        incident_name=incident_name,
                        employe_action=employe_action,
                        time_cancel_incident=time_cancel,
                        incident_effect=incident_effect,
                        victim_count=victim_count,
                        victim_death=victim_death,
                        drone_count=drone_count,
                        initiator_name=initiator_name
                    )
                    incidents_to_add.append(incident)
                    success_count += 1
                    
                except Exception as e:
                    error_rows.append(f"Строка {index + 2}: {str(e)}")
            
            if incidents_to_add:
                self.db.bulk_save_objects(incidents_to_add)
                self.db.commit()
            
            return {
                'success': True,
                'imported': success_count,
                'errors': error_rows
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def download_template_criminal(self):
        """Скачать шаблон Excel для криминальных ситуаций"""
        df = pd.DataFrame({
            'omvd_name': ['ГУ МВД по Херсонской области', 'ОМВД России «Генический»'],
            'crime_date': ['2024-01-15', '2024-01-20'],
            'registration_place': ['г. Херсон', 'г. Геническ'],
            'registration_number': [1001, 1002],
            'registration_date': ['2024-01-16', '2024-01-21'],
            'crime_article': ['ст. 159', 'ст. 158'],
            'fraud_type': ['Звонок', 'Сайт'],
            'victim_gender': [1, 2],
            'victim_birthday': ['1980-05-15', '1990-10-20'],
            'crime_category_name': ['Мошенничество при покупке/услуге', 'Кража с карты/счёта'],
            'sum_damage': [50000, 30000]
        })
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='CriminalSituations', index=False)
        return output.getvalue()

    def download_template_military(self):
        """Скачать шаблон Excel для военных инцидентов"""
        df = pd.DataFrame({
            'incident_date': ['2024-01-15', '2024-01-20'],
            'incident_time': ['10:30:00', '14:45:00'],
            'incident_name': ['Обстрел', 'Дрон'],
            'employe_action': ['Эвакуация', 'Разведка'],
            'time_cancel_incident': ['12:00:00', '16:00:00'],
            'incident_effect': ['Разрушения', 'Нет'],
            'victim_count': [2, 0],
            'victim_death': [1, 0],
            'drone_count': [0, 3],
            'initiator_name': ['ЦУКС МЧС Херсонской области (Среда)', '']
        })
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='MilitarySituations', index=False)
        return output.getvalue()