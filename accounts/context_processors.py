from accounts.models import Profile
from CashFlow.debug import debug_event

def user_permissions(request):
    context = {
        'user_is_viewer': False,
        'user_is_editor': False,
        'user_role': None,
    }
    
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            profile, _ = Profile.objects.get_or_create(user=request.user)
        
        profile_role = (profile.edit or "").strip()
        context['user_role'] = profile_role
        context['user_is_viewer'] = (profile_role == 'Viewer')
        context['user_is_editor'] = (profile_role == 'Editor')
        
        debug_event(
            "context_processor.permissions",
            user=request.user.username,
            role=profile.edit,
            is_viewer=context['user_is_viewer']
        )
        
    return context
