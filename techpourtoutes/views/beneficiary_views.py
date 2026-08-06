from django.shortcuts import render


def beneficiary_home(request):
    return render(request, "beneficiary/beneficiary_home.html", {})
