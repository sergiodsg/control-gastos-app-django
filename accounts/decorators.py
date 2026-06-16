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
                
            role = (profile.edit or "").strip()
            if role == 'Viewer':
                messages.error(request, "Su cuenta es de solo lectura. No puede realizar esta acción.")
                return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
        return view_func(request, *args, **kwargs)
    return _wrapped_view
