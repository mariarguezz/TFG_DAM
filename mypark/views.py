from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Plaza, Reserva
from django.http import JsonResponse
import json
from django.core.exceptions import PermissionDenied

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.rol != 'administrador':
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper

def login_view(request):
    error = None
    intentos = request.session.get('login_intentos', 0)
    bloqueado_hasta = request.session.get('login_bloqueado_hasta', None)

    # Comprobar si está bloqueado
    if bloqueado_hasta:
        from datetime import datetime
        bloqueado_hasta_dt = datetime.fromisoformat(bloqueado_hasta)
        ahora = datetime.now()
        if ahora < bloqueado_hasta_dt:
            segundos_restantes = int((bloqueado_hasta_dt - ahora).total_seconds())
            minutos = segundos_restantes // 60
            segundos = segundos_restantes % 60
            error = f'Demasiados intentos fallidos. Espera {minutos}:{segundos:02d} minutos.'
            return render(request, 'mypark/login.html', {'error': error, 'bloqueado': True})
        else:
            # Desbloquear
            request.session['login_intentos'] = 0
            request.session['login_bloqueado_hasta'] = None
            intentos = 0

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Login correcto — resetear intentos
            request.session['login_intentos'] = 0
            request.session['login_bloqueado_hasta'] = None
            login(request, user)
            if user.rol == 'administrador':
                return redirect('admin_panel')
            else:
                return redirect('dashboard')
        else:
            # Login incorrecto — incrementar intentos
            intentos += 1
            request.session['login_intentos'] = intentos

            if intentos >= 5:
                from datetime import datetime, timedelta
                bloqueado_hasta = datetime.now() + timedelta(minutes=5)
                request.session['login_bloqueado_hasta'] = bloqueado_hasta.isoformat()
                error = 'Demasiados intentos fallidos. Espera 5 minutos.'
            else:
                intentos_restantes = 5 - intentos
                error = f'Usuario o contraseña incorrectos. Te quedan {intentos_restantes} intentos.'

    return render(request, 'mypark/login.html', {'error': error})

def logout_view(request):
    rol = request.user.rol if request.user.is_authenticated else None
    logout(request)
    if rol == 'administrador':
        return redirect('admin_login')
    else:
        return redirect('login')

@login_required(login_url='login')
def dashboard(request):
    from datetime import date, datetime, timedelta
    from django.core.paginator import Paginator
    from mypark.models import TipoPlaza
    import re

    # Fechas
    hoy = date.today()
    manana = hoy + timedelta(days=1)
    fecha_str = request.GET.get('fecha', hoy.isoformat())

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        fecha = hoy

    # Filtros
    orden = request.GET.get('orden', 'asc')
    tipo_filtro = request.GET.get('tipo', 'todas')
    disponibilidad_filtro = request.GET.get('disponibilidad', 'todas')

    # Plazas
    plazas = Plaza.objects.all().select_related('tipo_plaza')
    if tipo_filtro != 'todas':
        plazas = plazas.filter(tipo_plaza__nombre=tipo_filtro)

    def orden_natural(plaza):
        partes = re.split(r'(\d+)', plaza.numero_plaza)
        return [int(p) if p.isdigit() else p for p in partes]

    plazas = list(plazas)
    plazas.sort(key=orden_natural, reverse=(orden == 'desc'))

    reservas = Reserva.objects.filter(fecha=fecha)

    if disponibilidad_filtro == 'libres':
        plazas_ids = [p.id for p in plazas if not reservas.filter(plaza=p).exists()]
        plazas = [p for p in plazas if p.id in plazas_ids]
    elif disponibilidad_filtro == 'ocupadas':
        plazas_ids = [p.id for p in plazas if reservas.filter(plaza=p).exists()]
        plazas = [p for p in plazas if p.id in plazas_ids]

    # Horas
    hora_inicio = 8
    hora_fin = 18
    horas = [f"{h:02d}:00" for h in range(hora_inicio, hora_fin + 1)]

    # Mapa
    mapa = []
    for plaza in plazas:
        reservas_plaza = reservas.filter(plaza=plaza)
        franjas_raw = []
        for h in range(hora_inicio, hora_fin + 1):
            ocupada = any(
                r.hora_inicio.hour <= h < r.hora_fin.hour
                for r in reservas_plaza
            )
            franjas_raw.append(ocupada)

        franjas_agrupadas = []
        i = 0
        while i < len(franjas_raw):
            estado = franjas_raw[i]
            count = 1
            while i + count < len(franjas_raw) and franjas_raw[i + count] == estado:
                count += 1
            franjas_agrupadas.append({'ocupada': estado, 'span': count})
            i += count

        mapa.append({'plaza': plaza, 'franjas': franjas_agrupadas})

    paginator = Paginator(mapa, 15)
    pagina_actual = request.GET.get('pagina', 1)
    mapa_paginado = paginator.get_page(pagina_actual)

    fecha_anterior = (fecha - timedelta(days=1)).isoformat()
    fecha_siguiente = (fecha + timedelta(days=1)).isoformat()

    # Estadísticas por tipo
    reservas_hoy = Reserva.objects.filter(fecha=hoy)
    tipos_con_stats = []
    for tipo in TipoPlaza.objects.all():
        total = Plaza.objects.filter(tipo_plaza=tipo).count()
        ocupadas = reservas_hoy.filter(plaza__tipo_plaza=tipo).values('plaza').distinct().count()
        libres = total - ocupadas
        tipo.plazas_libres = libres
        tipo.plazas_ocupadas = ocupadas
        tipos_con_stats.append(tipo)

    # Próximas reservas
    proximas_reservas = Reserva.objects.filter(
        usuario=request.user,
        fecha__gte=manana
    ).select_related('plaza', 'plaza__tipo_plaza').order_by('fecha', 'hora_inicio')[:3]

    # Fechas display
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
             'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
    es_hoy = fecha == hoy
    fecha_display = "Hoy" if es_hoy else f"{fecha.day} de {meses[fecha.month - 1]} de {fecha.year}"
    fecha_larga = f"{dias[hoy.weekday()].capitalize()} {hoy.day} de {meses[hoy.month - 1]} de {hoy.year}"

    context = {
        'fecha': fecha_str,
        'fecha_display': fecha_display,
        'fecha_anterior': fecha_anterior,
        'fecha_siguiente': fecha_siguiente,
        'horas': horas,
        'mapa': mapa_paginado,
        'paginator': paginator,
        'orden': orden,
        'tipo_filtro': tipo_filtro,
        'disponibilidad_filtro': disponibilidad_filtro,
        'tipos': tipos_con_stats,
        'proximas_reservas': proximas_reservas,
        'fecha_larga': fecha_larga,
    }
    return render(request, 'mypark/dashboard.html', context)

