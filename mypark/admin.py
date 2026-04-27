from django.contrib import admin
from .models import TipoPlaza, Plaza, Usuario, Reserva, Reporte

admin.site.register(TipoPlaza)
admin.site.register(Plaza)
admin.site.register(Usuario)
admin.site.register(Reserva)
admin.site.register(Reporte)