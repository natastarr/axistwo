from flask import Flask, request, render_template
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

app = Flask(__name__)

# Настройки для отправки email
SMTP_SERVER = 'smtp.gmail.com'  # Замените на ваш SMTP-сервер
SMTP_PORT = 587  # Порт SMTP-сервера
SMTP_USERNAME = 'your_email@gmail.com'  # Замените на ваш email
SMTP_PASSWORD = 'your_password'  # Замените на ваш пароль или app password

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        # Получаем данные из формы
        patient_last_name = request.form.get('patientLastName', '')
        patient_first_name = request.form.get('patientFirstName', '')
        patient_middle_name = request.form.get('patientMiddleName', '')
        doctor_email = request.form.get('doctorEmail', '')
        
        # Формируем полное имя пациента
        patient_full_name = f"{patient_last_name} {patient_first_name}"
        if patient_middle_name:
            patient_full_name += f" {patient_middle_name}"
        
        # Создаем отчет
        report_content = generate_report(request.form, patient_full_name)
        
        # Имя файла отчета
        report_filename = f"{patient_last_name}_{patient_first_name}_DC_TMD_report.txt"
        
        # Сохраняем отчет в файл
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # Отправляем отчет на email врача
        send_email(doctor_email, f"Отчет DC/TMD для пациента {patient_full_name}", 
                   f"Во вложении находится отчет DC/TMD для пациента {patient_full_name}.", 
                   report_filename)
        
        # Удаляем файл отчета после отправки
        if os.path.exists(report_filename):
            os.remove(report_filename)
        
        return 'success'
    except Exception as e:
        print(f"Ошибка: {str(e)}")
        return 'error', 500

