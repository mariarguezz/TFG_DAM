# MyPark — Sistema de gestión y reserva de parking corporativo

Trabajo de Fin de Grado — Grado Superior en Desarrollo de Aplicaciones Multiplataforma  
Autora: María Rodríguez Martínez  
Centro: Sinergia FP con Palcam  
Curso: 2025-2026

---

## Descripción

MyPark es una aplicación web multiplataforma para la gestión y reserva de plazas de parking corporativo. Permite a los empleados consultar la disponibilidad de plazas en tiempo real mediante un mapa interactivo tipo Gantt, realizar reservas y gestionar visitas externas. Los administradores disponen de un panel completo con estadísticas, gestión de usuarios y visualización de todas las reservas.

---

## Tecnologías utilizadas

- **Backend:** Python 3.14 + Django 6.0
- **Base de datos:** MySQL 8.0
- **Frontend:** HTML5 + Bootstrap 5 + JavaScript
- **Tipografía:** Inter (Google Fonts)
- **IDE:** PyCharm Community

---

## Instalación y configuración

### Requisitos previos
- Python 3.10 o superior
- MySQL 8.0 o superior
- pip

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu_usuario/MyPark.git
cd MyPark
```

### 2. Crear y activar el entorno virtual
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install django mysqlclient Pillow
```

### 4. Configurar la base de datos
Crear la base de datos en MySQL:
```sql
CREATE DATABASE parking_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Editar `parking/settings.py` con las credenciales de MySQL:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'parking_db',
        'USER': 'tu_usuario',
        'PASSWORD': 'tu_contraseña',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### 5. Aplicar migraciones
```bash
python manage.py migrate
```

### 6. Cargar datos de prueba
```bash
python manage.py shell
```

Dentro de la shell:
```python
from mypark.models import TipoPlaza, Plaza, Usuario

# Tipos de plaza
TipoPlaza.objects.create(nombre='Estándar', icono='🚗')
TipoPlaza.objects.create(nombre='Eléctrica', icono='⚡')
TipoPlaza.objects.create(nombre='Movilidad Reducida', icono='♿')
TipoPlaza.objects.create(nombre='Visita', icono='👤')

# Plazas
estandar = TipoPlaza.objects.get(nombre='Estándar')
electrica = TipoPlaza.objects.get(nombre='Eléctrica')
pmr = TipoPlaza.objects.get(nombre='Movilidad Reducida')
visita = TipoPlaza.objects.get(nombre='Visita')

for i in range(1, 182):
    Plaza.objects.create(numero_plaza=f'P{i}', tipo_plaza=estandar)
for i in range(1, 21):
    Plaza.objects.create(numero_plaza=f'E{i}', tipo_plaza=electrica)
for i in range(1, 11):
    Plaza.objects.create(numero_plaza=f'PMR{i}', tipo_plaza=pmr)
for i in range(1, 5):
    Plaza.objects.create(numero_plaza=f'V{i}', tipo_plaza=visita)

# Usuarios de prueba
Usuario.objects.create_superuser(username='admin', password='Admin1234', email='admin@mypark.com', rol='administrador')
Usuario.objects.create_user(username='empleado1', password='Empleado1234', email='empleado1@mypark.com', rol='empleado')

exit()
```

### 7. Arrancar el servidor
```bash
python manage.py runserver
```

---

## Acceso a la aplicación

| Panel | URL | Usuario | Contraseña |
|---|---|---|---|
| Empleado | http://127.0.0.1:8000/ | empleado1 | Empleado1234 |
| Administrador | http://127.0.0.1:8000/admin-login/ | admin | Admin1234 |

---

## Funcionalidades principales

**Panel empleado:**
- Mapa de plazas tipo Gantt en tiempo real
- Filtros por tipo de plaza y disponibilidad
- Nueva reserva con indicador de disponibilidad
- Gestión de reservas propias
- Perfil con foto

**Panel administrador:**
- Dashboard con estadísticas de ocupación
- Gestión completa de usuarios
- Visualización de todas las reservas
- Generación de reportes *(próximamente)*

---

## Seguridad

- Contraseñas cifradas con PBKDF2 + SHA256
- Protección CSRF en todos los formularios
- Límite de 5 intentos de login con bloqueo de 5 minutos
- Control de acceso por roles

---

## Estructura del proyecto

```
TFG DAM/
├── parking/          ← Configuración del proyecto
│   ├── settings.py
│   └── urls.py
├── mypark/           ← Aplicación principal
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── templates/
└── manage.py
```
