from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        ADVISOR = "ADVISOR", "Advisor"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT
    )

    email = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.username} ({self.role})"