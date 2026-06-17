import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import base64
from io import BytesIO
import zipfile
import io
import re

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Análisis de Productos",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============ LISTA COMPLETA DE MARCAS ============
MARCAS_COMPLETAS = [
    'TRIUMPH BOARD', 'VASTEC', 'RHINOBOX', 'LENOVO', 'EXIN', 'M4X', 'KENYA TECHNOLOGY',
    'HP', 'MADI-TEK', 'INVESTMENT & BUSINESS SMART SBI', 'ADVANCE', 'QUI-TECH', 'TEXCOPER',
    'WIDETEK', 'IQTOUCH', 'LG', 'ONESCREEN', 'HUAWEI', 'INOTEC', 'DELL', 'I3', 'ASUS',
    'QUAMTU', 'KODAK', 'RICOH', 'SHARP', 'CIBER', 'HAO TECH', 'BROTHER', 'VIEWSONIC',
    'AVISION', 'SAMSUNG', 'ALLWIYA', 'GAMEMAX', 'DYNABOOK', 'HIPPOBOX', 'CONTEX', 'INNEX',
    'CTOUCH', 'HIKVISION', 'ZKT ECO', 'YEALINK', 'TEROS', 'SILVER VOLT', 'QOSOFT',
    'MIMIO', 'HAITECH', 'OPTOMA TECHNOLOGY INC', 'GROWTH HACK', 'MSI', 'XEROX', 'QOMO',
    'EPSON', 'CLEVERTOUCH', 'I2S INNOVATIVE IMAGING SOLUTIONS', 'IQ BOARD', 'GCS', 'COLORTRAC',
    'CANON', 'BOOKEYE', 'JFA TECHNOLOGY', 'AMC', 'MAXTIC', 'SANDISK', 'KINGSTON', 'ADATA', 'NEW KRAL'
]

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
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        transition: transform 0.3s;
        margin: 0.5rem 0;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        margin-top: 0.5rem;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #999;
        margin-top: 0.2rem;
    }
    .highlight-junio {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
    }
    .highlight-junio .big-number {
        font-size: 3rem;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 5px;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f77b4;
        color: white;
    }
    .info-box {
        background-color: #cce5ff;
        color: #004085;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #b8daff;
        margin: 1rem 0;
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

class ProductAnalyzer:
    """Clase principal para el analisis de productos"""
    
    def __init__(self):
        self.df = None
        self.records = []
        self.source_info = ""
        self.carga_completa = False
        
    def load_from_github(self, repo_owner, repo_name, branch="main", folder=""):
        """Carga TODOS los archivos JSON desde GitHub, incluyendo los que estan en ZIP"""
        self.records = []
        self.carga_completa = False
        
        # Construir URL de la API de GitHub
        if folder:
            api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{folder}"
        else:
            api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents"
        
        try:
            st.info(f"🔍 Buscando archivos en: {repo_owner}/{repo_name}")
            
            response = requests.get(api_url)
            if response.status_code != 200:
                st.error(f"❌ Error al acceder al repositorio: {response.status_code}")
                return None
            
            files = response.json()
            archivos_encontrados = []
            
            # Recorrer todos los archivos y carpetas
            for file in files:
                if file['type'] == 'file':
                    nombre = file['name'].lower()
                    if nombre.endswith('.json') or nombre.endswith('.zip'):
                        archivos_encontrados.append(file)
                elif file['type'] == 'dir':
                    sub_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file['path']}"
                    sub_response = requests.get(sub_url)
                    if sub_response.status_code == 200:
                        sub_files = sub_response.json()
                        for sub_file in sub_files:
                            if sub_file['type'] == 'file':
                                nombre = sub_file['name'].lower()
                                if nombre.endswith('.json') or nombre.endswith('.zip'):
                                    archivos_encontrados.append(sub_file)
            
            if not archivos_encontrados:
                st.warning("⚠️ No se encontraron archivos JSON o ZIP en el repositorio")
                return None
            
            st.success(f"📁 Encontrados {len(archivos_encontrados)} archivos (JSON y ZIP)")
            
            # Cargar cada archivo
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_records = 0
            archivos_procesados = 0
            
            for idx, file_info in enumerate(archivos_encontrados):
                nombre = file_info['name']
                status_text.text(f"📄 Procesando {idx+1}/{len(archivos_encontrados)}: {nombre}")
                
                try:
                    file_response = requests.get(file_info['download_url'])
                    if file_response.status_code == 200:
                        contenido = file_response.content
                        
                        if nombre.lower().endswith('.zip'):
                            registros_zip = self._procesar_zip(contenido, nombre)
                            if registros_zip:
                                self.records.extend(registros_zip)
                                total_records += len(registros_zip)
                                archivos_procesados += 1
                                st.info(f"📦 {nombre}: {len(registros_zip)} registros extraidos")
                        else:
                            data = json.loads(contenido)
                            if 'records' in data:
                                self.records.extend(data['records'])
                                total_records += len(data['records'])
                                archivos_procesados += 1
                                st.info(f"📄 {nombre}: {len(data['records'])} registros")
                                
                except Exception as e:
                    st.warning(f"⚠️ Error en {nombre}: {str(e)[:100]}")
                
                progress_bar.progress((idx + 1) / len(archivos_encontrados))
            
            status_text.text(f"✅ ¡Carga completada! {archivos_procesados} archivos, {total_records} registros")
            progress_bar.empty()
            
            if self.records:
                self.df = pd.DataFrame(self.records)
                self._process_data()
                self.carga_completa = True
                self.source_info = f"GitHub: {repo_owner}/{repo_name} ({archivos_procesados} archivos)"
                return self.df
            
            return None
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            return None
    
    def _procesar_zip(self, contenido_zip, nombre_zip):
        """Procesa un archivo ZIP y extrae todos los JSON que contiene"""
        registros = []
        
        try:
            with zipfile.ZipFile(io.BytesIO(contenido_zip)) as zip_file:
                for file_name in zip_file.namelist():
                    if file_name.lower().endswith('.json'):
                        try:
                            with zip_file.open(file_name) as json_file:
                                data = json.load(json_file)
                                if 'records' in data:
                                    registros.extend(data['records'])
                        except Exception as e:
                            pass
        except Exception as e:
            st.error(f"❌ Error al procesar ZIP {nombre_zip}: {str(e)}")
        
        return registros
    
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
        
        # Extraer marca usando la lista completa
        self.df['marca'] = self.df['descripcion'].apply(self._extract_brand)
        
        # Extraer categoria
        self.df['categoria'] = self.df['descripcion'].apply(self._extract_category)
        
        # Convertir precio
        self.df['precio_float'] = pd.to_numeric(self.df['precio'], errors='coerce')
        
        # Filtrar Junio 2026
        self.df['es_junio_2026'] = (self.df['fecha_publicacion_dt'].dt.year == 2026) & \
                                   (self.df['fecha_publicacion_dt'].dt.month == 6)
        
        # Extraer mes y año para filtros
        self.df['mes'] = self.df['fecha_publicacion_dt'].dt.month
        self.df['año'] = self.df['fecha_publicacion_dt'].dt.year
        self.df['mes_nombre'] = self.df['fecha_publicacion_dt'].dt.strftime('%B %Y')
    
    def _extract_brand(self, descripcion):
        """Extrae la marca de la descripcion usando la lista completa"""
        if not isinstance(descripcion, str):
            return "Desconocida"
        
        desc_upper = descripcion.upper()
        
        # Primero buscar marcas que contienen espacios (ej: "TRIUMPH BOARD")
        # Ordenar por longitud para que las más específicas coincidan primero
        marcas_ordenadas = sorted(MARCAS_COMPLETAS, key=len, reverse=True)
        
        for marca in marcas_ordenadas:
            if marca.upper() in desc_upper:
                return marca
        
        # Si no se encuentra ninguna marca, buscar palabras clave genéricas
        if "HP" in desc_upper:
            return "HP"
        elif "LENOVO" in desc_upper:
            return "LENOVO"
        elif "DELL" in desc_upper:
            return "DELL"
        elif "ASUS" in desc_upper:
            return "ASUS"
        elif "SAMSUNG" in desc_upper:
            return "SAMSUNG"
        elif "LG" in desc_upper:
            return "LG"
        
        return "Otra"
    
    def _extract_category(self, descripcion):
        """Extrae la categoria de la descripcion"""
        if not isinstance(descripcion, str):
            return "Desconocida"
        
        desc_upper = descripcion.upper()
        if "PORTATIL" in desc_upper or "NOTEBOOK" in desc_upper or "LAPTOP" in desc_upper:
            return "Portatil"
        elif "ESCRITORIO" in desc_upper or "DESKTOP" in desc_upper or "TORRE" in desc_upper:
            return "Escritorio"
        elif "SERVIDOR" in desc_upper or "SERVER" in desc_upper:
            return "Servidor"
        elif "MONITOR" in desc_upper or "PANTALLA" in desc_upper:
            return "Monitor"
        elif "IMPRESORA" in desc_upper or "PRINTER" in desc_upper:
            return "Impresora"
        else:
            return "Otro"
    
    def get_stats(self, df_filtered=None):
        """Obtiene estadisticas del DataFrame filtrado"""
        if df_filtered is None:
            df_filtered = self.df
        
        if df_filtered is None or df_filtered.empty:
            return None
        
        stats = {
            'total': len(df_filtered),
            'por_marca': df_filtered['marca'].value_counts().to_dict(),
            'por_categoria': df_filtered['categoria'].value_counts().to_dict(),
            'por_estado': df_filtered['estado_ficha'].value_counts().to_dict(),
            'precio_promedio': df_filtered['precio_float'].mean(),
            'precio_min': df_filtered['precio_float'].min(),
            'precio_max': df_filtered['precio_float'].max(),
            'precio_mediana': df_filtered['precio_float'].median(),
            'dataframe': df_filtered
        }
        
        return stats

