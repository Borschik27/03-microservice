FROM python:3.8-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы в контейнер
COPY . /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Открываем порт для сервиса
EXPOSE 8082

# Указываем команду для запуска приложения
CMD ["python", "app.py"]
