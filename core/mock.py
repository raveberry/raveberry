from django.http import HttpResponse

def index(request):
    return HttpResponse('You started the server with DJANGO_MOCK')
