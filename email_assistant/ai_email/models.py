from django.db import models
from django.contrib.auth.models import User

class Manual(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='manuals')
  file = models.FileField(upload_to='manuals/')
  filename = models.CharField(max_length=255)
  uploaded_at = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return f"{self.filename} uploaded by {self.user.email}"