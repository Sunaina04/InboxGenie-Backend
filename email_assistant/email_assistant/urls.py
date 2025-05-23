"""
URL configuration for email_assistant project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from ai_email.views import (
    get_emails, 
    sent_emails_view, 
    generate_email_reply, 
    send_ai_email, 
    auto_reply_emails,
    delete_email_view,
    google_login,
    upload_manual,
    list_manuals,
    delete_manual,
    rename_manual,
    retry_embedding
)
urlpatterns = [
    path("admin/", admin.site.urls),
    path("emails/", get_emails, name="get_emails"),
    path("sent-mails/", sent_emails_view, name="sent_emails"),
    path("generate-reply/", generate_email_reply, name="generate_reply"),
    path("send-email/", send_ai_email, name="send_email"),
    path("auto-reply-emails/", auto_reply_emails, name="auto_reply"),
    path('delete-email/<str:message_id>/', delete_email_view, name='delete_email'),
    path('auth/google-login/', google_login, name='google_login'),
    path('api/manuals/', upload_manual, name='upload-manual'),
    path('api/list-manuals/', list_manuals, name='list_manuals'),
    path('api/delete-manual/<int:manual_id>/', delete_manual, name='delete_manual'),
    path('api/rename-manual/<int:manual_id>/', rename_manual, name='rename_manual'),
    path('api/manuals/<int:manual_id>/retry-embedding/', retry_embedding, name='retry-embedding')

]
# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)