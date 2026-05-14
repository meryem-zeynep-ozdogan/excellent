pipeline {
    agent any

    environment {
        // Python sanal ortam dizini
        VENV = ".venv"
    }

    stages {
        stage('0. Hazırlık ve Kurulum (Setup)') {
            steps {
                echo 'Sanal ortam kuruluyor ve kütüphaneler yükleniyor...'
                bat '''
                python -m venv %VENV%
                call %VENV%\\Scripts\\activate
                pip install -r requirements.txt
                pip install ruff bandit pytest pytest-benchmark pytest-bdd pydantic
                rustc --version
                cargo --version
                '''
            }
        }

        stage('1. Statik Kod & Güvenlik (Linting & Security)') {
            steps {
                echo 'Ruff ile kod standartlari ve Bandit ile güvenlik taraniyor...'
                bat '''
                call %VENV%\\Scripts\\activate
                echo "Ruff Analizi Başliyor..."
                ruff check .
                echo "Bandit Güvenlik Taramasi Başliyor..."
                bandit -r PythonFiles/ -ll
                '''
            }
        }

        stage('2. İş Mantığı ve Veritabanı Kalkanı (Unit Tests)') {
            steps {
                echo 'Kerem in PyTest veritabanı ve sınır değer testleri çalışıyor...'
                bat '''
                call %VENV%\\Scripts\\activate
                pytest test_database.py test_partitions.py -v
                '''
            }
        }

        stage('3. Frontend-Backend Şema Sözleşmesi (Contract Tests)') {
            steps {
                echo 'TL vs TRY gibi uyumsuzluklar için veri modeli doğrulanıyor...'
                bat '''
                call %VENV%\\Scripts\\activate
                pytest test_schema.py -v
                '''
            }
        }

        stage('4. UI/UX Uçtan Uca Testler (E2E Tests)') {
            steps {
                echo 'Flet arayüz davranışları test ediliyor...'
                bat '''
                call %VENV%\\Scripts\\activate
                pytest test_ui_workflows.py -v
                '''
            }
        }

        stage('5. Performans ve Hız Bariyeri (Benchmarks)') {
            steps {
                echo 'Fatura kayıt hızı ve Rust QR okuma modülü ölçülüyor...'
                bat '''
                call %VENV%\\Scripts\\activate
                echo "Python Benchmark Testleri:"
                pytest test_perf.py --benchmark-only --benchmark-fail-fast
                echo "Rust QR Benchmark Testleri:"
                cargo bench
                '''
            }
        }
    }

    post {
        success {
            echo '✅ HARİKA! Tüm testler başarıyla geçti. Kod Master dalına birleştirilmeye hazır.'
        }
        failure {
            echo '❌ HATA! Pipeline patladı. Lütfen konsol çıktılarını inceleyip kodu düzeltin.'
        }
        always {
            echo 'Temizlik yapılıyor...'
            // Gerekirse test veritabanlarını temizleme komutları buraya eklenebilir
        }
    }
}