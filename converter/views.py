from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from forms import VideoUploadForm

def home_view(request):
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            return HttpResponse('<h1>Conversion Started!</h1><p>Your video is being processed...</p>')
    else:
        form = VideoUploadForm()
    
    return render(request, 'converter/home.html', {'form': form})

def convert_video_view(request):
    return render(request, 'converter/index.html', {'form': VideoUploadForm()})

def converter_status_view(request):
    return JsonResponse({'status': 'operational', 'version': '1.0.0'})
