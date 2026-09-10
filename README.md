# VAULT — Respaldo de emergencia · Android ↔ PC

GUI en Python (CustomTkinter) para **respaldo y restauración de un dispositivo Android** a través de ADB, sin root: incremental, por categorías, con terminal integrada, explorador de archivos, gestor de apps, logcat en vivo y panel de estado del dispositivo.

Pensado como **el respaldo rápido para un formateo de emergencia**: conecta el teléfono, pulsa *Respaldo de emergencia* y todo lo importante (fotos, videos, documentos, música, APKs) baja a tu PC en un solo clic. Sin depender de una sola nube, sin root, con control granular cuando lo necesitas.

- **Interfaz**: CustomTkinter, estética "instrumento de precisión", esmeralda sobre grafito. Modo claro/oscuro.
- **Requisito**: `adb` en el PATH y `customtkinter` instalado
- **Estado**: v1.0
- **Multiplataforma**

---

## Características

- **9 vistas**: Respaldo · Restaurar · Conexión · Apps · Explorador · Comandos · Archivo · Ajustes · Acerca de.
- **Respaldo de emergencia**: un clic — todo, sin filtros, sin data, sin ocultos.
- **Conexión**: habilita ADB por WiFi, vincula por código (Android 11+) y conecta sin cable.
- **Backup (Celular → PC)** y **Restaurar (PC → Celular)**.
- **Respaldo incremental**: solo copia lo que cambió (skips de archivos ya sincronizados).
- **Categorías con descripción**: Todo, Fotos, Videos, Música, Documentos, Comprimidos, APKs — cada una explica qué tipos de archivo copia y desde dónde.
- **Exclusiones seguras** por defecto: caches, `LOST.DIR`, miniaturas, papelera, stickers de WhatsApp, etc. (ver `EXCL_DIRS`) + exclusiones extra configurables (separadas por coma, con ayuda en la UI).
- **Filtro por fecha**: solo archivos modificados desde una fecha dada (YYYY-MM-DD).
- **Incluir ocultos**: opción para copiar carpetas que empiezan con `.`.
- **Panel de estado del dispositivo**: modelo, Android, batería, almacenamiento, RAM, IP.
- **App Manager**: lista de apps de terceros; extrae su APK a la PC, abre o detiene apps.
- **Explorador de archivos**: navega el teléfono, baja/ sube archivos, crea carpetas, borra.
- **Logcat en vivo**: stream con colores por nivel (error, warning, info, debug).
- **Telemetría en vivo**: barra de progreso + velocidad, ETA y contador en mono.
- **Estadísticas de sesión**: tiempo total, velocidad media, archivos/min.
- **Comandos rápidos**: screencap, logcat, listar apps, info del dispositivo, reiniciar, apagar.
- **Terminal ADB integrada**: ejecuta comandos `adb ...` o del sistema sin salir de la app.
- **Configuración persistente**: rutas y preferencias en `vault_config.json` (en la carpeta de usuario de VAULT, no junto al programa).
- **Logs**: consola en pantalla + archivo `vault_<timestamp>.log` (misma carpeta de usuario).
- **Cancelación en caliente** de cualquier operación en curso.
- **Spinners de carga** en cada operación asíncrona (apps, explorador, estadísticas).
- **Acerca de**: créditos, licencia y enlace al repositorio.

---

## Instalación

### 1. Descarga ADB (una sola vez)

ADB es la herramienta gratuita de Google que VAULT usa para hablar con tu teléfono.

1. Descarga **platform-tools** desde: https://developer.android.com/tools/releases/platform-tools
2. Descomprime la carpeta donde quieras (ej. `C:\platform-tools` en Windows, `~/platform-tools` en Linux).
3. Añade esa carpeta al PATH o, más fácil, escribe la ruta completa del `adb` dentro de **Ajustes → Ruta de ADB**.

### 2. Activa la depuración USB en tu teléfono

1. Ve a **Ajustes → Acerca del teléfono** y toca 7 veces **Número de compilación** (se activan las opciones de desarrollador).
2. Entra a **Ajustes → Opciones de desarrollador** y activa **Depuración USB**.
3. Conecta el teléfono por cable y acepta el aviso de autorización.

### 3. Instala VAULT

```bash
pip install customtkinter
adb version   # debe responder, no "command not found"
python vault.py
```

### 4. Compilar para Windows (opcional)

Si prefieres un `.exe` sin Python instalado:

```bash
pip install customtkinter pillow pyinstaller
pyinstaller --onefile --windowed --name VAULT --icon vault.ico --collect-all customtkinter vault.py
```

El ejecutable queda en `dist\VAULT.exe`. ADB se descarga aparte y se configura en **Ajustes → Ruta de ADB**.

## Uso

```bash
python vault.py
```

1. Conecta el teléfono por ADB (`adb devices` debe listarlo como `device`).
2. En **Respaldo**: pulsa *Respaldo de emergencia* para todo, o elige categoría y fecha y pulsa *Iniciar respaldo*.
3. Monitorea la telemetría; puedes cancelar cuando quieras.
4. **Conexión** te permite pasar a WiFi sin cable; **Apps** y **Explorador** gestionan el teléfono.
5. **Comandos** permite acciones rápidas, logcat en vivo y terminal `adb shell ...` al vuelo.
6. **Ajustes** guarda rutas, exclusiones extra y el tema claro/oscuro.

---

## Estructura

```
├── vault.py        Todo el programa (interfaz + lógica)
├── vault.png       Logo (sidebar / icono)
├── vault.ico       Icono de ventana
└── LICENSE
```

---

## Licencia

MIT — ver [LICENSE](LICENSE).

> Hecho con la ayuda de un compañero de código IA. ✨