def nueva_reserva(request):
    from .models import Plaza, TipoPlaza
    from django.contrib import messages

    plazas = Plaza.objects.all().select_related('tipo_plaza').order_by('numero_plaza')
    tipos = TipoPlaza.objects.all()
    error = None
    success = None

    if request.method == 'POST':
        plaza_id = request.POST.get('plaza')
        fecha = request.POST.get('fecha')
        hora_inicio = request.POST.get('hora_inicio')
        hora_fin = request.POST.get('hora_fin')
        matricula = request.POST.get('matricula')
        es_visita = request.POST.get('es_visita') == 'on'
        nombre_visita = request.POST.get('nombre_visita', '')
        dni_visita = request.POST.get('dni_visita', '')

        # Validaciones
        if not all([plaza_id, fecha, hora_inicio, hora_fin, matricula]):
            error = 'Por favor rellena todos los campos obligatorios'
        elif hora_fin <= hora_inicio:
            error = 'La hora de fin debe ser posterior a la hora de inicio'
        elif es_visita and not nombre_visita:
            error = 'El nombre de la visita es obligatorio'
        else:
            # Comprobar solapamiento
            from datetime import time
            plaza = Plaza.objects.get(id=plaza_id)
            solapamiento = Reserva.objects.filter(
                plaza=plaza,
                fecha=fecha,
                hora_inicio__lt=hora_fin,
                hora_fin__gt=hora_inicio
            ).exists()

            if solapamiento:
                error = 'La plaza seleccionada no está disponible en ese horario'
            else:
                Reserva.objects.create(
                    usuario=request.user,
                    plaza=plaza,
                    fecha=fecha,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    matricula=matricula,
                    es_visita=es_visita,
                    nombre_visita=nombre_visita if es_visita else '',
                    dni_visita=dni_visita if es_visita else ''
                )
                success = 'Reserva confirmada correctamente'

    context = {
        'plazas': plazas,
        'tipos': tipos,
        'error': error,
        'success': success,
        'horas': [f"{h:02d}:00" for h in range(8, 19)],
    }
    return render(request, 'mypark/nueva_reserva.html', context)

