import pandas as pd
from datetime import datetime
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def asegurar_ruta(unidad, subcarpeta):
    """Crea la estructura de carpetas: Reportes/Nombre_Clinica/Inventarios o Pedidos"""
    nombre_unidad = unidad.replace(" ", "_")
    ruta = os.path.join(BASE_DIR, "Reportes", nombre_unidad, subcarpeta)
    if not os.path.exists(ruta):
        os.makedirs(ruta)
    return ruta

# --- CARGA DEL CATÁLOGO ---
def obtener_catalogo():
    try:
        df = pd.read_excel("catalogo_inventario_condesas.xlsx", dtype={"Referencia": str})
        df["Referencia"] = df["Referencia"].str.strip()
        return df.set_index("Referencia").to_dict("index")
    except Exception as e:
        print(f"Error al leer catálogo: {e}")
        return {}

# --- EXPORTACIÓN DE AUDITORÍA (REPORTE DE CAMPO) ---
def exportar_auditoria_roche(unidad, sesion_auditoria):
    catalogo_datos = obtener_catalogo()
    lista_para_excel = []

    for llave, info in sesion_auditoria.items():
        ref_base = llave.split("#")[0].strip()
        detalles_cat = catalogo_datos.get(ref_base, {})
        
        presentacion = detalles_cat.get("Cantidad_Comercial", 1)
        total_real = (info.get("stock_nuevo", 0) * presentacion) + info.get("en_uso", 0)
        
        # Solo las columnas que solicitaste
        fila = {
            "Referencia": ref_base,
            "Alias": detalles_cat.get("Alias", "N/A"),
            "A Bordo": info.get("en_uso", 0),
            "Nuevos": info.get("stock_nuevo", 0),
            "Total Real": total_real,
            "Lote": info.get("lote", ""),
            "Caducidad": info.get("caducidad", "")
        }
        lista_para_excel.append(fila)

    if not lista_para_excel:
        return None

    # Configuración de Carpeta y Nombre (Punto 1 y 3)
    ruta_carpeta = asegurar_ruta(unidad, "Inventarios")
    fecha_str = datetime.now().strftime("%d%m%Y")
    nombre_archivo = f"{fecha_str}_Cap_Inv_{unidad.replace(' ', '-')}.xlsx"
    ruta_completa = os.path.join(ruta_carpeta, nombre_archivo)

    df_nuevo = pd.DataFrame(lista_para_excel)

    # Lógica de anexar o crear (Punto 4)
    if os.path.exists(ruta_completa):
        df_existente = pd.read_excel(ruta_completa)
        # Combinamos y eliminamos duplicados por Referencia/Lote para no encimar datos
        df_final = pd.concat([df_existente, df_nuevo]).drop_duplicates(subset=["Referencia", "Lote"], keep="last")
    else:
        df_final = df_nuevo
    
    df_final.to_excel(ruta_completa, index=False)
    return ruta_completa

# --- LÓGICA DE SUGERENCIA DE PEDIDOS (Agrupado por Analizador) ---
def calcular_sugerencia_pedido(sesion_auditoria):
    catalogo_datos = obtener_catalogo()
    sugerencias = []

    for llave, info in sesion_auditoria.items():
        ref_base = llave.split("#")[0].strip()
        info_cat = catalogo_datos.get(ref_base)
        
        if not info_cat: continue
            
        presentacion = int(info_cat.get("Cantidad_Comercial", 1))
        minimo = int(info_cat.get("Stock_Minimo", 0))
        analizador = info_cat.get("Analizador", "Sin asignar")
        
        total_actual = (info.get("stock_nuevo", 0) * presentacion) + info.get("en_uso", 0)
        
        if total_actual < minimo:
            faltante = minimo - total_actual
            cajas_a_pedir = (faltante + presentacion - 1) // presentacion
            
            sugerencias.append({
                "ref": ref_base,
                "nombre": info_cat.get("Alias", "Sin nombre"),
                "analizador": analizador, # Se usa para agrupar, pero no se imprime en el Excel final si no quieres
                "actual": total_actual,
                "minimo": minimo,
                "pedir_cajas": cajas_a_pedir
            })
    
    # Punto 5: Ordenar por analizador para que en la App aparezcan agrupados
    return sorted(sugerencias, key=lambda x: x["analizador"])

