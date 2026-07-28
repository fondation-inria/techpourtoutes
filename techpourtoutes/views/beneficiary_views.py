from datetime import date

from django.shortcuts import render


def beneficiary_home(request):
    return render(request, "beneficiary/beneficiary_home.html", {})


def _age(birth_date):
    today = date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age
