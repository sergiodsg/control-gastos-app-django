def clear_org_session(request):
    request.session.pop('org_id', None)
    request.session.pop('org_name', None)
