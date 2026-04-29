import pandas as pd
import os
import csv
from datetime import datetime
import json
import glob

def obtener_catalogo():
    if os.path.exists("catalogo_maestro.json"):
        with open("catalogo_maestro.json", "r", encoding='utf-8') as f:
            return json.load(f) # [cite: 81]
    return {}

def obtener_alertas_stock(inventario):
    alertas = []
    hoy = datetime.now()
    
    for ref, datos in inventario.items():
        # 1. Alerta de Stock Bajo (Menos de 3 unidades)
        stock = datos.get("stock_nuevo", 0)
        if stock < 3:
            alertas.append(f"⚠️ Poco Stock: {datos['nombre']} (Solo {int(stock)} cajas)")

        # 2. Alerta de Caducidad (Menos de 30 días)
        fecha_cad = datos.get("caducidad")
        if fecha_cad:
            try:
                # Intentamos convertir el texto DD-MM-AAAA a fecha
                fecha_dt = datetime.strptime(fecha_cad, "%d-%m-%Y")
                dias_restantes = (fecha_dt - hoy).days
                
                if dias_restantes < 0:
                    alertas.append(f"❌ VENCIDO: {datos['nombre']} (Venció hace {abs(dias_restantes)} días)")
                elif dias_restantes <= 30:
                    alertas.append(f"⚠️ Próximo a vencer: {datos['nombre']} ({dias_restantes} días restantes)")
            except ValueError:
                # Por si el formato de fecha está mal escrito
                pass
                
    return alertas

def guardar_pedido(datos):
    unidad = datos["Unidad"].replace(" ", "_")
    mes_año = datetime.now().strftime("%B_%Y")
    ruta_carpeta = f"Inventario_Unidades/{unidad}"
    if not os.path.exists(ruta_carpeta): os.makedirs(ruta_carpeta)
    nombre_archivo = f"{ruta_carpeta}/Pedidos_{mes_año}.xlsx"
    df_nuevo = pd.DataFrame([datos])
    if os.path.exists(nombre_archivo):
        df_existente = pd.read_excel(nombre_archivo)
        df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
    else:
        df_final = df_nuevo
    df_final.to_excel(nombre_archivo, index=False) # [cite: 69, 70]
    return nombre_archivo

def exportar_auditoria_roche(unidad, stock_sesion): # nombre_base
    def limpiar_int(valor):
        try:
            return int(float(valor)) if valor and str(valor).strip() != "" else 0
        except:
            return 0

    try:
        fecha_str = datetime.now().strftime("%d-%m-%Y")
        nombre_archivo = f"{fecha_str}_cap_inv_{unidad.replace(' ', '_')}.xlsx"
        
        carpeta = f"Reportes_{unidad.replace(' ', '_')}"
        if not os.path.exists(carpeta):
            os.makedirs(carpeta)
        
        ruta_completa = os.path.join(carpeta, nombre_archivo)

        CATALOGO = obtener_catalogo()
        nuevas_filas = []
        
        # UNIFICAMOS EN UN SOLO BUCLE
        for llave_flet, info_sesion in stock_sesion.items():
            # 1. Obtenemos la referencia limpia (sin el #1, #2...)
            referencia_limpia = llave_flet.split("#")[0]
            
            # 2. Buscamos en el catálogo usando la referencia limpia
            info_cat = CATALOGO.get(referencia_limpia, {})
            
            # 3. Realizamos los cálculos específicos para ESTA fila
            presentacion_num = limpiar_int(info_cat.get("cant_com", 0))
            a_bordo = limpiar_int(info_sesion.get("en_uso", 0))
            nuevos_stock = limpiar_int(info_sesion.get("stock_nuevo", 0))
            
            total_unidades = (nuevos_stock * presentacion_num) + a_bordo

            # 4. Guardamos todo inmediatamente en la lista
            nuevas_filas.append({
                "Referencia": referencia_limpia,
                "Alias": info_sesion.get("nombre", ""),
                "Lote": info_sesion.get("lote", "S/L"),
                "Presentación": presentacion_num,
                "A Bordo / En uso": a_bordo,
                "Nuevos (Stock)": nuevos_stock,
                "Total Real": total_unidades,
                "Caducidad": info_sesion.get("caducidad", ""),
                "Fecha de Captura": datetime.now().strftime("%d-%m-%Y %H:%M")
            })
        
        df_nuevo = pd.DataFrame(nuevas_filas)

        # Si el archivo ya existe, lo leemos y concatenamos para NO sobreescribir
        if os.path.exists(ruta_completa):
            df_existente = pd.read_excel(ruta_completa)
            # Eliminamos duplicados basados en Referencia, dejando siempre la captura más reciente
            df_final = pd.concat([df_existente, df_nuevo]).drop_duplicates(subset=['Referencia'], keep='last')
        else:
            df_final = df_nuevo

        with pd.ExcelWriter(ruta_completa, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='Auditoria')
            ws = writer.sheets['Auditoria']
            for col in ['E', 'F', 'G']: 
                for cell in ws[col]:
                    cell.number_format = '0'
            for cell in ws['A']: cell.number_format = '@' # Formato texto para Ref

        return ruta_completa # Devolvemos la ruta para el mensaje de éxito
    except Exception as e:
        print(f"Error: {e}")
        return None