def mis_reservas(request):
    from datetime import date

    tipo_filtro = request.GET.get('tipo', 'todas')
    estado_filtro = request.GET.get('estado', 'todas')
    visita_filtro = request.GET.get('visita', 'todas')
    fecha_filtro = request.GET.get('fecha', '')

    reservas = Reserva.objects.filter(
        usuario=request.user
    ).select_related('plaza', 'plaza__tipo_plaza').order_by('-fecha', '-hora_inicio')

    # Filtro por tipo de plaza
    if tipo_filtro != 'todas':
        reservas = reservas.filter(plaza__tipo_plaza__nombre=tipo_filtro)

    # Filtro por estado
    hoy = date.today()
    if estado_filtro == 'futuras':
        reservas = reservas.filter(fecha__gte=hoy)
    elif estado_filtro == 'pasadas':
        reservas = reservas.filter(fecha__lt=hoy)

    # Filtro por visita
    if visita_filtro == 'si':
        reservas = reservas.filter(es_visita=True)
    elif visita_filtro == 'no':
        reservas = reservas.filter(es_visita=False)

    # Filtro por fecha
    if fecha_filtro:
        reservas = reservas.filter(fecha=fecha_filtro)

    from mypark.models import TipoPlaza
    tipos = TipoPlaza.objects.all()

    context = {
        'reservas': reservas,
        'tipos': tipos,
        'tipo_filtro': tipo_filtro,
        'estado_filtro': estado_filtro,
        'visita_filtro': visita_filtro,
        'fecha_filtro': fecha_filtro,
        'hoy': date.today(),
    }
    return render(request, 'mypark/mis_reservas.html', context)

def cancelar_reserva(request, reserva_id):
    if request.method == 'POST':
        reserva = Reserva.objects.get(id=reserva_id, usuario=request.user)
        reserva.delete()
    return redirect('mis_reservas')

def mi_perfil(request):
    if request.method == 'POST' and request.FILES.get('foto'):
        usuario = request.user
        usuario.foto = request.FILES['foto']
        usuario.save()

    context = {
        'usuario': request.user,
    }

    if request.user.rol == 'administrador':
        return render(request, 'mypark/admin_mi_perfil.html', context)
    else:
        return render(request, 'mypark/mi_perfil.html', context)

def disponibilidad(request):
    plaza_id = request.GET.get('plaza_id')
    fecha = request.GET.get('fecha')
    hora_inicio = request.GET.get('hora_inicio')
    hora_fin = request.GET.get('hora_fin')

    if not all([plaza_id, fecha, hora_inicio, hora_fin]):
        return JsonResponse({'disponible': None})

    solapamiento = Reserva.objects.filter(
        plaza_id=plaza_id,
        fecha=fecha,
        hora_inicio__lt=hora_fin,
        hora_fin__gt=hora_inicio
    ).exists()

    return JsonResponse({'disponible': not solapamiento})

def admin_login_view(request):
    error = None
    intentos = request.session.get('admin_login_intentos', 0)
    bloqueado_hasta = request.session.get('admin_login_bloqueado_hasta', None)

    if bloqueado_hasta:
        from datetime import datetime
        bloqueado_hasta_dt = datetime.fromisoformat(bloqueado_hasta)
        ahora = datetime.now()
        if ahora < bloqueado_hasta_dt:
            segundos_restantes = int((bloqueado_hasta_dt - ahora).total_seconds())
            minutos = segundos_restantes // 60
            segundos = segundos_restantes % 60
            error = f'Demasiados intentos fallidos. Espera {minutos}:{segundos:02d} minutos.'
            return render(request, 'mypark/admin_login.html', {'error': error, 'bloqueado': True})
        else:
            request.session['admin_login_intentos'] = 0
            request.session['admin_login_bloqueado_hasta'] = None
            intentos = 0

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None and user.rol == 'administrador':
            request.session['admin_login_intentos'] = 0
            request.session['admin_login_bloqueado_hasta'] = None
            login(request, user)
            return redirect('admin_panel')
        else:
            intentos += 1
            request.session['admin_login_intentos'] = intentos
            if intentos >= 5:
                from datetime import datetime, timedelta
                bloqueado_hasta = datetime.now() + timedelta(minutes=5)
                request.session['admin_login_bloqueado_hasta'] = bloqueado_hasta.isoformat()
                error = 'Demasiados intentos fallidos. Espera 5 minutos.'
            else:
                intentos_restantes = 5 - intentos
                error = f'Credenciales incorrectas o sin permisos de administrador. Te quedan {intentos_restantes} intentos.'

    return render(request, 'mypark/admin_login.html', {'error': error})