def mostrar_filtros(df):
    """Muestra los filtros interactivos y devuelve el DataFrame filtrado"""
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros Interactivos")
    
    df_filtrado = df.copy()
    
    # Filtro por categoria
    categorias = ['Todas'] + sorted(df['categoria'].unique().tolist())
    categoria_seleccionada = st.sidebar.selectbox("📂 Filtrar por Categoria:", categorias)
    
    if categoria_seleccionada != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['categoria'] == categoria_seleccionada]
    
    # Filtro por marca
    marcas = ['Todas'] + sorted(df['marca'].unique().tolist())
    marca_seleccionada = st.sidebar.selectbox("🏷️ Filtrar por Marca:", marcas)
    
    if marca_seleccionada != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['marca'] == marca_seleccionada]
    
    # Filtro por estado
    estados = ['Todos'] + sorted(df['estado_ficha'].unique().tolist())
    estado_seleccionado = st.sidebar.selectbox("📊 Filtrar por Estado:", estados)
    
    if estado_seleccionado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['estado_ficha'] == estado_seleccionado]
    
    # Mostrar resumen de filtros
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**📊 Registros mostrados:** {len(df_filtrado)}")
    
    if len(df_filtrado) < len(df):
        porcentaje = (len(df_filtrado) / len(df)) * 100
        st.sidebar.markdown(f"**Filtrados:** {porcentaje:.1f}% del total")
    
    return df_filtrado

