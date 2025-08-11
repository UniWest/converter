from django.http import HttpResponse, JsonResponse

def home(request):
    return HttpResponse('<h1>Converter App Running!</h1>')

def health(request):
    return JsonResponse({'status': 'ok'})
