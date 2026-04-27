from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator


class TipoPlaza(models.Model):
    nombre = models.CharField(max_length=50)
    icono = models.CharField(max_length=50, default='bi-car-front')

    def __str__(self):
        return self.nombre


class Plaza(models.Model):
    numero_plaza = models.CharField(max_length=10)
    tipo_plaza = models.ForeignKey(TipoPlaza, on_delete=models.PROTECT)

    def __str__(self):
        return self.numero_plaza


class Usuario(AbstractUser):
    ROL_CHOICES = [
        ('empleado', 'Empleado'),
        ('administrador', 'Administrador'),
    ]
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='empleado')


class Reserva(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    plaza = models.ForeignKey(Plaza, on_delete=models.PROTECT)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    matricula = models.CharField(
        max_length=15,
        validators=[RegexValidator(
            regex=r'^[A-Z0-9\-\s]{2,15}$',
            message='La matrícula solo puede contener letras, números, guiones y espacios'
        )]
    )
    es_visita = models.BooleanField(default=False)
    nombre_visita = models.CharField(max_length=100, blank=True, null=True)
    dni_visita = models.CharField(max_length=9, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['fecha', 'hora_inicio', 'hora_fin', 'plaza']),
        ]

    def __str__(self):
        return f"Reserva {self.id} - {self.plaza} - {self.fecha}"


class Reporte(models.Model):
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    formato = models.CharField(max_length=10, default='excel')
    reservas = models.ManyToManyField(Reserva)

    def __str__(self):
        return f"Reporte {self.id} - {self.fecha_generacion}"