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
            writer.writerow(["fecha", "clinica", "producto", "cambio_cantidad"])
        
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            clinica,
            producto,
            cantidad_ajustada
        ])

def verificar_alertas(inventario):
    alertas = []
    hoy = datetime.now()
    proximos_30_dias = hoy + timedelta(days=30)

    for nombre, datos in inventario.items():
        fecha_cad = datetime.strptime(datos["caducidad"], "%Y-%m-%d")
        
        # Regla 1: Por caducar (menos de 30 días)
        if hoy <= fecha_cad <= proximos_30_dias:
            alertas.append(f"⚠️ {nombre} caduca pronto: {datos['caducidad']}")
        
        # Regla 2: Stock bajo
        if datos["stock"] <= 3:
            alertas.append(f"📉 Stock crítico en {nombre}: solo quedan {datos['stock']}")
            
    return alertas