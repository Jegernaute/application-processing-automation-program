"""
URL configuration for repair_requests project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core.views import RegisterAPIView, RequestCreateView, RequestListView, RequestUpdateView
from core.views import VerifyCodeView
from core.views import LoginUserView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/verify-code/', VerifyCodeView.as_view(), name='verify-code'),
    path('api/register/', RegisterAPIView.as_view(), name='register'),
    path('api/login/', LoginUserView.as_view(), name='login'),
    path('api/requests/', RequestCreateView.as_view(), name='request-create'),
    path('api/requests/list/', RequestListView.as_view(), name='request-list'),
    path('api/requests/<int:pk>/', RequestUpdateView.as_view(), name='request-update'),


]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)