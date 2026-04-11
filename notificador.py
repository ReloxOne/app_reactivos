import smtplib
from email.message import EmailMessage

def enviar_por_correo(archivo_adjunto):
    # --- CONFIGURACIÓN (Usa tus datos aquí) ---
    remitente = "acruz@smlaboratorios.com"
    destinatario = "acruz@smlaboratorios.com" # Puede ser el mismo para pruebas
    password = "bxrz zwvr fbim nhua" # La contraseña de aplicación de Google
    
    msg = EmailMessage()
    msg['Subject'] = "Nuevo Pedido de Reactivos - " + archivo_adjunto
    msg['From'] = remitente
    msg['To'] = destinatario
    msg.set_content("Hola, adjunto el archivo actualizado con los pedidos de reactivos.")

    # Leemos el archivo Excel para adjuntarlo
    with open(archivo_adjunto, 'rb') as f:
        file_data = f.read()
        msg.add_attachment(
            file_data, 
            maintype='application', 
            subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
            filename=archivo_adjunto
        )

    # Conexión segura con el servidor de Gmail
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(remitente, password)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Error al enviar: {e}")
        return False