# --- GUARDAR PEDIDOS (Punto 3 - Ruta Específica) ---
def guardar_pedido(unidad, datos_pedido):
    ruta_carpeta = asegurar_ruta(unidad, "Pedidos")
    fecha_str = datetime.now().strftime("%d%m%Y")
    # Nota: Aquí el "Núm-de-pedido" podrías pasarlo o generarlo, por ahora uso un timestamp
    id_pedido = datetime.now().strftime("%H%M")
    nombre_archivo = f"{fecha_str}_Pedido_{id_pedido}_{unidad.replace(' ', '-')}.xlsx"
    ruta_completa = os.path.join(ruta_carpeta, nombre_archivo)
    
    df = pd.DataFrame(datos_pedido)
    df.to_excel(ruta_completa, index=False)
    return ruta_completa

# --- ALERTAS ---
def obtener_alertas_desde_excel(unidad):
    ruta_inv = asegurar_ruta(unidad, "Inventarios")
    archivos = [f for f in os.listdir(ruta_inv) if f.endswith(".xlsx")]
    if not archivos:
        return ["⚪ Sin reportes previos para esta unidad."]
    
    try:
        ultimo = os.path.join(ruta_inv, sorted(archivos)[-1])
        df = pd.read_excel(ultimo)
        alertas = []
        hoy = datetime.now()

        for _, fila in df.iterrows():
            alias = fila.get("Alias", "Desconocido")
            lote = fila.get("Lote", "S/L")
            total = fila.get("Total Real", 0)
            fecha_cad = fila.get("Caducidad")

            # 1. Alertas de Stock (Prioridad Crítica)
            if total == 0:
                alertas.append(f"❌ El reactivo {alias} está en CERO.")
            elif total < 200: # Ajusta este umbral según tu necesidad
                alertas.append(f"⚠️ El reactivo {alias} está por terminarse ({int(total)} pruebas).")

            # 2. Alertas de Caducidad
            if pd.notna(fecha_cad):
                try:
                    fecha_dt = datetime.strptime(str(fecha_cad), "%d-%m-%Y")
                    dias_restantes = (fecha_dt - hoy).days

                    if dias_restantes < 0:
                        alertas.append(f"🥀 Lote {lote} de {alias} está CADUCO.")
                    elif dias_restantes <= 30:
                        alertas.append(f"⏳ Lote {lote} de {alias} vence el {fecha_cad}.")
                except:
                    pass

        # Retornamos las 3 alertas más importantes para no saturar el menú
        if not alertas:
            return ["✅ Niveles y caducidades en orden."]
        
        return alertas[:4] 

    except Exception as e:
        return [f"⚠️ Error al procesar alertas: {str(e)}"]

def obtener_ultimo_inventario_dict(unidad):
    ruta_inv = asegurar_ruta(unidad, "Inventarios")
    archivos = [f for f in os.listdir(ruta_inv) if f.endswith(".xlsx")]
    if not archivos: return {}
    
    ultimo = os.path.join(ruta_inv, sorted(archivos)[-1])
    df = pd.read_excel(ultimo, dtype={"Referencia": str})
    
    return df.set_index("Referencia").to_dict("index")

def procesar_y_guardar_pedido_final(unidad, lista_carrito):
    # 1. Obtener último inventario
    ruta_inv = asegurar_ruta(unidad, "Inventarios")
    archivos = [f for f in os.listdir(ruta_inv) if f.endswith(".xlsx")]
    if not archivos: return None
    
    ultimo_path = os.path.join(ruta_inv, sorted(archivos)[-1])
    df_pedido = pd.read_excel(ultimo_path, dtype={"Referencia": str})
    
    # 2. Crear mapeo del pedido (Ref -> Cantidad)
    mapeo_pedido = {item["Referencia"]: item["Cantidad"] for item in lista_carrito}
    
    # 3. Añadir la columna de Pedido
    df_pedido["Pedido (Cajas)"] = df_pedido["Referencia"].map(mapeo_pedido).fillna(0)
    
    # Excel con sólo lo solictado:
    # df_pedido = df_pedido[df_pedido["Pedido (Cajas)"] > 0]

    # 5. Guardar en carpeta Pedidos
    ruta_folder = asegurar_ruta(unidad, "Pedidos")
    fecha_str = datetime.now().strftime("%d%m%Y")
    nombre_archivo = f"{fecha_str}_Pedido_{unidad.replace(' ', '-')}.xlsx"
    ruta_final = os.path.join(ruta_folder, nombre_archivo)
    
    df_pedido.to_excel(ruta_final, index=False)
    return ruta_final

