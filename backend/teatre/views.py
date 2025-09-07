from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from .models import Booking
import json
import os
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO

# Регистрация шрифта для кириллицы
FONT_PATH = os.path.join(settings.BASE_DIR, 'system-images', 'mavka-script.ttf')
pdfmetrics.registerFont(TTFont('MavkaScript', FONT_PATH))

def booking_page(request):
    bookings = Booking.objects.all()
    return render(request, 'teatre.html', {'bookings': bookings})

def api_book(request):
    if request.method == "POST":
        data = json.loads(request.body)
        full_name = data.get('full_name')
        phone = data.get('phone')
        row = int(data.get('row'))
        seat = int(data.get('seat'))
        price = int(data.get('price', 1000))

        if Booking.objects.filter(row=row, seat=seat).exists():
            return JsonResponse({'error': 'Место уже занято'}, status=400)

        booking = Booking.objects.create(
            full_name=full_name,
            phone=phone,
            row=row,
            seat=seat,
            price=price
        )

        # Генерация PDF в памяти
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A5)

        ticket_bg_path = os.path.join(settings.BASE_DIR, 'system-images', 'ticket_bg.png')
        if os.path.exists(ticket_bg_path):
            bg = ImageReader(ticket_bg_path)
            c.drawImage(bg, 0, 0, width=A5[0], height=A5[1])

        c.setFont("MavkaScript", 16)
        # c.drawString(50, 300, f"Адрес: ")
        c.drawString(50, 250, f"ФИО: {full_name}")
        c.drawString(50, 230, f"Ряд: {row}")
        c.drawString(50, 210, f"Место: {seat}")
        c.drawString(50, 190, f"Цена: {price} сом")

        c.showPage()
        c.save()
        buffer.seek(0)

        # Сохраняем PDF в поле модели (если нужно)
        booking.ticket_pdf.save(f"ticket_{booking.id}.pdf", buffer, save=True)
        buffer.seek(0)

        # Возвращаем URL для скачивания
        return JsonResponse({'success': True, 'ticket_url': booking.ticket_pdf.url})

    return JsonResponse({'error': 'Метод не поддерживается'}, status=405)