def generar_catalogo_desde_excel(ruta_excel):
    catalogo_unificado = {}
    try:
        excel_file = pd.ExcelFile(ruta_excel)
        for pestaña in excel_file.sheet_names:
            df = pd.read_excel(ruta_excel, sheet_name=pestaña)
            # Limpiamos nombres de columnas de espacios accidentales
            df.columns = [str(c).strip() for c in df.columns]
            
            for _, fila in df.iterrows():
                ref = str(fila['Referencia']).strip()
                if not ref or ref == 'nan': 
                    continue
                
                catalogo_unificado[ref] = {
                    "alias": str(fila['Alias']),
                    "fabricacion": str(fila['Fabricación']),
                    "cant_com": float(fila['Cantidad_Comercial']),
                    "u_medida": str(fila['Unidad_Medida']),
                    "u_conteo": float(fila['Unidad']), # Factor de escala para el ingeniero
                    "analizador": str(fila['Analizador'])
                }
        
        with open("catalogo_maestro.json", "w", encoding='utf-8') as f:
            json.dump(catalogo_unificado, f, indent=4, ensure_ascii=False)
        print(f"✅ Catálogo unificado con {len(catalogo_unificado)} referencias.")
    except Exception as e:
        print(f"❌ Error al procesar el catálogo: {e}")

# En logica.py
import glob

def obtener_alertas_desde_excel(unidad):
    alertas = []
    hoy = datetime.now()
    carpeta = f"Reportes_{unidad.replace(' ', '_')}"
    
    if not os.path.exists(carpeta):
        return ["No hay reportes previos para esta unidad."]

    # Buscamos todos los archivos .xlsx en la carpeta
    archivos = glob.glob(os.path.join(carpeta, "*.xlsx"))
    if not archivos:
        return ["No se encontraron archivos de inventario."]

    # Ordenamos por fecha de modificación para obtener el más reciente
    archivo_reciente = max(archivos, key=os.path.getmtime)
    
    try:
        df = pd.read_excel(archivo_reciente)
        
        for _, fila in df.iterrows():
            nombre = fila.get("Alias", "Producto desconocido")
            stock = fila.get("Nuevos (Stock)", 0)
            caducidad_str = str(fila.get("Caducidad", ""))

            # 1. Regla de Stock Bajo
            if stock < 3:
                alertas.append(f"⚠️ Poco Stock: {nombre} ({int(stock)} cajas)")

            # 2. Regla de Caducidad
            if caducidad_str and caducidad_str != "nan":
                try:
                    fecha_dt = datetime.strptime(caducidad_str, "%d-%m-%Y")
                    dias_restantes = (fecha_dt - hoy).days
                    
                    if dias_restantes < 0:
                        alertas.append(f"❌ VENCIDO: {nombre}")
                    elif dias_restantes <= 30:
                        alertas.append(f"⚠️ Vence pronto: {nombre} ({dias_restantes} días)")
                except:
                    pass # Formato de fecha inválido
                    
        return alertas if alertas else ["✅ Todo al día según el último reporte."]
    except Exception as e:
        return [f"Error al leer reporte: {str(e)}"]