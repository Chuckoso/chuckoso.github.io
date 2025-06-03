# WAUR Maya–Blender Bridge - Integración Técnica (Actualizado)

Este documento resume la integración actual entre **Maya 2018** y **Blender 4.x** para el bridge de trabajo con modelos 3D dentro del proyecto WAUR. Contiene el comportamiento, flujo de archivos, y arquitectura real de los módulos usados.

---

## 🧩 Estructura de Archivos

```
/Maya/scripts/
    ma_bridge_sender.py
    ma_bridge_listener.py
    ma_bridge_session.py
    ma_bridge_ui.py

/Blender/MODULES/
    bl_bridge_listener.py

/Blender/Addons/
    bl_maya_bridge.py      ← addon instalado (con UI)
    bl_fbx_io_maya.py      ← addon para import/export FBX con configuración Maya
```

---

## 🔌 Configuración de Puertos

- **Maya escucha en puerto 6001** (para recibir comandos de Blender)
- **Blender escucha en puerto 6000** (para recibir comandos de Maya)

Esta separación evita conflictos cuando ambas aplicaciones están ejecutándose.

---

## 🔄 Flujo Maya → Blender

### 1. El usuario selecciona un objeto en Maya y presiona "Send to Blender":
- `ma_bridge_sender.py`:
  - Duplica el objeto, resetea transformaciones
  - Exporta el `.fbx` a: `C:/Telltale/temp/<scene>_<object>_toBlender.fbx`
  - Genera el `.json`: `..._meta.json` con:
    - `"object"`: path completo del objeto original
    - `"parent"`: grupo padre
    - `"world_matrix"`: transformaciones
    - `"materials"`: datos de shading groups y asignaciones por cara
    - `"light_links"`: luces linkeadas (filtradas para incluir solo transforms válidos)
  - Envía: `IMPORT|<path>` a Blender por socket (puerto 6000)

### 2. En Blender:
- `bl_bridge_listener.py` escucha en puerto 6000
- Al recibir `IMPORT|...`:
  - Importa el `.fbx` usando `bpy.ops.import_scene.fbx_maya()` si está disponible
  - Lee el `.json` y extrae metadata
  - Renombra el objeto según `"object"` del `.json`
  - Guarda atributos personalizados en el objeto:
    - `["maya_scene"]`: nombre de la escena Maya
    - `["maya_object"]`: nombre del objeto
    - `["maya_full_path"]`: path completo original

---

## 🔄 Flujo Blender → Maya

### 1. El usuario edita el modelo y presiona "Send to Maya":
- `bl_maya_bridge.py` (addon):
  - Lee `maya_scene` y `maya_object` desde los atributos del objeto
  - Exporta el `.fbx` usando `bpy.ops.export_scene.fbx_maya()` como:
    `C:/Telltale/temp/<scene>_<object>_fromBlender.fbx`
  - Envía: `REPLACE|<scene>|<object>` a Maya (puerto 6001)

### 2. En Maya:
- `ma_bridge_listener.py` recibe el comando y ejecuta `replace_object_from_blender()`:
  - Parsea scene y object del comando
  - Lee el `.json` original (del envío inicial) para obtener metadata
  - **BORRA el objeto original ANTES de importar** (crítico para evitar merge)
  - Importa el `.fbx` en modo ADD
  - Busca el objeto importado y lo procesa:
    - Restaura jerarquía (parent)
    - Aplica transformaciones (world matrix)
    - Renombra al nombre original
    - Restaura materiales por cara si hay datos
    - Restaura light linking (filtrando items válidos)

---

## 📌 Comportamiento y Validaciones

### Sistema de Sesión
- La información de sesión se guarda como **atributos personalizados** directamente en los objetos de Blender
- No requiere variables globales ni módulos externos
- Persiste al guardar el archivo `.blend`

### Manejo de FBX
- Maya exporta con transformaciones reseteadas para evitar problemas de escala/rotación
- La importación en Maya usa modo **ADD**, nunca MERGE
- El objeto original se borra ANTES de importar para evitar conflictos

### Light Linking
- El sistema filtra y valida los items del light linking:
  - Convierte shapes a transforms si es necesario
  - Ignora light sets y grupos
  - Elimina duplicados
  - Solo procesa transforms de luces válidos

### Materiales
- Captura asignaciones de materiales por cara
- Guarda información de shading groups
- Restaura asignaciones exactas al regresar de Blender

---

## ⚠️ Validaciones y Manejo de Errores

- Si no hay sesión activa, el exportador en Blender se bloquea con mensaje de error
- Si el `.json` no tiene `"object"`, se detiene el flujo
- Verifica que archivos FBX no estén vacíos antes de importar
- Maneja casos donde el path del objeto cambia después de operaciones
- Logging detallado en cada paso para debugging

---

## 🚀 Uso Típico

### En Maya:
1. Cargar la UI desde `ma_bridge_ui.py`
2. Presionar "Start/Stop Listener" para iniciar el listener en puerto 6001
3. Seleccionar objeto y usar "Send to Blender"

### En Blender:
1. Asegurar que `bl_fbx_io_maya.py` está instalado y activo
2. El listener se inicia automáticamente si `bl_maya_bridge.py` está instalado
3. Editar el modelo importado
4. Usar "Send to Maya" desde el panel Bridge

---

## 🛠️ Requisitos

- **Maya 2018** con Python 2.7
- **Blender 4.x** con Python 3.x
- Carpeta temporal: `C:/Telltale/temp` (debe existir con permisos de escritura)
- Addons de Blender instalados:
  - `bl_maya_bridge.py`
  - `bl_fbx_io_maya.py`

---

## ✅ Estado Actual

- ✅ Flujo bidireccional completo y estable
- ✅ Sistema de sesiones robusto usando atributos personalizados
- ✅ Manejo correcto de jerarquías y transformaciones
- ✅ Light linking funcional con validación de items
- ✅ Captura y restauración de materiales
- ✅ Manejo de errores mejorado
- ✅ Sin dependencias de módulos externos para sesiones

---

## 📝 Notas Importantes

1. **Codificación**: Usar solo ASCII en comentarios de código Python para Maya (no acentos ni caracteres especiales)
2. **Paths**: El sistema maneja automáticamente las diferencias entre `/` y `\` en rutas
3. **Namespaces**: El bridge NO usa namespaces para evitar complicaciones
4. **Selección**: No es necesario mantener objetos seleccionados para light linking

---

## 🐛 Solución de Problemas Comunes

### "Object has no session data"
- El objeto en Blender no tiene los atributos de sesión Maya
- Solución: Verificar que el objeto fue importado desde Maya originalmente

### Light linking muestra errores pero reporta éxito
- Normal en algunas versiones de Maya, si el conteo final es correcto, ignorar los warnings

### Objeto no aparece después de enviar
- Verificar que los puertos no estén ocupados por otra instancia
- Reiniciar Maya y Blender si es necesario

### FBX muestra ventana de warnings
- En Maya 2018 no se puede suprimir completamente
- Los warnings no afectan la funcionalidad