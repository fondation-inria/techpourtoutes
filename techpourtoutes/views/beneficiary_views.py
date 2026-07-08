from django.shortcuts import render


def beneficiary_home(request):
    return render(request, "coalition/beneficiary_home.html", {})
