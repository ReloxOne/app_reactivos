import pandas as pd
import os
from datetime import datetime

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