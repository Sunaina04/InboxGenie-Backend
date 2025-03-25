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
from django.urls import path
from ai_email.views import get_emails, generate_email_reply, send_ai_email, sent_emails_view, auto_reply_inquiry_emails


urlpatterns = [
    path('admin/', admin.site.urls),
    path("emails/", get_emails, name="get_emails"),
    path("sent_mails/", sent_emails_view, name="sent_emails"),
    path("generate-reply/", generate_email_reply, name="generate_email_reply"),
    path("send_ai_email/", send_ai_email, name="send_ai_email"),
    path("auto-reply-inquiries/", auto_reply_inquiry_emails, name="auto_reply_inquiry_emails"),
]
