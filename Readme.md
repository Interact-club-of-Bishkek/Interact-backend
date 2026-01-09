# 🦋 Interact Club Backend

**Backend для системы волонтёров Interact Club of Bishkek** — платформа для подачи заявок, управления волонтёрами, выбора команд и проектов.

Проект написан на **Django + Django REST Framework** с архитектурой API, управляемой через ViewSets и класс‑based views.

---

## 🧠 О ПРОЕКТЕ

Interact Backend — серверная часть веб решения для клуба Interact:

* 📋 Подача заявок волонтёров
* 🚀 Админка для кураторов (управление заявками, создание волонтёров)
* 🧩 Отдельные команды с набором волонтёров
* 📊 Dashboard волонтёров с фильтрами и модалками

---

## 🛠 Технологии

* **Backend:** Python, Django
* **API:** Django REST Framework
* **База данных:** PostgreSQL
* **Deployment:** Docker / docker-compose

---

## 📦 Структура проекта

```text
.
├── manage.py
├── Interact_backend/        # Настройки Django
├── volunteers/             # App: волонтёры, анкеты
├── directions/             # App: направления и команды
├── projects/               # App: проекты
├── templates/              # HTML шаблоны для страниц (Dashboard, команды и пр.)
├── static/                 # Статика для сайта
├── docker-compose.yml
└── ...
```

---

## 🚀 Установка и запуск (локально)

### 1) Клонировать репозиторий

```bash
git clone https://github.com/Interact-club-of-Bishkek/Interact-backend.git
cd Interact-backend
```

---

### 2) Создать `.env` файл (пример)

```dotenv
# ----------------------------------------------------
# --- НАСТРОЙКИ СЕКРЕТНЫХ КЛЮЧЕЙ И БОТА ---
# ----------------------------------------------------
SECRET_KEY=your_django_secret
BOT_TOKEN=your_telegram_bot_token

# ----------------------------------------------------
# --- НАСТРОЙКИ FINIK API ---
# ----------------------------------------------------
FINIK_ENV=beta
FINIK_API_KEY=
FINIK_ACCOUNT_ID=
FINIK_QR_NAME=
FINIK_REDIRECT_URL=backend
FINIK_WEBHOOK_URL=backend

# ----------------------------------------------------
# --- НАСТРОЙКИ POSTGRESQL (Для сервиса 'db') ---
# ----------------------------------------------------
POSTGRES_USER=interact_user
POSTGRES_PASSWORD=strong_password
POSTGRES_DB=interact_db

# ----------------------------------------------------
# --- НАСТРОЙКИ DJANGO (Для сервиса 'backend') ---
# ----------------------------------------------------
DB_HOST=db
DB_NAME=${POSTGRES_DB}
DB_USER=${POSTGRES_USER}
DB_PASSWORD=${POSTGRES_PASSWORD}
DB_PORT=5432

DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_API_BASE_URL=http://backend:8000/api/
```

---

### 3) Запуск через Docker

```bash
docker compose up -d --build
```

Контейнеры:

* `backend` — Django
* `db` — PostgreSQL

---

### 4) Миграции и сбор статики

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py collectstatic --noinput
```

---

###
