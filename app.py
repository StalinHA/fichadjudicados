import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import requests
import base64
from io import StringIO
import tempfile
from pathlib import Path
import urllib.parse

# Configuración de la página - DEBE SER LA PRIMERA INSTRUCCIÓN DE STREAMLIT
st.set_page_config(
    page_title="Dashboard de Análisis de Productos",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #f0f2f6, #ffffff);
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        transition: transform 0.3s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
    }
    .github-info {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .stButton > button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #135a8a;
        color: white;
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class GitHubLoader:
    """Clase para manejar la carga de archivos desde GitHub"""
    
    def __init__(self):
        self.api_base = "https://api.github.com"
        self.raw_base = "https://raw.githubusercontent.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        # Configurar token si existe en secrets
        if 'github_token' in st.secrets:
            self.headers["Authorization"] = f"token {st.secrets.github_token}"
    
    def get_repo_contents(self, repo_url, path=""):
        """Obtiene el contenido de un repositorio de GitHub"""
        # Extraer owner y repo de la URL
        repo_path = self._extract_repo_path(repo_url)
        if not repo_path:
            return None
        
        # Construir URL de la API
        if path:
            api_url = f"{self.api_base}/repos/{repo_path}/contents/{path}"
        else:
            api_url = f"{self.api_base}/repos/{repo_path}/contents"
        
        try:
            response = requests.get(api_url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                st.warning(f"No se encontró el repositorio o la ruta. Verifica que el repositorio sea público.")
                return None
            else:
                st.error(f"Error al acceder al repositorio: {response.status_code}")
                return None
        except Exception as e:
            st.error(f"Error de conexión: {str(e)}")
            return None
    
    def _extract_repo_path(self, repo_url):
        """Extrae el path del repositorio de la URL"""
        if "github.com" in repo_url:
            # Limpiar URL
            repo_url = repo_url.replace("https://", "").replace("http://", "")
            parts = repo_url.split("/")
            if len(parts) >= 3:
                owner = parts[1]
                repo = parts[2].replace(".git", "")
                return f"{owner}/{repo}"
        return None
    
    def get_file_content_raw(self, repo_url, file_path):
        """Obtiene el contenido de un archivo usando raw.githubusercontent.com"""
        repo_path = self._extract_repo_path(repo_url)
        if not repo_path:
            return None
        
        # Usar el formato raw
        raw_url = f"{self.raw_base}/{repo_path}/main/{file_path}"
        
        try:
            response = requests.get(raw_url)
            if response.status_code == 200:
                return response.text
            else:
                # Intentar con 'master' en lugar de 'main'
                raw_url = f"{self.raw_base}/{repo_path}/master/{file_path}"
                response = requests.get(raw_url)
                if response.status_code == 200:
                    return response.text
            return None
        except Exception as e:
            return None
    
    def list_json_files(self, repo_url, path=""):
        """Lista todos los archivos JSON en un repositorio"""
        contents = self.get_repo_contents(repo_url, path)
        json_files = []
        
        if contents and isinstance(contents, list):
            for item in contents:
                if item['type'] == 'file' and item['name'].endswith('.json'):
                    json_files.append({
                        'name': item['name'],
                        'path': item['path'],
                        'download_url': item['download_url']
                    })
                elif item['type'] == 'dir':
                    # Buscar recursivamente en subdirectorios
                    sub_contents = self.get_repo_contents(repo_url, item['path'])
                    if sub_contents and isinstance(sub_contents, list):
                        for sub_item in sub_contents:
                            if sub_item['type'] == 'file' and sub_item['name'].endswith('.json'):
                                json_files.append({
                                    'name': sub_item['name'],
                                    'path': sub_item['path'],
                                    'download_url': sub_item['download_url']
                                })
        
        return json_files
    
    def load_json_from_url(self, url):
        """Carga un archivo JSON desde una URL"""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            st.error(f"Error al cargar {url}: {str(e)}")
            return None

class ProductAnalyzer:
    def __init__(self):
        self.df = None
        self.records = []
        self.github_loader = GitHubLoader()
        self.source_info = ""
        
    def load_from_github_repo(self, repo_url, path=""):
        """Carga todos los archivos JSON desde un repositorio de GitHub"""
        all_records = []
        
        st.info(f"🔍 Buscando archivos JSON en: {repo_url}")
        
        json_files = self.github_loader.list_json_files(repo_url, path)
        
        if not json_files:
            st.warning("No se encontraron archivos JSON en el repositorio")
            return None
        
        st.success(f"📁 Encontrados {len(json_files)} archivos JSON")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, file_info in enumerate(json_files):
            status_text.text(f"Cargando archivo {idx+1} de {len(json_files)}: {file_info['name']}")
            
            try:
                data = self.github_loader.load_json_from_url(file_info['download_url'])
                if data and 'records' in data:
                    all_records.extend(data['records'])
            except Exception as e:
                st.error(f"Error al cargar {file_info['name']}: {str(e)}")
            
            progress_bar.progress((idx + 1) / len(json_files))
        
        status_text.text(f"✅ ¡Carga completada!")
        progress_bar.empty()
        
        self.records = all_records
        self.source_info = f"GitHub: {repo_url}"
        
        if all_records:
            self.df = pd.DataFrame(all_records)
            self._process_data()
            return self.df
        else:
            st.warning("No se encontraron registros en los archivos")
            return None
    
    def load_from_github_urls(self, urls):
        """Carga archivos JSON desde URLs específicas"""
        all_records = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, url in enumerate(urls):
            status_text.text(f"Cargando archivo {idx+1} de {len(urls)}")
            
            try:
                data = self.github_loader.load_json_from_url(url)
                if data and 'records' in data:
                    all_records.extend(data['records'])
            except Exception as e:
                st.error(f"Error al cargar {url}: {str(e)}")
            
            progress_bar.progress((idx + 1) / len(urls))
        
        status_text.text(f"✅ ¡Carga completada!")
        progress_bar.empty()
        
        self.records = all_records
        self.source_info = f"GitHub URLs ({len(urls)} archivos)"
        
        if all_records:
            self.df = pd.DataFrame(all_records)
            self._process_data()
            return self.df
        else:
            st.warning("No se encontraron registros en los archivos")
            return None
    
    def _process_data(self):
        """Procesa y transforma los datos"""
        if self.df is None or self.df.empty:
            return
            
        # Convertir fechas
        self.df['fecha_registro_dt'] = pd.to_datetime(
            self.df['fecha_registro'], 
            format='%d/%m/%Y %I:%M:%S %p',
            errors='coerce'
        )
        self.df['fecha_publicacion_dt'] = pd.to_datetime(
            self.df['fecha_publicacion'], 
            format='%d/%m/%Y %I:%M:%S %p',
            errors='coerce'
        )
        self.df['fecha_adjudicacion_dt'] = pd.to_datetime(
            self.df['fecha_adjudicacion'], 
            format='%d/%m/%Y %I:%M:%S %p',
            errors='coerce'
        )
        
        # Extraer marca de la descripción
        self.df['marca'] = self.df['descripcion'].apply(self._extract_brand)
        
        # Extraer categoría de la descripción
        self.df['categoria'] = self.df['descripcion'].apply(self._extract_category)
        
        # Convertir precio a float
        self.df['precio_float'] = pd.to_numeric(self.df['precio'], errors='coerce')
        
        # Filtrar registros de Junio 2026
        self.df['es_junio_2026'] = (self.df['fecha_publicacion_dt'].dt.year == 2026) & \
                                   (self.df['fecha_publicacion_dt'].dt.month == 6)
    
    def _extract_brand(self, descripcion):
        """Extrae la marca de la descripción"""
        if not isinstance(descripcion, str):
            return "Desconocida"
        
        brands = {
            'HP': ['HP', 'Hewlett-Packard'],
            'LENOVO': ['LENOVO', 'ThinkPad'],
            'DELL': ['DELL', 'Latitude', 'Precision'],
            'ASUS': ['ASUS'],
            'ACER': ['ACER'],
            'MADI-TEK': ['MADI-TEK'],
            'CYBER WORKPAD': ['CYBER WORKPAD']
        }
        
        desc_upper = descripcion.upper()
        for brand, keywords in brands.items():
            if any(keyword.upper() in desc_upper for keyword in keywords):
                return brand.capitalize()
        
        return "Otra"
    
    def _extract_category(self, descripcion):
        """Extrae la categoría de la descripción"""
        if not isinstance(descripcion, str):
            return "Desconocida"
        
        if "PORTATIL" in descripcion.upper() or "NOTEBOOK" in descripcion.upper():
            return "Portátil"
        elif "ESCRITORIO" in descripcion.upper() or "DESKTOP" in descripcion.upper():
            return "Escritorio"
        elif "SERVIDOR" in descripcion.upper() or "SERVER" in descripcion.upper():
            return "Servidor"
        else:
            return "Otro"
    
    def get_monthly_stats(self):
        """Obtiene estadísticas del mes de Junio 2026"""
        if self.df is None or self.df.empty:
            return None
            
        df_junio = self.df[self.df['es_junio_2026'] == True]
        
        if df_junio.empty:
            return {
                'total': 0,
                'por_marca': {},
                'por_categoria': {},
                'por_estado': {},
                'precio_promedio': 0,
                'precio_min': 0,
                'precio_max': 0
            }
        
        stats = {
            'total': len(df_junio),
            'por_marca': df_junio['marca'].value_counts().to_dict(),
            'por_categoria': df_junio['categoria'].value_counts().to_dict(),
            'por_estado': df_junio['estado_ficha'].value_counts().to_dict(),
            'precio_promedio': df_junio['precio_float'].mean(),
            'precio_min': df_junio['precio_float'].min(),
            'precio_max': df_junio['precio_float'].max(),
            'dataframe': df_junio
        }
        
        return stats

def create_dashboard():
    st.markdown('<h1 class="main-header">📊 Dashboard de Análisis de Productos</h1>', unsafe_allow_html=True)
    
    # Inicializar el analizador
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = ProductAnalyzer()
    
    # Sidebar - Configuración
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # Mostrar opciones de carga
        load_method = st.radio(
            "Selecciona el método de carga:",
            ["🌐 GitHub - Repositorio", "🌐 GitHub - URLs específicas"]
        )
        
        if load_method == "🌐 GitHub - Repositorio":
            st.markdown("""
            <div class="github-info">
            <strong>📌 Instrucciones:</strong><br>
            Ingresa la URL del repositorio y opcionalmente una subcarpeta.<br>
            El sistema buscará automáticamente todos los archivos .json
            </div>
            """, unsafe_allow_html=True)
            
            # Configuración por defecto para tu repositorio
            default_repo = "https://github.com/StalinHA/fichadjudicados"
            
            repo_url = st.text_input(
                "URL del repositorio:",
                value=default_repo,
                placeholder="https://github.com/usuario/repo"
            )
            
            subpath = st.text_input(
                "Subcarpeta (opcional):",
                placeholder="data/json/"
            )
            
            if st.button("🔍 Buscar y Cargar JSON", use_container_width=True):
                if repo_url:
                    with st.spinner("Cargando archivos desde GitHub..."):
                        df = st.session_state.analyzer.load_from_github_repo(repo_url, subpath)
                        if df is not None and not df.empty:
                            st.success(f"✅ {len(df)} registros cargados exitosamente!")
                            st.rerun()
                    st.rerun()
                else:
                    st.warning("Por favor, ingresa la URL de tu repositorio")
        
        else:  # URLs específicas
            st.markdown("""
            <div class="github-info">
            <strong>📌 Instrucciones:</strong><br>
            Ingresa las URLs directas de los archivos JSON.<br>
            Usa el formato: https://raw.githubusercontent.com/usuario/repo/rama/archivo.json
            </div>
            """, unsafe_allow_html=True)
            
            urls_text = st.text_area(
                "URLs de archivos JSON (una por línea):",
                placeholder="https://raw.githubusercontent.com/StalinHA/fichadjudicados/main/archivo1.json\nhttps://raw.githubusercontent.com/StalinHA/fichadjudicados/main/archivo2.json",
                height=150
            )
            
            if st.button("📥 Cargar desde URLs", use_container_width=True):
                if urls_text:
                    urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
                    with st.spinner(f"Cargando {len(urls)} archivos..."):
                        df = st.session_state.analyzer.load_from_github_urls(urls)
                        if df is not None and not df.empty:
                            st.success(f"✅ {len(df)} registros cargados exitosamente!")
                            st.rerun()
                    st.rerun()
                else:
                    st.warning("Por favor, ingresa al menos una URL")
        
        st.divider()
        
        # Mostrar información de carga
        if st.session_state.analyzer.df is not None and not st.session_state.analyzer.df.empty:
            st.metric("📊 Total de registros", len(st.session_state.analyzer.df))
            
            # Filtros adicionales en sidebar
            st.divider()
            st.header("🔍 Filtros rápidos")
            
            # Filtro por marca
            marcas = ['Todas'] + sorted(st.session_state.analyzer.df['marca'].unique().tolist())
            marca_seleccionada = st.selectbox("🏷️ Filtrar por Marca:", marcas)
            
            # Filtro por categoría
            categorias = ['Todas'] + sorted(st.session_state.analyzer.df['categoria'].unique().tolist())
            categoria_seleccionada = st.selectbox("📂 Filtrar por Categoría:", categorias)
            
            return marca_seleccionada, categoria_seleccionada
    
    return None, None

def main():
    marca_seleccionada, categoria_seleccionada = create_dashboard()
    
    analyzer = st.session_state.analyzer
    
    if analyzer.df is None or analyzer.df.empty:
        st.info("📁 Por favor, carga archivos JSON para comenzar el análisis")
        
        # Mostrar ejemplo de uso
        with st.expander("💡 Guía de uso", expanded=True):
            st.markdown("""
            ### 🚀 Cómo usar este dashboard:
            
            #### Opción 1: Cargar desde repositorio GitHub (Recomendado)
            1. En el panel izquierdo, selecciona "🌐 GitHub - Repositorio"
            2. La URL de tu repositorio ya está preconfigurada: `https://github.com/StalinHA/fichadjudicados`
            3. Haz clic en "🔍 Buscar y Cargar JSON"
            
            #### Opción 2: Cargar desde URLs específicas
            1. En el panel izquierdo, selecciona "🌐 GitHub - URLs específicas"
            2. Ingresa las URLs directas de tus archivos JSON (una por línea)
            3. Haz clic en "📥 Cargar desde URLs"
            
            ### 📋 Formato de archivos JSON:
            ```json
            {
                "records": [
                    {
                        "ID_ProductoOfertado": "12345",
                        "descripcion": "COMPUTADORA PORTATIL...",
                        "precio": "1800.00",
                        "fecha_registro": "09/06/2026 11:35:03 p. m.",
                        "fecha_publicacion": "13/09/2025 12:00:00 a. m."
                    }
                ]
            }