def superadmin_panel(request):
    resolver = getattr(request, 'resolver_match', None)
    url_name = resolver.url_name if resolver else ''
    is_panel = bool(url_name and url_name.startswith('superadmin'))
    return {'is_superadmin_panel': is_panel}
