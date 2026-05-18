from django.db import models
from django.contrib.auth.models import User

class Organization(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nombre de la organización")

    class Meta:
        verbose_name = "Organización"
        verbose_name_plural = "Organizaciones"

    def __str__(self):
        return self.name

class OrganizationAccess(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organization_accesses', verbose_name="Usuario")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='user_accesses', verbose_name="Organización")

    class Meta:
        verbose_name = "Acceso a organización"
        verbose_name_plural = "Accesos a organizaciones"
        unique_together = ('user', 'organization')

    def __str__(self):
        return f"{self.user.username} - {self.organization.name}"
