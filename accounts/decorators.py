from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from accounts.models import Profile

def viewer_restricted(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
            except Profile.DoesNotExist:
                profile, _ = Profile.objects.get_or_create(user=request.user)
                
            role = (profile.edit or "").strip().lower()
            if role == 'viewer' and not request.user.is_superuser:
                messages.error(
                    request,
                    "Su cuenta es de solo lectura (rol Viewer): no tiene permisos para crear, editar ni "
                    "eliminar registros. Si necesita realizar esta acción, solicite a un administrador "
                    "que cambie su rol a Editor."
                )
                return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
        return view_func(request, *args, **kwargs)
    return _wrapped_view
