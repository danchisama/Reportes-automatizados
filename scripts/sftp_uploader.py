import paramiko
import os
import logging
from configparser import ConfigParser

class SFTPUploader:
    def __init__(self, config_path):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"No se encontró el archivo de configuración en: {config_path}")
            
        config = ConfigParser()
        config.read(config_path)
        
        self.host = config['SFTP']['host']
        self.port = int(config['SFTP'].get('port', 22))
        self.usuario = config['SFTP']['usuario']
        self.contrasena = config['SFTP']['contrasena']
        self.carpeta_destino = config['SFTP']['carpeta_destino']
        self.test_mode = config.getboolean('General', 'test_mode', fallback=False)

    def subir_archivo(self, ruta_archivo):
        if self.test_mode:
            print(f"[TEST MODE] Saltando subida SFTP para: {os.path.basename(ruta_archivo)}")
            logging.info(f"[TEST MODE] Saltando subida SFTP para: {ruta_archivo}")
            return True

        if not os.path.exists(ruta_archivo):
            logging.error(f"Archivo no encontrado para SFTP: {ruta_archivo}")
            return False

        try:
            transport = paramiko.Transport((self.host, self.port))
            transport.connect(username=self.usuario, password=self.contrasena)
            sftp = paramiko.SFTPClient.from_transport(transport)
            
            try:
                sftp.chdir(self.carpeta_destino)
                filename = os.path.basename(ruta_archivo)
                sftp.put(ruta_archivo, filename)
                logging.info(f"Éxito al subir {filename} a SFTP")
                print(f"[OK] Archivo subido a SFTP: {filename}")
                return True
            finally:
                sftp.close()
                transport.close()
        except Exception as e:
            logging.error(f"Error en SFTP: {e}")
            print(f"[ERROR] Error en SFTP: {e}")
            return False

if __name__ == "__main__":
    pass
