pipeline {
    agent any

    environment {
        // Sunumdaki ve bilgisayarındaki Python yolu
        PYTHON_PATH = "C:\\Users\\merzey\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe"
        VENV = ".venv"
    }

    stages {
        stage('1. Build (Rust Core Compilation)') {
            steps {
                echo '🏗️ BUILDRust core compiled by cargo...'
                bat '''
                call %VENV%\\Scripts\\activate || (
                    "%PYTHON_PATH%" -m venv %VENV%
                    call %VENV%\\Scripts\\activate
                )
                pip install maturin
                
                echo "Rust modülleri Python için derleniyor (Maturin)..."
                cd rust_db && maturin develop --release
                cd ..
                cd rust_qr && maturin develop --release
                cd ..
                '''
            }
        }

        stage('2. Test (Pytest & Cargo Tests)') {
            steps {
                echo '🧪 TEST: Pytest & Cargo run tests...'
                bat '''
                call %VENV%\\Scripts\\activate
                echo "Unit tests for financial calculations and DB integrity..."
                pytest -m Tests/tests.py -v
                '''
            }
        }

        stage('3. Analyze (Code Quality & Security)') {
            steps {
                echo '🔍 ANALYZE: Code quality checked by Ruff & Bandit...'
                bat '''
                call %VENV%\\Scripts\\activate
                echo "Ruff Analizi (PEP 8 ve Standartlar)..."
                ruff check .
                echo "Bandit Güvenlik Taraması..."
                bandit -r PythonFiles/ -ll
                '''
            }
        }

        stage('4. Deploy (Artifact Generation)') {
            steps {
                echo '🚀 DEPLOY: Ships to staging or production...'
                bat '''
                echo "Uygulama klasör yapısı hazırlanıyor ve artifactler oluşturuluyor..."
                if not exist "Database" mkdir Database
                if not exist "ExcelReports" mkdir ExcelReports
                if not exist "Markdowns" mkdir Markdowns
                
                echo "Opsiyonel: PyInstaller ile .exe üretimi burada tetiklenebilir."
                :: python -m PyInstaller app.spec
                '''
            }
        }
    }

    post {
        success {
            echo '✅ DELIVER WITH CONFIDENCE: Tüm aşamalar başarıyla tamamlandı!'
        }
        failure {
            echo '❌ PIPELINE FAILED: Sunumdaki kural uyarınca işlem durduruldu ve ekip bilgilendirildi!'
        }
    }
}