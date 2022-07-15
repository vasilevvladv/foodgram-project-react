import io
from pathlib import Path

from django.db.models import Sum
from recipes.models import RecipeIngredientAmount
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONTS_DIR = Path('./fonts/TimesNewRoman.ttf').resolve()


def create_pdf_shopping_cart(user):
    """ Создает pdf-файл."""

    buffer = io.BytesIO()
    pdf_page = canvas.Canvas(buffer, pagesize=A4)
    pdfmetrics.registerFont(TTFont('TimesNewRoman', FONTS_DIR))
    pdf_page.setFont('TimesNewRoman', 14)
    x, y = 50, 690
    purchases = RecipeIngredientAmount.objects.filter(
        recipe__shopping_cart__user=user
    ).values('ingredient__name', 'ingredient__measurement_unit').annotate(
        total_amount=Sum('amount')
    )
    if purchases:
        pdf_page.drawCentredString(300, 750, 'Список продуктов')
        for content in purchases:
            name = content['ingredient__name'].capitalize()
            amount = content['total_amount']
            measure = content['ingredient__measurement_unit']
            row = f'{name} - {amount} ({measure});'
            pdf_page.drawString(
                x, y, row
            )
            y -= 30
        pdf_page.save()
        buffer.seek(0)
        return buffer
    else:
        pdf_page.drawCentredString(315, 425,  'Список покупок пуст')
        pdf_page.showPage()
        pdf_page.save()
        buffer.seek(0)
        return buffer
