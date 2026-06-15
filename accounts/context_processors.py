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
            profile = Profile.objects.create(user=request.user)
        
        context['user_role'] = profile.edit
        context['user_is_viewer'] = (profile.edit.strip() == 'Viewer')
        context['user_is_editor'] = (profile.edit.strip() == 'Editor')
        
        debug_event(
            "context_processor.permissions",
            user=request.user.username,
            role=profile.edit,
            is_viewer=context['user_is_viewer']
        )
        
    return context
