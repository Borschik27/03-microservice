import os
from flask import Flask, request, jsonify
from minio import Minio
from minio.error import S3Error
from PIL import Image
import io
import jwt
import requests
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)

# Настройки Minio
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', '127.0.0.1:9000')
MINIO_ROOT_USER = os.getenv('MINIO_ROOT_USER', 'minio')
MINIO_ROOT_PASSWORD = os.getenv('MINIO_ROOT_PASSWORD', 'minio123')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'images')

# Настройки для security
SECURITY_URL = os.getenv('SECURITY_URL', 'http://security:8082/v1/token/validation')  # URL для валидации токена

# Подключение к Minio
client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ROOT_USER,
    secret_key=MINIO_ROOT_PASSWORD,
    secure=False
)

# Создание бакета, если он не существует
if not client.bucket_exists(MINIO_BUCKET):
    client.make_bucket(MINIO_BUCKET)

# Настроим Prometheus метрики
metrics = PrometheusMetrics(app)

# Валидируем токен
def validate_token(token):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(SECURITY_URL, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('login')
    return None

@app.route('/v1/upload', methods=['POST'])
def upload_file():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "Missing token"}), 400

    # Валидируем токен
    token = token.split(" ")[1]  # Извлекаем сам токен
    login = validate_token(token)
    if not login:
        return jsonify({"error": "Invalid or expired token"}), 401

    # Проверяем, что файл был отправлен
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Сжимаем изображение
    img = Image.open(file.stream)
    img = img.convert("RGB")
    img = img.resize((img.width // 2, img.height // 2))
    
    # Сохраняем изображение в память
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    
    # Загрузка в Minio
    try:
        object_name = f'{login}/{file.filename}'  # Используем login пользователя для организации файлов в MinIO
        client.put_object(MINIO_BUCKET, object_name, img_byte_arr, len(img_byte_arr.getvalue()))
        return jsonify({"message": "File uploaded successfully"}), 200
    except S3Error as e:
        return jsonify({"error": f"Failed to upload file: {e}"}), 500

# Конфигурируем метрики для успешных и неудачных запросов
metrics.info('app_info', 'Application Info', version='1.0')

# Пример метрики для успешных загрузок
successful_uploads = metrics.counter('successful_uploads', 'Number of successful file uploads')

# Пример метрики для неудачных загрузок
failed_uploads = metrics.counter('failed_uploads', 'Number of failed file uploads')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)
