from .models import PortalLink

def portal_links_processor(request):
    return {
        'nav_portal_links': PortalLink.objects.all().order_by('id')
    }
