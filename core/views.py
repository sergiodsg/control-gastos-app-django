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
    
    # Pasamos banderas para ocultar navbar y sidebar
    return render(request, 'core/registro.html', {
        'form': form,
        'hide_navbar': True,
        'hide_sidebar': True
    })
