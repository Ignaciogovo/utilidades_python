# utilidades-python:enviar_correo
# Descripción: Envío de correo vía SMTP (Gmail por defecto) con soporte texto/HTML
# __version__ = "1.0.0"
#
# Clase principal: EmailWriter (estado: conexión SMTP viva + datos del mensaje)
#
# Configuración (variables de entorno, todas opcionales salvo emisor y password):
#   EMISOR_CORREO    → dirección remitente (obligatorio para conectar)
#   PASS_CORREO      → password / app password (obligatorio para conectar)
#   RECEPTOR_CORREO  → lista separada por comas (obligatorio para conectar)
#   ASUNTO           → subject por defecto. Default: "UPS ALERTA"
#   TEXTO            → cuerpo por defecto. Default: ""
#   SMTP_HOST        → servidor SMTP. Default: "smtp.gmail.com"
#   SMTP_PORT        → puerto. Default: 587
#
# API:
#   with EmailWriter() as m:
#       m.conectar()
#       m.enviar("asunto", "cuerpo")            # texto plano
#       m.enviar("asunto", "<h1>hola</h1>", html=True)
#   # al salir del with se cierra la conexión
#
#   w = EmailWriter()
#   w.conectar()
#   w.enviar()
#   w.cerrar()

import os
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# ponytail: solo SMTP con STARTTLS (puerto 587). Añadir SSL/465 si hace falta.
class EmailWriter:
    def __init__(self):
        self.remitente = os.getenv("EMISOR_CORREO", "")
        self.password = os.getenv("PASS_CORREO", "")
        self.receptores = [r.strip() for r in os.getenv("RECEPTOR_CORREO", "").split(",") if r.strip()]
        self.asunto = os.getenv("ASUNTO", "UPS ALERTA")
        self.texto = os.getenv("TEXTO", "")
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.server = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.cerrar()

    def conectar(self) -> None:
        if not self.remitente or not self.password or not self.receptores:
            raise ValueError(
                "Faltan env vars: EMISOR_CORREO, PASS_CORREO y/o RECEPTOR_CORREO"
            )
        self.server = smtplib.SMTP(self.smtp_host, self.smtp_port)
        self.server.ehlo()
        self.server.starttls()
        self.server.login(self.remitente, self.password)

    def _construir_mensaje(self, asunto: str, cuerpo: str, html: bool):
        if html:
            mensaje = MIMEMultipart()
            mensaje.attach(MIMEText(cuerpo, "html"))
        else:
            mensaje = EmailMessage()
            mensaje.set_content(cuerpo)
        mensaje["From"] = self.remitente
        mensaje["To"] = ", ".join(self.receptores)
        mensaje["Subject"] = asunto
        return mensaje

    def enviar(self, asunto: str = None, cuerpo: str = None, html: bool = False) -> None:
        if self.server is None:
            raise RuntimeError("llama a conectar() antes de enviar()")
        asunto_final = asunto if asunto is not None else self.asunto
        cuerpo_final = cuerpo if cuerpo is not None else self.texto
        mensaje = self._construir_mensaje(asunto_final, cuerpo_final, html)
        self.server.sendmail(self.remitente, self.receptores, mensaje.as_string())

    def cerrar(self) -> None:
        if self.server is not None:
            self.server.quit()
            self.server = None


if __name__ == "__main__":
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        old_env = {k: os.environ.get(k) for k in (
            "EMISOR_CORREO", "PASS_CORREO", "RECEPTOR_CORREO", "ASUNTO", "TEXTO",
            "SMTP_HOST", "SMTP_PORT",
        )}
        try:
            os.environ["EMISOR_CORREO"] = "test@origen.com"
            os.environ["PASS_CORREO"] = "secret123"
            os.environ["RECEPTOR_CORREO"] = "a@x.com, b@x.com ,c@x.com"
            os.environ["ASUNTO"] = "asunto de prueba"
            os.environ["TEXTO"] = "cuerpo por defecto"

            w = EmailWriter()
            assert w.remitente == "test@origen.com"
            assert w.receptores == ["a@x.com", "b@x.com", "c@x.com"], w.receptores
            assert w.asunto == "asunto de prueba"
            assert w.texto == "cuerpo por defecto"
            assert w.smtp_host == "smtp.gmail.com"
            assert w.smtp_port == 587
            assert w.server is None

            m_txt = w._construir_mensaje("s1", "c1", html=False)
            assert isinstance(m_txt, EmailMessage)
            assert m_txt["From"] == "test@origen.com"
            assert m_txt["To"] == "a@x.com, b@x.com, c@x.com"
            assert m_txt["Subject"] == "s1"
            assert "c1" in m_txt.as_string()

            m_html = w._construir_mensaje("s2", "<b>x</b>", html=True)
            assert isinstance(m_html, MIMEMultipart)
            assert m_html["Subject"] == "s2"
            assert "<b>x</b>" in m_html.as_string()

            try:
                w.enviar()
                assert False, "debería haber fallado sin conectar()"
            except RuntimeError:
                pass

            del os.environ["EMISOR_CORREO"]
            w2 = EmailWriter()
            try:
                w2.conectar()
                assert False, "debería haber fallado sin EMISOR_CORREO"
            except ValueError:
                pass

            os.environ["SMTP_PORT"] = "465"
            w3 = EmailWriter()
            assert w3.smtp_port == 465
        finally:
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    print("enviar_correo v1.0.0 OK")