def convertir_excel_a_pdf(ruta_xlsx):
    try:
        df = pd.read_excel(ruta_xlsx)
        # Convertir todo a string para evitar errores de tipo
        df = df.fillna("").astype(str)

        ruta_pdf = ruta_xlsx.replace(".xlsx", ".pdf")
        
        # Hoja carta vertical con márgenes de 15mm
        MARGEN = 15 * mm
        doc = SimpleDocTemplate(
            ruta_pdf,
            pagesize=letter,
            leftMargin=MARGEN,
            rightMargin=MARGEN,
            topMargin=MARGEN,
            bottomMargin=MARGEN
        )
        
        ancho_util = letter[0] - 2 * MARGEN  # ~182mm disponibles
        columnas = df.columns.tolist()
        n_cols = len(columnas)

        # --- Calcular ancho proporcional por columna ---
        # Mide el texto más largo de cada columna (cabecera o dato)
        def ancho_texto(texto, es_cabecera=False):
            # Aproximación: 2mm por carácter, cabeceras un poco más
            factor = 2.4 if es_cabecera else 2.0
            return max(len(str(texto)) * factor * mm, 12 * mm)

        anchos_max = []
        for col in columnas:
            max_dato = max(df[col].apply(lambda x: len(str(x))).max(), len(str(col)))
            anchos_max.append(max_dato)

        total_chars = sum(anchos_max)
        anchos_col = [
            max((v / total_chars) * ancho_util, 10 * mm)
            for v in anchos_max
        ]

        # Escalar si la suma supera el ancho útil
        suma = sum(anchos_col)
        if suma > ancho_util:
            factor_escala = ancho_util / suma
            anchos_col = [a * factor_escala for a in anchos_col]

        # --- Estilos de texto ---
        estilos = getSampleStyleSheet()
        estilo_cabecera = ParagraphStyle(
            "cabecera",
            parent=estilos["Normal"],
            fontSize=7,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            leading=9,
        )
        estilo_dato = ParagraphStyle(
            "dato",
            parent=estilos["Normal"],
            fontSize=6.5,
            fontName="Helvetica",
            alignment=TA_CENTER,
            leading=8,
        )

        # --- Construir datos de la tabla con Paragraph (permite wrap) ---
        filas_tabla = []

        # Cabeceras
        filas_tabla.append([
            Paragraph(str(col), estilo_cabecera) for col in columnas
        ])

        # Datos
        for _, fila in df.iterrows():
            filas_tabla.append([
                Paragraph(str(fila[col]), estilo_dato) for col in columnas
            ])

        # --- Crear tabla ---
        tabla = Table(filas_tabla, colWidths=anchos_col, repeatRows=1)
        tabla.setStyle(TableStyle([
            # Cabecera
            ("BACKGROUND",  (0, 0), (-1, 0),  colors.HexColor("#C8DCF0")),
            ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.HexColor("#1A1A2E")),
            ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
            # Filas alternas
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F8FF")]),
            # Bordes
            ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#AAAAAA")),
            ("BOX",         (0, 0), (-1, -1), 0.8, colors.HexColor("#555555")),
            # Padding
            ("TOPPADDING",  (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ]))

        # --- Título del documento ---
        titulo_texto = os.path.basename(ruta_xlsx).replace(".xlsx", "")
        estilo_titulo = ParagraphStyle(
            "titulo",
            parent=estilos["Normal"],
            fontSize=10,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            spaceAfter=6,
        )
        titulo = Paragraph(f"REPORTE DE PEDIDO E INVENTARIO: {titulo_texto}", estilo_titulo)

        # --- Construir PDF ---
        doc.build([titulo, Spacer(1, 4 * mm), tabla])
        return ruta_pdf

    except Exception as e:
        print(f"Error al generar PDF: {e}")
        return None