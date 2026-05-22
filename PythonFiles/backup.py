import os
import zipfile
import datetime
import sqlite3
import shutil
import tempfile

# ============================================================================
# YEREL YEDEKLEME YÖNETİCİSİ
# ============================================================================


class LocalBackupManager:
    def __init__(self, database_folder="Database"):
        """
        Yedekleme yöneticisi başlatılır.

        Args:
            database_folder (str): Yedeklenecek kaynak klasörün yolu. Varsayılan: 'Database'
        """
        self.database_folder = os.path.abspath(database_folder)

    def get_default_filename(self):
        """
        Tarih ve saat içeren varsayılan bir yedekleme dosya adı oluşturur.
        Örnek: Excellent_Backup_2023-10-27_14-30-00.zip
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"Excellent_Backup_{timestamp}.zip"

    def create_backup(self, destination_path):
        """
        Database klasörünü belirtilen yola zip olarak yedekler.

        Args:
            destination_path (str): Zip dosyasının oluşturulacağı tam dosya yolu.

        Returns:
            tuple: (başarı_durumu (bool), mesaj (str))
        """
        if not os.path.exists(self.database_folder):
            return False, f"Kaynak klasör bulunamadı: {self.database_folder}"

        try:
            # Hedef klasörün var olduğundan emin ol (eğer bir klasör yolu verildiyse)
            dest_dir = os.path.dirname(destination_path)
            if dest_dir and not os.path.exists(dest_dir):
                os.makedirs(dest_dir)

            # Zip dosyasını oluştur
            with zipfile.ZipFile(destination_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Klasör içindeki tüm dosyaları gez
                for root, dirs, files in os.walk(self.database_folder):
                    for file in files:
                        file_path = os.path.join(root, file)

                        # Zip içindeki dosya yolu (Database klasörünü kök alarak)
                        # os.path.relpath kullanarak tam yoldan göreceli yola çeviriyoruz
                        # Böylece zip içinde "Database/dosya.db" gibi görünecek
                        parent_dir = os.path.dirname(self.database_folder)
                        arcname = os.path.relpath(file_path, parent_dir)

                        zipf.write(file_path, arcname)

            return True, f"Yedekleme başarıyla oluşturuldu:\n{destination_path}"

        except Exception as e:
            return False, f"Yedekleme sırasında hata oluştu: {str(e)}"

    def restore_backup(self, zip_path):
        """
        Zip yedek dosyasından veritabanını geri yükler.
        Canlı SQLite bağlantılarıyla çakışmamak için Python'un
        sqlite3.backup() API'sini (SQLite Online Backup API) kullanır.

        Args:
            zip_path (str): Yedek zip dosyasının tam yolu

        Returns:
            tuple: (başarı_durumu (bool), mesaj (str))
        """
        if not os.path.exists(zip_path):
            return False, f"Yedek dosyası bulunamadı: {zip_path}"

        if not zipfile.is_zipfile(zip_path):
            return False, "Geçersiz yedek dosyası (zip formatında değil)"

        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp(prefix="excellent_restore_")
            with zipfile.ZipFile(zip_path, "r") as zipf:
                zipf.extractall(temp_dir)

            # Zip içinde "Database/" klasörü olup olmadığını kontrol et
            extracted_db_folder = os.path.join(temp_dir, "Database")
            if not os.path.exists(extracted_db_folder):
                return False, "Geçersiz yedek: zip içinde 'Database' klasörü bulunamadı"

            db_files = ["invoices.db", "settings.db", "history.db"]
            found_any = False

            for db_file in db_files:
                src_path = os.path.join(extracted_db_folder, db_file)
                dst_path = os.path.join(self.database_folder, db_file)

                if not os.path.exists(src_path):
                    continue

                found_any = True
                # Hedef klasörün var olduğundan emin ol
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)

                # SQLite Online Backup API: src -> dst (canlı bağlantıyla güvenli)
                src_conn = sqlite3.connect(src_path)
                dst_conn = sqlite3.connect(dst_path)
                try:
                    src_conn.backup(dst_conn)
                    dst_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    dst_conn.commit()
                finally:
                    dst_conn.close()
                    src_conn.close()

            if not found_any:
                return False, "Yedek dosyasında geçerli veritabanı dosyası bulunamadı"

            return True, "Geri yükleme başarıyla tamamlandı"

        except Exception as e:
            return False, f"Geri yükleme sırasında hata oluştu: {str(e)}"
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # Test bloğu
    manager = LocalBackupManager()
    default_name = manager.get_default_filename()
    # print(f"Varsayılan isim: {default_name}")

    # Test için masaüstüne kaydetme örneği (Yorum satırı)
    # desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    # test_path = os.path.join(desktop, default_name)
    # success, msg = manager.create_backup(test_path)
    # print(msg)
