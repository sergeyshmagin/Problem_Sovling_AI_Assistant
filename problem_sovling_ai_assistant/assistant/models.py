from django.db import models

class ProblemCard(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    who = models.CharField(max_length=255, blank=True)
    what = models.TextField(blank=True)
    where = models.CharField(max_length=255, blank=True)
    when = models.CharField(max_length=255, blank=True)
    why_now = models.TextField(blank=True)

    r1_as_is = models.TextField(blank=True)
    r2_to_be = models.TextField(blank=True)
    gap = models.TextField(blank=True)

    analysis = models.TextField(blank=True)
    key_question = models.TextField(blank=True)

    problem_type = models.CharField(
        max_length=50,
        choices=[('challenge', 'Вызов'), ('failure', 'Сбой')],
        blank=True
    )

    key_question = models.TextField(blank=True)

    def __str__(self):
        return f"ProblemCard #{self.pk}"
