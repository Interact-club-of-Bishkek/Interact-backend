import os
import shutil

# Путь к текущей папке
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("🧹 Начинаем полную очистку проекта...")

# 1. Удаляем базу данных
db_path = os.path.join(BASE_DIR, "db.sqlite3")
if os.path.exists(db_path):
    os.remove(db_path)
    print("✅ База данных db.sqlite3 удалена.")
else:
    print("ℹ️ База данных не найдена (уже удалена).")

# 2. Проходим по всем папкам
for root, dirs, files in os.walk(BASE_DIR):
    # Игнорируем виртуальное окружение, чтобы не сломать библиотеки
    if "venv" in root or "env" in root or ".git" in root:
        continue

    # А. Удаляем папки __pycache__
    for dir_name in dirs:
        if dir_name == "__pycache__":
            dir_path = os.path.join(root, dir_name)
            shutil.rmtree(dir_path)
            print(f"🗑 Удален кэш: {dir_path}")

    # Б. Очищаем папки migrations
    if "migrations" in root:
        for file in files:
            if file != "__init__.py":
                file_path = os.path.join(root, file)
                os.remove(file_path)
                print(f"❌ Удалена миграция: {file_path}")

print("\n✨ Очистка завершена! Теперь система чиста.")
print("👉 Теперь выполните: python manage.py makemigrations")
print("👉 Затем: python manage.py migrate")