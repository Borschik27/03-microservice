import os
import jwt
import datetime
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)

# Секретный ключ для JWT
JWT_SECRET = os.getenv('JWT_SECRET', 'edb20f74ef10a2e010ae7f73fb18a6f7b5f2988c9cf2e14e06ec95ea8a7afedb')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')

# Настроим Prometheus метрики
metrics = PrometheusMetrics(app)

# Заготовка "базы данных" пользователей
users_db = {}

@app.route('/v1/user', methods=['POST'])
def register_user():
    data = request.get_json()
    if not data or 'login' not in data or 'password' not in data:
        return jsonify({"error": "Missing login or password"}), 400
    
    login = data['login']
    password = data['password']

    # Хэшируем пароль перед сохранением
    hashed_password = generate_password_hash(password)
    users_db[login] = {'password': hashed_password}

    return jsonify({"message": f"User {login} registered successfully"}), 201

@app.route('/v1/users', methods=['GET'])
def list_users():
    # Возвращаем список пользователей
    users = list(users_db.keys())  # Получаем только логины пользователей
    return jsonify({"users": users}), 200


@app.route('/v1/token', methods=['POST'])
def generate_token():
    data = request.get_json()
    if not data or 'login' not in data or 'password' not in data:
        return jsonify({"error": "Missing login or password"}), 400
    
    login = data['login']
    password = data['password']
    
    # Проверяем, существует ли пользователь
    if login not in users_db or not check_password_hash(users_db[login]['password'], password):
        return jsonify({"error": "Invalid credentials"}), 401
    
    # Создаём JWT токен
    token = jwt.encode({
        'login': login,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return jsonify({"token": token}), 200

@app.route('/v1/token/validation', methods=['GET'])
def validate_token():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "Missing token"}), 400

    try:
        token = token.split(" ")[1]  # Получаем сам токен из заголовка
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return jsonify({"valid": True, "login": payload['login']}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

# Конфигурируем метрики для успешных и неудачных запросов
metrics.info('app_info', 'Application Info', version='1.0')

# Пример метрики для успешных загрузок
successful_uploads = metrics.counter('successful_uploads', 'Number of successful file uploads')

# Пример метрики для неудачных загрузок
failed_uploads = metrics.counter('failed_uploads', 'Number of failed file uploads')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082)
