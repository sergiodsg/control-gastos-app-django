from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView as AuthLoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from CashFlow.debug import debug_event

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
        debug_event(
            "usuario.registro.intento",
            username=request.POST.get("username"),
            email=request.POST.get("email"),
        )
        if form.is_valid():
            user = form.save()
            debug_event(
                "usuario.creado",
                user_id=user.id,
                username=user.username,
                email=user.email,
                is_superuser=user.is_superuser,
            )
            login(request, user)
            messages.success(request, "Registro exitoso. ¡Bienvenido!")
            return redirect('dashboard')
        debug_event(
            "usuario.registro.error",
            username=request.POST.get("username"),
            errors=form.errors.get_json_data(),
        )
    else:
        form = RegistroForm()
    
    # Pasamos banderas para ocultar navbar y sidebar
    return render(request, 'accounts/registro.html', {
        'form': form,
        'hide_navbar': True,
        'hide_sidebar': True
    })
