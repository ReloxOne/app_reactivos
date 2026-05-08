import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
from datetime import datetime
from dotenv import load_dotenv

# Variables .env
load_dotenv()

def enviar_por_correo(lista_rutas, unidad_nombre):
    # Leer variables .env
    remitente    = os.getenv("CORREO_REMITENTE")
    password     = os.getenv("CORREO_PASSWORD")
    destinatario = os.getenv("CORREO_DESTINATARIO")

    # Validación de credenciales
    if not all([remitente, password, destinatario]):
        print("Error: faltan credenciales en el archivo .env")
        return False

    msg = MIMEMultipart()
    nombre_base = os.path.basename(lista_rutas[0]) if lista_rutas else "Pedido"
    msg['Subject'] = f"PEDIDO DE REACTIVOS - {nombre_base}"
    msg['From']    = remitente
    msg['To']      = destinatario

    fecha_hoy = datetime.now().strftime("%d/%m/%Y a las %H:%M horas")

    cuerpo_mensaje = f"""Este es un correo automatizado.

Se adjunta el pedido de reactivos correspondiente a la unidad: {unidad_nombre},
generado el día {fecha_hoy}.

Favor de tomarlo en cuenta para su procesamiento.

No es necesario responder a este correo."""

    msg.attach(MIMEText(cuerpo_mensaje, "plain"))

    try:
        for ruta in lista_rutas:
            if ruta and os.path.exists(ruta):
                with open(ruta, "rb") as f:
                    parte = MIMEApplication(f.read(), Name=os.path.basename(ruta))
                parte['Content-Disposition'] = f'attachment; filename="{os.path.basename(ruta)}"'
                msg.attach(parte)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(remitente, password)
            server.send_message(msg)
        return True

    except Exception as e:
        print(f"Error en envío: {e}")
        return False