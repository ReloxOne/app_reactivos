import os
import shutil
import psutil  # Necesitarás instalarlo con: pip install psutil
from pathlib import Path

def obtener_unidades_usb():
    """Detecta las unidades extraíbles conectadas."""
    unidades = []
    for partition in psutil.disk_partitions():
        if 'removable' in partition.opts or partition.fstype == '':
            # En Windows, las USB suelen aparecer como 'removable'
            unidades.append(partition.mountpoint)
    return unidades

def limpiar_y_copiar():
    directorio_actual = Path(os.getcwd())
    nombre_proyecto = directorio_actual.name
    
    # --- 1. SELECCIÓN DE USB ---
    usbs = obtener_unidades_usb()
    if not usbs:
        print("❌ No se detectó ninguna unidad USB. Conecta una e intenta de nuevo.")
        return

    print("Unidades USB detectadas:")
    for i, unidad in enumerate(usbs):
        print(f"[{i}] {unidad}")
    
    try:
        idx = int(input("\nSelecciona el número de la unidad destino: "))
        destino_usb = Path(usbs[idx]) / nombre_proyecto
    except (ValueError, IndexError):
        print("❌ Selección no válida.")
        return

    # --- 2. LIMPIEZA DE METADATOS (MODO INCÓGNITO) ---
    carpetas_a_borrar = ['.git', '.vscode', '__pycache__', '.pytest_cache', 'build', 'dist']
    extensiones_a_borrar = ['*.pyc', '*.pyo', '*.pyd']

    print(f"\n🧹 Limpiando metadatos en origen...")
    for carpeta in carpetas_a_borrar:
        for ruta in directorio_actual.rglob(carpeta):
            try:
                shutil.rmtree(ruta)
                print(f"  ✅ Borrado: {carpeta}")
            except: pass

    for ext in extensiones_a_borrar:
        for archivo in directorio_actual.rglob(ext):
            try:
                os.remove(archivo)
            except: pass

    # --- 3. COPIA A USB ---
    print(f"\n🚀 Copiando proyecto a {destino_usb}...")
    try:
        # Si la carpeta ya existe en la USB, la borramos para que la copia sea fresca
        if destino_usb.exists():
            shutil.rmtree(destino_usb)
        
        # Copiamos todo el árbol de archivos
        shutil.copytree(directorio_actual, destino_usb)
        print(f"\n✨ ¡Éxito! Proyecto extraído de forma segura a la USB.")
        print(f"📂 Ubicación: {destino_usb}")
    except Exception as e:
        print(f"❌ Error al copiar: {e}")

if __name__ == "__main__":
    # Necesitas instalar psutil para que funcione la detección de USB
    # Ejecuta: pip install psutil
    limpiar_y_copiar()