from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('reserva/nueva/', views.nueva_reserva, name='nueva_reserva'),
    path('mis-reservas/', views.mis_reservas, name='mis_reservas'),
    path('reserva/cancelar/<int:reserva_id>/', views.cancelar_reserva, name='cancelar_reserva'),
    path('mi-perfil/', views.mi_perfil, name='mi_perfil'),
    path('api/disponibilidad/', views.disponibilidad, name='disponibilidad'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/reservas/', views.admin_reservas, name='admin_reservas'),
    path('admin-panel/usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('admin-panel/usuarios/nuevo/', views.admin_nuevo_usuario, name='admin_nuevo_usuario'),
    path('admin-panel/reporte/', views.admin_reporte, name='admin_reporte'),
    path('admin-panel/usuarios/<int:usuario_id>/editar/', views.admin_editar_usuario, name='admin_editar_usuario'),
    path('admin-panel/usuarios/<int:usuario_id>/eliminar/', views.admin_eliminar_usuario, name='admin_eliminar_usuario'),
]