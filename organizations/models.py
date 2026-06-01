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

class Account(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='accounts', verbose_name="Organización")
    name = models.CharField(max_length=255, verbose_name="Nombre de la cuenta", default="Cuenta Principal")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    class Meta:
        verbose_name = "Cuenta"
        verbose_name_plural = "Cuentas"

    def __str__(self):
        return f"{self.name} - {self.organization.name}"

class Category(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='categories', verbose_name="Organización")
    name = models.CharField(max_length=100, verbose_name="Nombre")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    color = models.CharField(max_length=7, default="#000000", verbose_name="Color (Hex)")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.name

class Project(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='projects', verbose_name="Organización")
    name = models.CharField(max_length=200, verbose_name="Nombre")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"

    def __str__(self):
        return self.name

class ProjectOrganizationAccess(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='shared_organizations', verbose_name="Proyecto")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='shared_projects', verbose_name="Organización")

    class Meta:
        verbose_name = "Acceso de organización a proyecto"
        verbose_name_plural = "Accesos de organizaciones a proyectos"
        unique_together = ('project', 'organization')

    def __str__(self):
        return f"{self.organization.name} - {self.project.name}"

class ProjectUserAccess(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_accesses', verbose_name="Usuario")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='user_accesses', verbose_name="Proyecto")

    class Meta:
        verbose_name = "Acceso de usuario a proyecto"
        verbose_name_plural = "Accesos de usuarios a proyectos"
        unique_together = ('user', 'project')

    def __str__(self):
        return f"{self.user.username} - {self.project.name}"

class Valuation(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='valuations', verbose_name="Proyecto")
    name = models.CharField(max_length=255, verbose_name="Nombre de la valuación", default="Valuación")
    amount_usd = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="Monto en Dólares", default=0)
    amount_bs = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="Monto en Bolívares", default=0)
    daily_rate = models.DecimalField(max_digits=20, decimal_places=4, verbose_name="Tasa del día", default=1)

    class Meta:
        verbose_name = "Valuación"
        verbose_name_plural = "Valuaciones"

    def __str__(self):
        return f"{self.name} - {self.project.name} ({self.amount_usd} $)"

class Transaction(models.Model):
    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]

    date = models.DateField(verbose_name="Fecha")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='transactions', verbose_name="Organización")
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions', verbose_name="Cuenta")
    reference_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Número de referencia")
    description = models.TextField(verbose_name="Descripción")
    notes = models.TextField(blank=True, null=True, verbose_name="Notas")
    
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Categoría")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, blank=True, null=True, related_name='transactions', verbose_name="Proyecto")
    valuation = models.ForeignKey(Valuation, on_delete=models.SET_NULL, blank=True, null=True, related_name='transactions', verbose_name="Valuación")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendiente', verbose_name="Estado")
    
    amount_bs = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="Monto en Bolívares")
    amount_usd = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="Monto en Dólares")
    daily_rate = models.DecimalField(max_digits=20, decimal_places=4, verbose_name="Tasa del día")
    
    real_dollars = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True, verbose_name="Dólares reales")
    real_dollar_rate = models.DecimalField(max_digits=20, decimal_places=4, blank=True, null=True, verbose_name="Tasa dólar real")

    class Meta:
        verbose_name = "Transacción"
        verbose_name_plural = "Transacciones"

    def __str__(self):
        return f"{self.date} - {self.description[:50]}"
