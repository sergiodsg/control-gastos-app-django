from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView as AuthLoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import LoginForm, RegistroForm


class LoginView(AuthLoginView):
    template_name = 'accounts/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        if self.request.user.is_superuser:
            return reverse_lazy('superadmin_dashboard')
        return super().get_success_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'hide_navbar': True, 'hide_sidebar': True})
        return context

    def get_default_redirect_url(self):
        if self.request.user.is_authenticated and self.request.user.is_superuser:
            return reverse_lazy('superadmin_dashboard')
        return super().get_default_redirect_url()


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
    return render(request, 'accounts/registro.html', {
        'form': form,
        'hide_navbar': True,
        'hide_sidebar': True
    })