def mostrar_tabla_productos(df, titulo):
    """Muestra la tabla de productos con filtros"""
    st.subheader(titulo)
    
    columnas = ['ID_ProductoOfertado', 'descripcion', 'marca', 'categoria', 
                'precio', 'estado_ficha', 'fecha_publicacion']
    
    df_show = df[columnas].copy()
    df_show['descripcion'] = df_show['descripcion'].str[:150] + '...'
    df_show.columns = ['ID', 'Descripcion', 'Marca', 'Categoria', 
                       'Precio (USD)', 'Estado', 'Fecha Publicacion']
    
    st.dataframe(df_show, use_container_width=True, height=500)

def main():
    st.markdown('<h1 class="main-header">📊 Dashboard de Analisis de Productos</h1>', unsafe_allow_html=True)
    
    # Inicializar el analizador
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = ProductAnalyzer()
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuracion")
        
        st.markdown("""
        <div class="info-box">
        <strong>📌 Soporte para ZIP</strong><br>
        El sistema detecta y extrae automaticamente<br>
        archivos JSON desde dentro de ZIP
        </div>
        """, unsafe_allow_html=True)
        
        repo_owner = st.text_input("👤 Owner del repositorio:", value="StalinHA")
        repo_name = st.text_input("📁 Nombre del repositorio:", value="fichadjudicados")
        branch = st.text_input("🌿 Rama:", value="main")
        folder = st.text_input("📂 Carpeta (opcional):", value="")
        
        if st.button("🚀 Cargar TODOS los JSON (incluye ZIP)", use_container_width=True, type="primary"):
            with st.spinner("Cargando archivos desde GitHub..."):
                df = st.session_state.analyzer.load_from_github(repo_owner, repo_name, branch, folder)
                if df is not None and not df.empty:
                    st.success(f"✅ {len(df)} registros cargados exitosamente!")
                    st.rerun()
                else:
                    st.error("❌ No se pudieron cargar los datos")
        
        st.divider()
        
        if st.session_state.analyzer.carga_completa:
            st.success(f"✅ Datos cargados: {len(st.session_state.analyzer.df)} registros")
            st.info(f"📂 Fuente: {st.session_state.analyzer.source_info}")
    
    analyzer = st.session_state.analyzer
    
    if not analyzer.carga_completa or analyzer.df is None or analyzer.df.empty:
        st.info("📁 Haz clic en 'Cargar TODOS los JSON (incluye ZIP)' en el panel izquierdo")
        
        with st.expander("💡 Guia de uso", expanded=True):
            st.markdown("""
            ### 🚀 Como usar este dashboard:
            
            1. Configura tu repositorio en el panel izquierdo
            2. Haz clic en "Cargar TODOS los JSON (incluye ZIP)"
            3. El sistema buscara y cargara automaticamente:
               - Archivos .json directos
               - Archivos .zip que contengan .json
            
            ### 📂 Estructura de archivos soportada:
