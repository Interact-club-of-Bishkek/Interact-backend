from django.shortcuts import render
from django.http import JsonResponse
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

# Шрифт кириллицы
FONT_PATH = os.path.join(settings.BASE_DIR, 'system-images', 'mavka-script.ttf')
pdfmetrics.registerFont(TTFont('MavkaScript', FONT_PATH))

def booking_page(request):
    bookings = Booking.objects.all()
    return render(request, 'teatre_opera.html', {'bookings': bookings})

def api_book(request):
    if request.method == "POST":
        data = json.loads(request.body)
        full_name = data.get('full_name')
        phone = data.get('phone')
        row = int(data.get('row'))
        seat = int(data.get('seat'))
        price = int(data.get('price', 1000))
        hall_type = data.get('hall_type', 'parter')

        if Booking.objects.filter(row=row, seat=seat, hall_type=hall_type).exists():
            return JsonResponse({'error': 'Место уже занято'}, status=400)

        booking = Booking.objects.create(
            full_name=full_name,
            phone=phone,
            row=row,
            seat=seat,
            price=price,
            hall_type=hall_type
        )

        # Генерация PDF
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A5)

        ticket_bg_path = os.path.join(settings.BASE_DIR, 'system-images', 'ticket_bg.png')
        if os.path.exists(ticket_bg_path):
            bg = ImageReader(ticket_bg_path)
            c.drawImage(bg, 0, 0, width=A5[0], height=A5[1])

        c.setFont("MavkaScript", 16)
        c.drawString(50, 250, f"ФИО: {full_name}")
        c.drawString(50, 230, f"Ряд: {row}")
        c.drawString(50, 210, f"Место: {seat}")
        c.drawString(50, 190, f"Ложа: {booking.get_hall_type_display()}")
        c.drawString(50, 170, f"Цена: {price} сом")

        c.showPage()
        c.save()
        buffer.seek(0)

        booking.ticket_pdf.save(f"ticket_{booking.id}.pdf", buffer, save=True)
        buffer.seek(0)

        return JsonResponse({'success': True, 'ticket_url': booking.ticket_pdf.url})

    return JsonResponse({'error': 'Метод не поддерживается'}, status=405)