def generate_report(form_data, patient_name):
    """Генерирует содержимое отчета на основе данных формы"""
    
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    report = f"ОТЧЕТ DC/TMD: Ось II\n"
    report += f"Дата и время: {now}\n"
    report += f"Пациент: {patient_name}\n"
    report += "="*50 + "\n\n"
    
    # 1. Рисунок боли
    report += "1. РИСУНОК БОЛИ\n"
    report += f"Количество болевых зон: {form_data.get('painZones', '0')}\n\n"
    
    # 2. Шкала хронической боли (GCPS версия 2.0)
    report += "2. ШКАЛА ХРОНИЧЕСКОЙ БОЛИ (GCPS версия 2.0)\n"
    report += f"Дней с болью за последние 6 месяцев: {form_data.get('painDays', 'Не указано')}\n"
    report += f"Интенсивность боли прямо сейчас (0-10): {form_data.get('currentPain', 'Не указано')}\n"
    report += f"Самая сильная боль за последние 30 дней (0-10): {form_data.get('worstPain', 'Не указано')}\n"
    report += f"Средняя интенсивность боли за последние 30 дней (0-10): {form_data.get('averagePain', 'Не указано')}\n"
    report += f"Дней с ограничением обычной деятельности: {form_data.get('disabilityDays', 'Не указано')}\n"
    report += f"Влияние на повседневную деятельность (0-10): {form_data.get('dailyInterference', 'Не указано')}\n"
    report += f"Влияние на социальную активность (0-10): {form_data.get('socialInterference', 'Не указано')}\n"
    report += f"Влияние на работоспособность (0-10): {form_data.get('workInterference', 'Не указано')}\n\n"
    
    # Расчет характеристики интенсивности боли (CPI)
    try:
        current_pain = int(form_data.get('currentPain', 0))
        worst_pain = int(form_data.get('worstPain', 0))
        average_pain = int(form_data.get('averagePain', 0))
        cpi = round(((current_pain + worst_pain + average_pain) / 3) * 10)
        report += f"Характеристика интенсивности боли (CPI): {cpi}/100\n"
    except (ValueError, TypeError):
        report += "Характеристика интенсивности боли (CPI): Не удалось рассчитать\n"
    
    # Расчет баллов за дни нетрудоспособности
    try:
        disability_days = int(form_data.get('disabilityDays', 0))
        disability_days_points = 0
        if disability_days >= 0 and disability_days <= 1:
            disability_days_points = 0
        elif disability_days == 2:
            disability_days_points = 1
        elif disability_days >= 3 and disability_days <= 5:
            disability_days_points = 2
        elif disability_days >= 6:
            disability_days_points = 3
        report += f"Баллы за дни нетрудоспособности: {disability_days_points}/3\n"
    except (ValueError, TypeError):
        report += "Баллы за дни нетрудоспособности: Не удалось рассчитать\n"
    
    # Расчет баллов за интерференцию
    try:
        daily_interference = int(form_data.get('dailyInterference', 0))
        social_interference = int(form_data.get('socialInterference', 0))
        work_interference = int(form_data.get('workInterference', 0))
        
        interference_score = round(((daily_interference + social_interference + work_interference) / 3) * 10)
        interference_points = 0
        
        if interference_score >= 0 and interference_score <= 29:
            interference_points = 0
        elif interference_score >= 30 and interference_score <= 49:
            interference_points = 1
        elif interference_score >= 50 and interference_score <= 69:
            interference_points = 2
        elif interference_score >= 70:
            interference_points = 3
        
        report += f"Баллы за интерференцию: {interference_points}/3\n"
        
        # Общий балл нетрудоспособности
        total_disability_points = disability_days_points + interference_points
        report += f"Общий балл нетрудоспособности: {total_disability_points}/6\n"
        
        # Степень хронической боли
        chronic_pain_grade = ""
        if cpi == 0:
            chronic_pain_grade = "0 - Нет боли"
        elif cpi < 50 and total_disability_points < 3:
            chronic_pain_grade = "I - Боль низкой интенсивности, без инвалидности"
        elif cpi >= 50 and total_disability_points < 3:
            chronic_pain_grade = "II - Боль высокой интенсивности, без инвалидности"
        elif total_disability_points >= 3 and total_disability_points <= 4:
            chronic_pain_grade = "III - Умеренно ограничивающая боль"
        elif total_disability_points >= 5:
            chronic_pain_grade = "IV - Строго ограничивающая боль"
        
        report += f"Степень хронической боли: {chronic_pain_grade}\n\n"
    except (ValueError, TypeError):
        report += "Баллы за интерференцию: Не удалось рассчитать\n"
        report += "Общий балл нетрудоспособности: Не удалось рассчитать\n"
        report += "Степень хронической боли: Не удалось рассчитать\n\n"
    
    # 3. Шкала ограничения функции нижней челюсти-8 (JFLS-8)
    report += "3. ШКАЛА ОГРАНИЧЕНИЯ ФУНКЦИИ НИЖНЕЙ ЧЕЛЮСТИ-8 (JFLS-8)\n"
    jfls_values = []
    jfls_missing_count = 0
    
    for i in range(1, 9):
        value = form_data.get(f'jfls{i}', None)
        if value:
            jfls_values.append(int(value))
            report += f"Пункт {i}: {value}\n"
        else:
            jfls_missing_count += 1
            report += f"Пункт {i}: Не указано\n"
    
    if jfls_missing_count <= 2 and jfls_values:
        jfls_sum = sum(jfls_values)
        jfls_score = round((jfls_sum / (8 - jfls_missing_count)) * 10) / 10
        report += f"Общий балл JFLS-8: {jfls_score}/10\n\n"
    else:
        report += "Общий балл JFLS-8: Невозможно рассчитать (пропущено более 2 элементов)\n\n"
    
    # 4. Анкета здоровья пациента (PHQ-4)
    report += "4. АНКЕТА ЗДОРОВЬЯ ПАЦИЕНТА (PHQ-4)\n"
    phq4_values = []
    phq4_missing_count = 0
    
    for i in range(1, 5):
        value = form_data.get(f'phq4_{i}', None)
        if value:
            phq4_values.append(int(value))
            report += f"Пункт {i}: {value}\n"
        else:
            phq4_missing_count += 1
            report += f"Пункт {i}: Не указано\n"
    
    report += f"Сложность выполнения работы: {form_data.get('phq4_difficulty', 'Не указано')}\n"
    
    if phq4_missing_count <= 1 and phq4_values:
        phq4_sum = sum(phq4_values)
        if phq4_missing_count == 1:
            phq4_score = round((phq4_sum * 4) / (4 - phq4_missing_count))
        else:
            phq4_score = phq4_sum
        
        report += f"Общий балл PHQ-4: {phq4_score}/12\n"
        
        phq4_interpretation = ""
        if phq4_score >= 0 and phq4_score <= 3:
            phq4_interpretation = "Нет дистресса"
        elif phq4_score >= 4 and phq4_score <= 5:
            phq4_interpretation = "Легкий дистресс"
        elif phq4_score >= 6 and phq4_score <= 8:
            phq4_interpretation = "Умеренный дистресс"
        else:
            phq4_interpretation = "Сильный дистресс"
        
        report += f"Интерпретация: {phq4_interpretation}\n\n"
    else:
        report += "Общий балл PHQ-4: Невозможно рассчитать (пропущено более 1 элемента)\n\n"
    
    # 5. ГАД-7 (Генерализованное тревожное расстройство)
    report += "5. ГАД-7 (ГЕНЕРАЛИЗОВАННОЕ ТРЕВОЖНОЕ РАССТРОЙСТВО)\n"
    gad7_values = []
    gad7_missing_count = 0
    
    for i in range(1, 8):
        value = form_data.get(f'gad7_{i}', None)
        if value:
            gad7_values.append(int(value))
            report += f"Пункт {i}: {value}\n"
        else:
            gad7_missing_count += 1
            report += f"Пункт {i}: Не указано\n"
    
    report += f"Сложность выполнения работы: {form_data.get('gad7_difficulty', 'Не указано')}\n"
    
    if gad7_missing_count <= 2 and gad7_values:
        gad7_sum = sum(gad7_values)
        if gad7_missing_count > 0:
            gad7_score = round((gad7_sum * 7) / (7 - gad7_missing_count))
        else:
            gad7_score = gad7_sum
        
        report += f"Общий балл ГАД-7: {gad7_score}/21\n"
        
        gad7_interpretation = ""
        if gad7_score >= 0 and gad7_score <= 5:
            gad7_interpretation = "Нет тревоги"
        elif gad7_score >= 6 and gad7_score <= 10:
            gad7_interpretation = "Легкая тревожность"
        elif gad7_score >= 11 and gad7_score <= 15:
            gad7_interpretation = "Умеренная тревожность"
        else:
            gad7_interpretation = "Сильная тревога"
        
        report += f"Интерпретация: {gad7_interpretation}\n\n"
    else:
        report += "Общий балл ГАД-7: Невозможно рассчитать (пропущено более 2 элементов)\n\n"
    
    return report

def send_email(to_email, subject, body, attachment_path):
    """Отправляет email с вложением"""
    
    # Создаем объект сообщения
    msg = MIMEMultipart()
    msg['From'] = SMTP_USERNAME
    msg['To'] = to_email
    msg['Subject'] = subject
    
    # Добавляем текст сообщения
    msg.attach(MIMEText(body, 'plain'))
    
    # Добавляем вложение
    with open(attachment_path, 'rb') as f:
        attachment = MIMEApplication(f.read(), _subtype='txt')
        attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
        msg.attach(attachment)
    
    # Отправляем сообщение
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)

if __name__ == '__main__':
    # Создаем папку templates, если она не существует
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Копируем index.html в папку templates
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    with open(os.path.join('templates', 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    app.run(debug=True)
