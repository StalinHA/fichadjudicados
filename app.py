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
    .estado-activo {
        background-color: #28a745;
        color: white;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        display: inline-block;
        font-weight: bold;
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
        
        # Extraer marca y categoria
        self.df['marca'] = self.df['descripcion'].apply(self._extract_brand)
        self.df['categoria'] = self.df['descripcion'].apply(self._extract_category)
        self.df['precio_float'] = pd.to_numeric(self.df['precio'], errors='coerce')
        
        # ============ ESTADO ACTIVO ============
        # Una ficha está ACTIVA si estado_ficha = "OFERTADA" Y estado_oferta = "VIGENTE"
        self.df['es_activo'] = (self.df['estado_ficha'] == 'OFERTADA') & (self.df['estado_oferta'] == 'VIGENTE')
        
        # Filtrar Junio 2026
        self.df['es_junio_2026'] = (self.df['fecha_publicacion_dt'].dt.year == 2026) & \
                                   (self.df['fecha_publicacion_dt'].dt.month == 6)
        
        # Extraer año y mes para análisis de fechas
        self.df['año_publicacion'] = self.df['fecha_publicacion_dt'].dt.year
        self.df['mes_publicacion'] = self.df['fecha_publicacion_dt'].dt.month
        self.df['año_mes_publicacion'] = self.df['fecha_publicacion_dt'].dt.strftime('%Y-%m')
        self.df['mes_nombre_publicacion'] = self.df['fecha_publicacion_dt'].dt.strftime('%B %Y')
    
    def _extract_brand(self, descripcion):
        """Extrae la marca de la descripcion usando la lista completa"""
        if not isinstance(descripcion, str):
            return "Desconocida"
        
        desc_upper = descripcion.upper()
        marcas_ordenadas = sorted(MARCAS_COMPLETAS, key=len, reverse=True)
        
        for marca in marcas_ordenadas:
            if marca.upper() in desc_upper:
                return marca
        
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
            'por_estado_oferta': df_filtered['estado_oferta'].value_counts().to_dict(),
            'activos': df_filtered['es_activo'].sum(),
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
    estados = ['Todos', 'Activos (OFERTADA + VIGENTE)'] + sorted(df['estado_ficha'].unique().tolist())
    estado_seleccionado = st.sidebar.selectbox("📊 Filtrar por Estado:", estados)
    
    if estado_seleccionado == 'Activos (OFERTADA + VIGENTE)':
        df_filtrado = df_filtrado[df_filtrado['es_activo'] == True]
    elif estado_seleccionado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['estado_ficha'] == estado_seleccionado]
    
    # Filtro por rango de fechas
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Filtro por Fecha de Publicación")
    
    if not df['fecha_publicacion_dt'].isna().all():
        fecha_min = df['fecha_publicacion_dt'].min().date()
        fecha_max = df['fecha_publicacion_dt'].max().date()
        
        fecha_inicio = st.sidebar.date_input(
            "Fecha Inicio:",
            value=fecha_min,
            min_value=fecha_min,
            max_value=fecha_max
        )
        
        fecha_fin = st.sidebar.date_input(
            "Fecha Fin:",
            value=fecha_max,
            min_value=fecha_min,
            max_value=fecha_max
        )
        
        df_filtrado = df_filtrado[
            (df_filtrado['fecha_publicacion_dt'].dt.date >= fecha_inicio) & 
            (df_filtrado['fecha_publicacion_dt'].dt.date <= fecha_fin)
        ]
    
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
                'precio', 'estado_ficha', 'estado_oferta', 'fecha_publicacion']
    
    df_show = df[columnas].copy()
    df_show['descripcion'] = df_show['descripcion'].str[:150] + '...'
    df_show.columns = ['ID', 'Descripcion', 'Marca', 'Categoria', 
                       'Precio (USD)', 'Estado Ficha', 'Estado Oferta', 'Fecha Publicacion']
    
    st.dataframe(df_show, use_container_width=True, height=500)

