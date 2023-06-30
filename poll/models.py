from django.db import models

class settings(models.Model):
    days = models.IntegerField(null=False)
    max_back_question = models.IntegerField(null=False)