@login_required(login_url='login')
@admin_required
def admin_panel(request):
    from datetime import date, datetime, timedelta
    from django.core.paginator import Paginator
    from mypark.models import TipoPlaza
    import re

    fecha_str = request.GET.get('fecha', date.today().isoformat())
    orden = request.GET.get('orden', 'asc')
    tipo_filtro = request.GET.get('tipo', 'todas')
    disponibilidad_filtro = request.GET.get('disponibilidad', 'todas')

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        fecha = date.today()

    plazas = Plaza.objects.all().select_related('tipo_plaza')

    if tipo_filtro != 'todas':
        plazas = plazas.filter(tipo_plaza__nombre=tipo_filtro)

    def orden_natural(plaza):
        partes = re.split(r'(\d+)', plaza.numero_plaza)
        return [int(p) if p.isdigit() else p for p in partes]

    plazas = list(plazas)
    plazas.sort(key=orden_natural, reverse=(orden == 'desc'))

    reservas = Reserva.objects.filter(fecha=fecha)

    if disponibilidad_filtro == 'libres':
        plazas_ids = [p.id for p in plazas if not reservas.filter(plaza=p).exists()]
        plazas = [p for p in plazas if p.id in plazas_ids]
    elif disponibilidad_filtro == 'ocupadas':
        plazas_ids = [p.id for p in plazas if reservas.filter(plaza=p).exists()]
        plazas = [p for p in plazas if p.id in plazas_ids]

    hora_inicio = 8
    hora_fin = 18
    horas = [f"{h:02d}:00" for h in range(hora_inicio, hora_fin + 1)]

    mapa = []
    for plaza in plazas:
        reservas_plaza = reservas.filter(plaza=plaza)
        franjas_raw = []
        for h in range(hora_inicio, hora_fin + 1):
            ocupada = any(
                r.hora_inicio.hour <= h < r.hora_fin.hour
                for r in reservas_plaza
            )
            franjas_raw.append(ocupada)

        franjas_agrupadas = []
        i = 0
        while i < len(franjas_raw):
            estado = franjas_raw[i]
            count = 1
            while i + count < len(franjas_raw) and franjas_raw[i + count] == estado:
                count += 1
            franjas_agrupadas.append({'ocupada': estado, 'span': count})
            i += count

        mapa.append({'plaza': plaza, 'franjas': franjas_agrupadas})

    paginator = Paginator(mapa, 15)
    pagina_actual = request.GET.get('pagina', 1)
    mapa_paginado = paginator.get_page(pagina_actual)

    fecha_anterior = (fecha - timedelta(days=1)).isoformat()
    fecha_siguiente = (fecha + timedelta(days=1)).isoformat()

    hoy = date.today()

    # Estadísticas
    total_plazas = Plaza.objects.count()
    reservas_hoy = Reserva.objects.filter(fecha=hoy)
    plazas_ocupadas_hoy = reservas_hoy.values('plaza').distinct().count()
    plazas_libres_hoy = total_plazas - plazas_ocupadas_hoy
    visitas_hoy = Reserva.objects.filter(fecha=hoy, es_visita=True).count()

    stats_tipos = []
    for tipo in TipoPlaza.objects.all():
        total = Plaza.objects.filter(tipo_plaza=tipo).count()
        ocupadas = reservas_hoy.filter(plaza__tipo_plaza=tipo).values('plaza').distinct().count()
        libres = total - ocupadas
        stats_tipos.append({
            'nombre': tipo.nombre,
            'icono': tipo.icono,
            'libres': libres,
            'ocupadas': ocupadas,
        })

    es_hoy = fecha == hoy
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
             'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    fecha_display = "Hoy" if es_hoy else f"{fecha.day} de {meses[fecha.month - 1]} de {fecha.year}"

    from mypark.models import TipoPlaza
    tipos = TipoPlaza.objects.all()

    context = {
        'fecha': fecha_str,
        'fecha_display': fecha_display,
        'fecha_anterior': fecha_anterior,
        'fecha_siguiente': fecha_siguiente,
        'horas': horas,
        'mapa': mapa_paginado,
        'paginator': paginator,
        'orden': orden,
        'tipo_filtro': tipo_filtro,
        'tipos': tipos,
        'disponibilidad_filtro': disponibilidad_filtro,
        'total_plazas': total_plazas,
        'plazas_ocupadas_hoy': plazas_ocupadas_hoy,
        'plazas_libres_hoy': plazas_libres_hoy,
        'visitas_hoy': visitas_hoy,
        'stats_tipos': stats_tipos,
    }
    return render(request, 'mypark/admin_panel.html', context)