def mostrar_analisis_fechas(df):
    """Muestra el análisis de fechas por año y mes"""
    st.subheader("📅 Análisis de Productos por Fecha de Publicación")
    
    # Crear columnas para año y mes
    df_fechas = df.copy()
    df_fechas['año'] = df_fechas['fecha_publicacion_dt'].dt.year
    df_fechas['mes'] = df_fechas['fecha_publicacion_dt'].dt.month
    df_fechas['mes_nombre'] = df_fechas['fecha_publicacion_dt'].dt.strftime('%B')
    
    # Agrupar por año y mes
    df_agrupado = df_fechas.groupby(['año', 'mes', 'mes_nombre']).agg({
        'ID_ProductoOfertado': 'count',
        'precio_float': ['mean', 'min', 'max'],
        'es_activo': 'sum'
    }).reset_index()
    
    df_agrupado.columns = ['Año', 'Mes', 'Mes Nombre', 'Total Productos', 
                           'Precio Promedio', 'Precio Min', 'Precio Max', 'Activos']
    
    # Mostrar tabla
    st.dataframe(df_agrupado, use_container_width=True)
    
    # Gráfico de evolución por mes
    st.subheader("📈 Evolución de Productos por Mes")
    
    fig = px.line(df_agrupado, x='Mes Nombre', y='Total Productos',
                  title='Cantidad de Productos por Mes',
                  labels={'Total Productos': 'Cantidad', 'Mes Nombre': 'Mes'},
                  markers=True)
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de barras por año
    st.subheader("📊 Productos por Año")
    
    df_anios = df_agrupado.groupby('Año').agg({'Total Productos': 'sum'}).reset_index()
    
    fig = px.bar(df_anios, x='Año', y='Total Productos',
                 title='Productos por Año',
                 color='Año', text='Total Productos')
    fig.update_traces(textposition='outside')
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de distribución por año y mes (heatmap)
    st.subheader("🗓️ Mapa de Calor - Productos por Año y Mes")
    
    pivot_df = df_agrupado.pivot_table(
        index='Año', 
        columns='Mes', 
        values='Total Productos',
        fill_value=0
    )
    
    # Renombrar meses
    meses_nombres = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
                     7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
    pivot_df.columns = [meses_nombres.get(m, m) for m in pivot_df.columns]
    
    fig = px.imshow(pivot_df, 
                    title='Mapa de Calor - Productos por Año y Mes',
                    labels=dict(x="Mes", y="Año", color="Cantidad"),
                    color_continuous_scale='Viridis',
                    aspect="auto")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def main():
    st.markdown('<h1 class="main-header">📊 Dashboard de Analisis de Productos</h1>', unsafe_allow_html=True)
    
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = ProductAnalyzer()
    
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
        return
    
    df = analyzer.df
    df_filtrado = mostrar_filtros(df)
    stats = analyzer.get_stats(df_filtrado)
    
    if stats is None or stats['total'] == 0:
        st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados")
        return
    
    # ============ SECCION JUNIO 2026 ============
    df_junio = df[df['es_junio_2026'] == True]
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; margin: 1rem 0;">
        <h2 style="color: white; text-align: center; margin: 0;">📊 RESULTADOS DE JUNIO 2026</h2>
    </div>
    """, unsafe_allow_html=True)
    
    if not df_junio.empty:
        stats_junio = analyzer.get_stats(df_junio)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                <div class="metric-value" style="color: white;">{stats_junio['total']}</div>
                <div class="metric-label" style="color: white;">📦 Fichas Nuevas</div>
                <div class="metric-sub" style="color: rgba(255,255,255,0.8);">Incorporadas en Junio 2026</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(stats_junio['por_marca'])}</div>
                <div class="metric-label">🏷️ Marcas</div>
                <div class="metric-sub">Diferentes</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(stats_junio['por_categoria'])}</div>
                <div class="metric-label">📂 Categorias</div>
                <div class="metric-sub">Diferentes</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">${stats_junio['precio_promedio']:,.2f}</div>
                <div class="metric-label">💰 Precio Promedio</div>
                <div class="metric-sub">Min: ${stats_junio['precio_min']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{stats_junio['activos']}</div>
                <div class="metric-label">✅ Fichas Activas</div>
                <div class="metric-sub">OFERTADA + VIGENTE</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏷️ Marcas - Junio 2026")
            if stats_junio['por_marca']:
                df_marcas_junio = pd.DataFrame(list(stats_junio['por_marca'].items()), 
                                               columns=['Marca', 'Cantidad'])
                df_marcas_junio = df_marcas_junio.sort_values('Cantidad', ascending=False)
                
                fig = px.bar(df_marcas_junio.head(15), x='Marca', y='Cantidad',
                            title=f'Top 15 Marcas (Total: {stats_junio["total"]} fichas)',
                            color='Marca', text='Cantidad')
                fig.update_traces(textposition='outside')
                fig.update_layout(height=450)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("📂 Categorias - Junio 2026")
            if stats_junio['por_categoria']:
                df_cat_junio = pd.DataFrame(list(stats_junio['por_categoria'].items()), 
                                            columns=['Categoria', 'Cantidad'])
                df_cat_junio = df_cat_junio.sort_values('Cantidad', ascending=False)
                
                fig = px.pie(df_cat_junio, values='Cantidad', names='Categoria',
                            title='Distribucion por Categoria',
                            color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(height=450)
                st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        st.subheader("📋 Detalle de Fichas Nuevas - Junio 2026")
        mostrar_tabla_productos(df_junio, "")
        
        st.subheader("💾 Exportar Datos de Junio 2026")
        col1, col2 = st.columns(2)
        
        with col1:
            csv = df_junio.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="fichas_nuevas_junio_2026.csv" style="text-decoration: none; background-color: #1f77b4; color: white; padding: 10px 20px; border-radius: 5px; display: inline-block;">📥 Descargar CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
        
        with col2:
            json_str = df_junio.to_json(orient='records', date_format='iso')
            b64_json = base64.b64encode(json_str.encode()).decode()
            href_json = f'<a href="data:file/json;base64,{b64_json}" download="fichas_nuevas_junio_2026.json" style="text-decoration: none; background-color: #28a745; color: white; padding: 10px 20px; border-radius: 5px; display: inline-block;">📥 Descargar JSON</a>'
            st.markdown(href_json, unsafe_allow_html=True)
    
    else:
        st.warning("📊 No se encontraron fichas nuevas en Junio 2026")
    
    st.divider()
    
    # ============ PESTAÑAS PRINCIPALES ============
    st.markdown("""
    <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); padding: 1rem; border-radius: 10px; margin: 1rem 0;">
        <h2 style="color: white; text-align: center; margin: 0;">📊 ANALISIS COMPLETO DE TODOS LOS PRODUCTOS</h2>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Resumen General", 
        "🏷️ Analisis por Marca", 
        "📂 Analisis por Categoria",
        "📅 Analisis por Fechas",
        "📋 Datos Detallados"
    ])
    
    with tab1:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{stats['total']}</div>
                <div class="metric-label">📦 Total Productos</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(stats['por_marca'])}</div>
                <div class="metric-label">🏷️ Marcas</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(stats['por_categoria'])}</div>
                <div class="metric-label">📂 Categorias</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">${stats['precio_promedio']:,.2f}</div>
                <div class="metric-label">💰 Precio Promedio</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            st.markdown(f"""
            <div class="metric-card" style="background: #28a745; color: white;">
                <div class="metric-value" style="color: white;">{stats['activos']}</div>
                <div class="metric-label" style="color: white;">✅ Fichas Activas</div>
                <div class="metric-sub" style="color: rgba(255,255,255,0.8);">OFERTADA + VIGENTE</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Distribucion por Marca")
            if stats['por_marca']:
                df_marcas = pd.DataFrame(list(stats['por_marca'].items()), 
                                         columns=['Marca', 'Cantidad'])
                df_marcas = df_marcas.sort_values('Cantidad', ascending=False)
                
                fig = px.pie(df_marcas.head(15), values='Cantidad', names='Marca',
                            title='Top 15 Marcas',
                            color_discrete_sequence=px.colors.qualitative.Set3)
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(height=450)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Distribucion por Categoria")
            if stats['por_categoria']:
                df_categorias = pd.DataFrame(list(stats['por_categoria'].items()), 
                                            columns=['Categoria', 'Cantidad'])
                df_categorias = df_categorias.sort_values('Cantidad', ascending=False)
                
                fig = px.bar(df_categorias, x='Categoria', y='Cantidad',
                            title='Productos por Categoria',
                            color='Categoria',
                            color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_traces(textposition='outside')
                fig.update_layout(height=450)
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("🏷️ Analisis Detallado por Marca")
        if stats['por_marca']:
            df_marcas = pd.DataFrame(list(stats['por_marca'].items()), 
                                     columns=['Marca', 'Cantidad'])
            df_marcas = df_marcas.sort_values('Cantidad', ascending=False)
            
            fig = px.bar(df_marcas, x='Marca', y='Cantidad', 
                        color='Marca', text='Cantidad')
            fig.update_traces(textposition='outside')
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_marcas, use_container_width=True)
    
    with tab3:
        st.subheader("📂 Analisis Detallado por Categoria")
        if stats['por_categoria']:
            df_categorias = pd.DataFrame(list(stats['por_categoria'].items()), 
                                         columns=['Categoria', 'Cantidad'])
            df_categorias = df_categorias.sort_values('Cantidad', ascending=False)
            
            fig = px.pie(df_categorias, values='Cantidad', names='Categoria',
                        color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_categorias, use_container_width=True)
    
    with tab4:
        mostrar_analisis_fechas(df_filtrado)
    
    with tab5:
        mostrar_tabla_productos(df_filtrado, "Todos los Productos")
        
        st.subheader("💾 Exportar Datos Completos")
        csv = df_filtrado.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="productos_completos.csv" style="text-decoration: none; background-color: #1f77b4; color: white; padding: 10px 20px; border-radius: 5px; display: inline-block;">📥 Descargar CSV</a>'
        st.markdown(href, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
