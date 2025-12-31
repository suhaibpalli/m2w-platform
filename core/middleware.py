class CharsetMiddleware:
    """Ensure charset is set in HTTP headers"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add charset to Content-Type if not already present
        if 'text/html' in response.get('Content-Type', '') and 'charset' not in response.get('Content-Type', ''):
            response['Content-Type'] = 'text/html; charset=utf-8'
        
        return response
