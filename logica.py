import pandas as pd
import os
import csv
from datetime import datetime, timedelta


def guardar_pedido(datos):
    unidad = datos["Unidad"].replace(" ", "_")
    mes_año = datetime.now().strftime("%B_%Y")

    ruta_carpeta = f"Inventario_Unidades/{unidad}"
    if not os.path.exists(ruta_carpeta):
        os.makedirs(ruta_carpeta)

    nombre_archivo = f"{ruta_carpeta}/Pedidos_{mes_año}.xlsx"

    df_nuevo = pd.DataFrame([datos])

    if os.path.exists(nombre_archivo):
        df_existente = pd.read_excel(nombre_archivo)
        df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
    else:
        df_final = df_nuevo

    df_final.to_excel(nombre_archivo, index=False)
    return nombre_archivo


def registrar_evento_ml(clinica, producto, cantidad_ajustada):
    archivo_historial = "consumo_datos_ml.csv"
    existe = os.path.exists(archivo_historial)

    with open(archivo_historial, mode="a", newline="") as f:
        writer = csv.writer(f)
        # Si el archivo es nuevo, ponemos cabeceras (ideal para Pandas después)
        if not existe:
            writer.writerow(
                ["fecha", "clinica", "producto", "cambio_cantidad"])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            clinica,
            producto,
            cantidad_ajustada
        ])


def verificar_alertas(inventario):
    alertas = []
    # Si por alguna razón el inventario no es un diccionario válido, salimos
    if not isinstance(inventario, dict):
        return []

    for ref, datos in inventario.items():
        # Si 'datos' es un número o algo que no sea un diccionario, lo ignoramos
        if not isinstance(datos, dict):
            continue

        nombre = datos.get("nombre", "Producto Desconocido")
        # Usamos .get para que si no existe 'stock_nuevo', devuelva 0 y no truene
        cantidad = datos.get("stock_nuevo", 0)

        if cantidad == 0:
            alertas.append(f"🚨 {nombre} AGOTADO")
        elif cantidad < 3:
            alertas.append(f"⚠️ {nombre} bajo en stock ({cantidad})")

    return alertas


def exportar_auditoria_completa(unidad, inventario):

    fecha_hoy = datetime.now().strftime("%Y%m%d_%H%M")
    nombre_archivo = f"Auditoria_{unidad.replace(' ', '_')}_{fecha_hoy}.csv"

    columnas = [
        "Referencia",
        "Reactivo",
        "Presentación",
        "Caducidad",
        "En Uso",
        "Nuevo",
        "Solicitado"
    ]

    try:
        with open(nombre_archivo, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(columnas)

            for ref, datos in inventario.items():
                writer.writerow([
                    ref,
                    datos.get("nombre", ""),
                    datos.get("presentacion", ""),
                    datos.get("caducidad", "N/A"),
                    datos.get("en_uso", 0),
                    datos.get("stock_nuevo", 0),
                    datos.get("solicitado", 0)
                ])
        return nombre_archivo
    except Exception as e:
        print(f"Error al exportar: {e}")
        return None