@login_required(login_url='login')
@admin_required
def admin_reservas(request):
    from datetime import date

    tipo_filtro = request.GET.get('tipo', 'todas')
    estado_filtro = request.GET.get('estado', 'todas')
    visita_filtro = request.GET.get('visita', 'todas')
    fecha_filtro = request.GET.get('fecha', '')
    usuario_filtro = request.GET.get('usuario', '')
    matricula_filtro = request.GET.get('matricula', '')

    reservas = Reserva.objects.all().select_related(
        'plaza', 'plaza__tipo_plaza', 'usuario'
    ).order_by('-fecha', '-hora_inicio')

    if tipo_filtro != 'todas':
        reservas = reservas.filter(plaza__tipo_plaza__nombre=tipo_filtro)

    hoy = date.today()
    if estado_filtro == 'futuras':
        reservas = reservas.filter(fecha__gte=hoy)
    elif estado_filtro == 'pasadas':
        reservas = reservas.filter(fecha__lt=hoy)

    if visita_filtro == 'si':
        reservas = reservas.filter(es_visita=True)
    elif visita_filtro == 'no':
        reservas = reservas.filter(es_visita=False)

    if fecha_filtro:
        reservas = reservas.filter(fecha=fecha_filtro)

    if usuario_filtro:
        reservas = reservas.filter(usuario__username__icontains=usuario_filtro)

    if matricula_filtro:
        reservas = reservas.filter(matricula__icontains=matricula_filtro)

    from mypark.models import TipoPlaza
    tipos = TipoPlaza.objects.all()

    context = {
        'reservas': reservas,
        'tipos': tipos,
        'tipo_filtro': tipo_filtro,
        'estado_filtro': estado_filtro,
        'visita_filtro': visita_filtro,
        'fecha_filtro': fecha_filtro,
        'usuario_filtro': usuario_filtro,
        'matricula_filtro': matricula_filtro,
    }
    return render(request, 'mypark/admin_reservas.html', context)

@login_required(login_url='login')
@admin_required
def admin_usuarios(request):
    from mypark.models import Usuario

    rol_filtro = request.GET.get('rol', 'todos')
    nombre_filtro = request.GET.get('nombre', '')

    usuarios = Usuario.objects.all().order_by('username')

    if rol_filtro != 'todos':
        usuarios = usuarios.filter(rol=rol_filtro)

    if nombre_filtro:
        usuarios = usuarios.filter(username__icontains=nombre_filtro)

    context = {
        'usuarios': usuarios,
        'rol_filtro': rol_filtro,
        'nombre_filtro': nombre_filtro,
    }
    return render(request, 'mypark/admin_usuarios.html', context)

@login_required(login_url='login')
@admin_required
def admin_editar_usuario(request, usuario_id):
    from mypark.models import Usuario
    usuario = Usuario.objects.get(id=usuario_id)
    error = None
    success = None

    if request.method == 'POST':
        usuario.first_name = request.POST.get('first_name', '')
        usuario.last_name = request.POST.get('last_name', '')
        usuario.email = request.POST.get('email', '')
        usuario.rol = request.POST.get('rol', 'empleado')

        nueva_password = request.POST.get('password', '')
        if nueva_password:
            usuario.set_password(nueva_password)

        usuario.save()
        success = f'Usuario {usuario.username} actualizado correctamente'

    context = {
        'usuario': usuario,
        'error': error,
        'success': success,
    }
    return render(request, 'mypark/admin_editar_usuario.html', context)

@login_required(login_url='login')
@admin_required
def admin_eliminar_usuario(request, usuario_id):
    from mypark.models import Usuario
    if request.method == 'POST':
        usuario = Usuario.objects.get(id=usuario_id)
        if usuario != request.user:
            usuario.delete()
    return redirect('admin_usuarios')

@login_required(login_url='login')
@admin_required
def admin_nuevo_usuario(request):
    from mypark.models import Usuario
    error = None
    success = None

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        rol = request.POST.get('rol', 'empleado')

        if not username or not password:
            error = 'El nombre de usuario y la contraseña son obligatorios'
        elif Usuario.objects.filter(username=username).exists():
            error = 'Ya existe un usuario con ese nombre'
        else:
            Usuario.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name,
                rol=rol
            )
            success = f'Usuario {username} creado correctamente'

    context = {'error': error, 'success': success}
    return render(request, 'mypark/admin_nuevo_usuario.html', context)

@login_required(login_url='login')
@admin_required
def admin_reporte(request):
    return render(request, 'mypark/admin_reporte.html')