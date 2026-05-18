from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import RegistroForm
from django.contrib import messages

def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registro exitoso. ¡Bienvenido!")
            return redirect('dashboard')
    else:
        form = RegistroForm()
    return render(request, 'accounts/registro.html', {'form': form})
