from datetime import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    today = datetime.now()
    year = today.year
    return {"year": year}
