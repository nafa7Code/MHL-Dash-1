# المرحلة الأولى: بناء المتطلبات
FROM python:3.11-slim AS builder

# تثبيت المتطلبات الأساسية
RUN apt-get update && apt-get install -y build-essential libpq-dev curl

# إعداد مجلد العمل
WORKDIR /app

# نسخ ملف المتطلبات وتثبيت الحزم في مجلد مؤقت
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --user -r requirements.txt

# المرحلة الثانية: إعداد التشغيل
FROM python:3.11-slim

# إنشاء المستخدم
RUN useradd -m appuser

# تثبيت الأدوات المطلوبة
RUN apt-get update && apt-get install -y libpq-dev curl && apt-get clean

# مجلد العمل
WORKDIR /app

# نسخ الحزم المثبتة من المرحلة السابقة
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# نسخ الكود بالكامل
COPY . .

# إعداد المتغيرات الخاصة بـ Django
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# إنشاء مجلدات static/media
RUN mkdir -p /app/staticfiles /app/media

# تجميع ملفات static
RUN python manage.py collectstatic --noinput

# تعيين المستخدم غير الجذر
USER appuser

# أمر التشغيل باستخدام gunicorn
CMD ["gunicorn", "logistics_project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
