from .models import SiteSettings

def site_settings(request):
    """
    Add site settings to all template contexts
    """
    try:
        settings = SiteSettings.objects.first()
        return {'site_settings': settings}
    except SiteSettings.DoesNotExist:
        return {'site_settings': None}
