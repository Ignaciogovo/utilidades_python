import os
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class CorreoWritter:
    def __init__(self):
        self.remitente = os.getenv('EMISOR_CORREO')
        self.password = os.getenv('PASS_CORREO')
        self.receptores = os.getenv('RECEPTOR_CORREO', '').split(',')
        self.asunto = os.getenv('ASUNTO', 'UPS ALERTA')
        self.texto = os.getenv('TEXTO', '')

    def iniciar_sesion(self):
        email_smtp = "smtp.gmail.com"
        self.server = smtplib.SMTP(email_smtp, 587) 
        self.server.ehlo()
        self.server.starttls()
        self.server.login(self.remitente, self.password)

    def enviar_correo(self, html=0):
        if html == 0:
            mensaje = EmailMessage()
            mensaje.set_content(self.texto)
        else:
            mensaje = MIMEMultipart()
            mensaje.attach(MIMEText(self.texto, 'html'))

        mensaje['From'] = self.remitente
        mensaje['To'] = ', '.join(self.receptores)
        mensaje['Subject'] = self.asunto

        self.server.sendmail(self.remitente, self.receptores, mensaje.as_string())

    def cerrar_conexion(self):
        self.server.quit()

if __name__ == "__main__":
    correo = CorreoWritter()
    correo.iniciar_sesion()
    correo.enviar_correo()
    correo.cerrar_conexion()
    print(f"Correo enviado a {correo.receptores} con asunto '{correo.asunto}'")
