import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import base64
from io import BytesIO

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Análisis de Productos",
    page_icon=" ",
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
    .filter-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
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
    .info-box {
        background-color: #cce5ff;
        color: #004085;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #b8daff;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class ProductAnalyzer:
    """Clase principal para el análisis de productos"""
    
    def __init__(self):
        self.df = None
        self.records = []
        self.source_info = ""
        self.carga_completa = False
        
    def load_from_github(self, repo_owner, repo_name, branch="main", folder=""):
        """Carga TODOS los archivos JSON desde GitHub"""
        self.records = []
        self.carga_completa = False
        
        # Construir URL de la API de GitHub
        if folder:
            api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{folder}"
        else:
            api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents"
        
        try:
            st.info(f"🔍 Buscando archivos en: {repo_owner}/{repo_name}")
            
            # Obtener lista de archivos
            response = requests.get(api_url)
            if response.status_code != 200:
                st.error(f"❌ Error al acceder al repositorio: {response.status_code}")
                return None
            
            files = response.json()
            json_files = []
            
            # Recorrer todos los archivos y carpetas
            for file in files:
                if file['type'] == 'file' and file['name'].endswith('.json'):
                    json_files.append(file)
                elif file['type'] == 'dir':
                    # Buscar en subdirectorios
                    sub_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file['path']}"
                    sub_response = requests.get(sub_url)
                    if sub_response.status_code == 200:
                        sub_files = sub_response.json()
                        for sub_file in sub_files:
                            if sub_file['type'] == 'file' and sub_file['name'].endswith('.json'):
                                json_files.append(sub_file)
            
            if not json_files:
                st.warning("⚠️ No se encontraron archivos JSON en el repositorio")
                return None
            
            st.success(f"📁 Encontrados {len(json_files)} archivos JSON")
            
            # Cargar cada archivo JSON
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_records = 0
            archivos_cargados = 0
            
            for idx, file_info in enumerate(json_files):
                status_text.text(f"📄 Cargando {idx+1}/{len(json_files)}: {file_info['name']} ({file_info['size']} bytes)")
                
                try:
                    # Descargar el archivo
                    file_response = requests.get(file_info['download_url'])
                    if file_response.status_code == 200:
                        data = file_response.json()
                        if 'records' in data:
                            records_count = len(data['records'])
                            self.records.extend(data['records'])
                            total_records += records_count
                            archivos_cargados += 1
                except Exception as e:
                    st.error(f"❌ Error en {file_info['name']}: {str(e)[:100]}")
                
                progress_bar.progress((idx + 1) / len(json_files))
            
            status_text.text(f"✅ ¡Carga completada! {archivos_cargados} archivos, {total_records} registros")
            progress_bar.empty()
            
            if self.records:
                self.df = pd.DataFrame(self.records)
                self._process_data()
                self.carga_completa = True
                self.source_info = f"GitHub: {repo_owner}/{repo_name} ({archivos_cargados} archivos)"
                return self.df
            
            return None
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
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
        
        # Extraer marca
        self.df['marca'] = self.df['descripcion'].apply(self._extract_brand)
        
        # Extraer categoría
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
            'CYBER WORKPAD': ['CYBER WORKPAD'],
            'SAMSUNG': ['SAMSUNG'],
            'TOSHIBA': ['TOSHIBA'],
            'IBM': ['IBM']
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
        
        desc_upper = descripcion.upper()
        if "PORTATIL" in desc_upper or "NOTEBOOK" in desc_upper or "LAPTOP" in desc_upper:
            return "Portátil"
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
        """Obtiene estadísticas del DataFrame filtrado"""
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

def mostrar_metricas(stats):
    """Muestra las métricas principales"""
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
            <div class="metric-label">📂 Categorías</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">${stats['precio_promedio']:,.2f}</div>
            <div class="metric-label">💰 Precio Promedio</div>
            <div class="metric-sub">Min: ${stats['precio_min']:,.2f} | Max: ${stats['precio_max']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(stats['por_estado'])}</div>
            <div class="metric-label">📊 Estados</div>
        </div>
        """, unsafe_allow_html=True)

def mostrar_graficos(stats):
    """Muestra los gráficos principales"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Distribución por Marca")
        if stats['por_marca']:
            df_marcas = pd.DataFrame(list(stats['por_marca'].items()), 
                                     columns=['Marca', 'Cantidad'])
            df_marcas = df_marcas.sort_values('Cantidad', ascending=False)
            
            fig = px.pie(df_marcas, values='Cantidad', names='Marca',
                        title=f'Total: {stats["total"]} productos',
                        color_discrete_sequence=px.colors.qualitative.Set3,
                        hover_data={'Cantidad': True})
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla de marcas
            with st.expander("📋 Ver detalle de marcas"):
                st.dataframe(df_marcas, use_container_width=True)
    
    with col2:
        st.subheader("📂 Distribución por Categoría")
        if stats['por_categoria']:
            df_categorias = pd.DataFrame(list(stats['por_categoria'].items()), 
                                        columns=['Categoría', 'Cantidad'])
            df_categorias = df_categorias.sort_values('Cantidad', ascending=False)
            
            fig = px.bar(df_categorias, x='Categoría', y='Cantidad',
                        title='Productos por Categoría',
                        color='Categoría',
                        color_discrete_sequence=px.colors.qualitative.Set2,
                        text='Cantidad')
            fig.update_traces(textposition='outside')
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla de categorías
            with st.expander("📋 Ver detalle de categorías"):
                st.dataframe(df_categorias, use_container_width=True)

def mostrar_tabla_productos(df, titulo="📋 Lista de Productos"):
    """Muestra la tabla de productos con filtros"""
    st.subheader(titulo)
    
    # Columnas a mostrar
    columnas = ['ID_ProductoOfertado', 'descripcion', 'marca', 'categoria', 
                'precio', 'estado_ficha', 'fecha_publicacion']
    
    df_show = df[columnas].copy()
    df_show['descripcion'] = df_show['descripcion'].str[:150] + '...'
    df_show.columns = ['ID', 'Descripción', 'Marca', 'Categoría', 
                       'Precio (USD)', 'Estado', 'Fecha Publicación']
    
    st.dataframe(df_show, use_container_width=True, height=500)

def mostrar_analisis_precios(stats, df):
    """Muestra el análisis de precios detallado"""
    st.subheader("📈 Análisis de Precios")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Precio Mínimo", f"${stats['precio_min']:,.2f}")
    with col2:
        st.metric("💰 Precio Máximo", f"${stats['precio_max']:,.2f}")
    with col3:
        st.metric("💰 Precio Promedio", f"${stats['precio_promedio']:,.2f}")
    
    st.divider()
    
    # Gráfico de precios por marca
    if len(df['marca'].unique()) > 1:
        df_precios_marca = df.groupby('marca').agg({
            'precio_float': ['mean', 'min', 'max', 'count']
        }).reset_index()
        df_precios_marca.columns = ['Marca', 'Promedio', 'Mínimo', 'Máximo', 'Cantidad']
        df_precios_marca = df_precios_marca.sort_values('Promedio', ascending=False)
        
        fig = px.bar(df_precios_marca, x='Marca', y='Promedio',
                    title='Precio Promedio por Marca',
                    color='Marca',
                    text=df_precios_marca['Promedio'].apply(lambda x: f'${x:,.0f}'),
                    hover_data={'Mínimo': True, 'Máximo': True, 'Cantidad': True})
        fig.update_traces(textposition='outside')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabla de precios por marca
        with st.expander("📋 Detalle de precios por marca"):
            st.dataframe(df_precios_marca.round(2), use_container_width=True)
    
    # Distribución de precios
    fig = px.box(df, x='categoria', y='precio_float', color='categoria',
                title='Distribución de Precios por Categoría',
                labels={'categoria': 'Categoría', 'precio_float': 'Precio (USD)'})
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def mostrar_filtros(df):
    """Muestra los filtros interactivos y devuelve el DataFrame filtrado"""
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros Interactivos")
    
    df_filtrado = df.copy()
    
    # Filtro por categoría
    categorias = ['Todas'] + sorted(df['categoria'].unique().tolist())
    categoria_seleccionada = st.sidebar.selectbox("📂 Filtrar por Categoría:", categorias)
    
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
    
    # Filtro por rango de precios
    min_precio = float(df['precio_float'].min())
    max_precio = float(df['precio_float'].max())
    
    rango_precio = st.sidebar.slider(
        "💰 Rango de Precios (USD):",
        min_value=min_precio,
        max_value=max_precio,
        value=(min_precio, max_precio),
        step=10.0
    )
    
    df_filtrado = df_filtrado[
        (df_filtrado['precio_float'] >= rango_precio[0]) & 
        (df_filtrado['precio_float'] <= rango_precio[1])
    ]
    
    # Filtro por fecha
    fechas_disponibles = sorted(df['fecha_publicacion_dt'].dropna().unique())
    if len(fechas_disponibles) > 0:
        fecha_min = df['fecha_publicacion_dt'].min()
        fecha_max = df['fecha_publicacion_dt'].max()
        
        fecha_inicio = st.sidebar.date_input(
            "📅 Fecha Inicio:",
            value=fecha_min.date() if pd.notnull(fecha_min) else datetime.now().date(),
            min_value=fecha_min.date() if pd.notnull(fecha_min) else None,
            max_value=fecha_max.date() if pd.notnull(fecha_max) else None
        )
        
        fecha_fin = st.sidebar.date_input(
            "📅 Fecha Fin:",
            value=fecha_max.date() if pd.notnull(fecha_max) else datetime.now().date(),
            min_value=fecha_min.date() if pd.notnull(fecha_min) else None,
            max_value=fecha_max.date() if pd.notnull(fecha_max) else None
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

def mostrar_pestanas(df, stats_completos):
    """Muestra las pestañas con diferentes vistas"""
    
    # Crear pestañas
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Resumen General", 
        "🏷️ Análisis por Marca", 
        "📂 Análisis por Categoría",
        "💰 Análisis de Precios",
        "📋 Datos Detallados"
    ])
    
    with tab1:
        st.subheader("📊 Resumen General del Dashboard")
        
        # Métricas principales
        mostrar_metricas(stats_completos)
        
        st.divider()
        
        # Gráficos principales
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 10 Marcas")
            if stats_completos['por_marca']:
                df_marcas = pd.DataFrame(list(stats_completos['por_marca'].items()), 
                                         columns=['Marca', 'Cantidad'])
                df_marcas = df_marcas.sort_values('Cantidad', ascending=False).head(10)
                fig = px.bar(df_marcas, x='Marca', y='Cantidad', 
                            color='Marca', text='Cantidad')
                fig.update_traces(textposition='outside')
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Distribución por Estado")
            if stats_completos['por_estado']:
                df_estado = pd.DataFrame(list(stats_completos['por_estado'].items()), 
                                         columns=['Estado', 'Cantidad'])
                fig = px.pie(df_estado, values='Cantidad', names='Estado',
                            color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("🏷️ Análisis Detallado por Marca")
        
        if stats_completos['por_marca']:
            df_marcas = pd.DataFrame(list(stats_completos['por_marca'].items()), 
                                     columns=['Marca', 'Cantidad'])
            df_marcas = df_marcas.sort_values('Cantidad', ascending=False)
            
            # Gráfico de barras
            fig = px.bar(df_marcas, x='Marca', y='Cantidad', 
                        title='Productos por Marca',
                        color='Marca',
                        text='Cantidad')
            fig.update_traces(textposition='outside')
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla completa
            st.dataframe(df_marcas, use_container_width=True)
            
            # Análisis por marca y categoría
            st.subheader("📊 Matriz Marca vs Categoría")
            matriz = pd.crosstab(df['marca'], df['categoria'])
            st.dataframe(matriz, use_container_width=True)
    
    with tab3:
        st.subheader("📂 Análisis Detallado por Categoría")
        
        if stats_completos['por_categoria']:
            df_categorias = pd.DataFrame(list(stats_completos['por_categoria'].items()), 
                                         columns=['Categoría', 'Cantidad'])
            df_categorias = df_categorias.sort_values('Cantidad', ascending=False)
            
            # Gráfico de pastel
            fig = px.pie(df_categorias, values='Cantidad', names='Categoría',
                        title='Distribución por Categoría',
                        color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla
            st.dataframe(df_categorias, use_container_width=True)
            
            # Análisis de precios por categoría
            st.subheader("💰 Precios por Categoría")
            df_precios_cat = df.groupby('categoria')['precio_float'].agg(
                ['mean', 'min', 'max', 'count', 'median']
            ).reset_index()
            df_precios_cat.columns = ['Categoría', 'Promedio', 'Mínimo', 'Máximo', 'Cantidad', 'Mediana']
            st.dataframe(df_precios_cat.round(2), use_container_width=True)
    
    with tab4:
        mostrar_analisis_precios(stats_completos, df)
    
    with tab5:
        mostrar_tabla_productos(df, "📋 Todos los Productos")
        
        # Botón de exportación
        st.subheader("💾 Exportar Datos")
        col1, col2 = st.columns(2)
        
        with col1:
            csv = df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="productos_completos.csv" style="text-decoration: none; background-color: #1f77b4; color: white; padding: 10px 20px; border-radius: 5px; display: inline-block;">📥 Descargar CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
        
        with col2:
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Productos')
            excel_data = excel_buffer.getvalue()
            b64_excel = base64.b64encode(excel_data).decode()
            href_excel = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="productos_completos.xlsx" style="text-decoration: none; background-color: #28a745; color: white; padding: 10px 20px; border-radius: 5px; display: inline-block;">📥 Descargar Excel</a>'
            st.markdown(href_excel, unsafe_allow_html=True)

def main():
    st.markdown('<h1 class="main-header">📊 Dashboard de Análisis de Productos</h1>', unsafe_allow_html=True)
    
    # Inicializar el analizador
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = ProductAnalyzer()
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        st.markdown("""
        <div class="info-box">
        <strong>📌 Carga desde GitHub</strong><br>
        El sistema cargará automáticamente TODOS los archivos JSON
        </div>
        """, unsafe_allow_html=True)
        
        # Configuración del repositorio
        repo_owner = st.text_input("👤 Owner del repositorio:", value="StalinHA")
        repo_name = st.text_input("📁 Nombre del repositorio:", value="fichadjudicados")
        branch = st.text_input("🌿 Rama:", value="main")
        folder = st.text_input("📂 Carpeta (opcional):", value="")
        
        if st.button("🚀 Cargar TODOS los JSON", use_container_width=True, type="primary"):
            with st.spinner("Cargando archivos desde GitHub..."):
                df = st.session_state.analyzer.load_from_github(repo_owner, repo_name, branch, folder)
                if df is not None and not df.empty:
                    st.success(f"✅ {len(df)} registros cargados exitosamente!")
                    st.rerun()
                else:
                    st.error("❌ No se pudieron cargar los datos")
        
        st.divider()
        
        # Mostrar información de carga
        if st.session_state.analyzer.carga_completa:
            st.success(f"✅ Datos cargados: {len(st.session_state.analyzer.df)} registros")
            st.info(f"📂 Fuente: {st.session_state.analyzer.source_info}")
    
    analyzer = st.session_state.analyzer
    
    # Verificar si hay datos cargados
    if not analyzer.carga_completa or analyzer.df is None or analyzer.df.empty:
        st.info("📁 Haz clic en 'Cargar TODOS los JSON' en el panel izquierdo")
        
        with st.expander("💡 Guía de uso", expanded=True):
            st.markdown("""
            ### 🚀 Cómo usar este dashboard:
            
            1. **Configura tu repositorio** en el panel izquierdo
            2. **Haz clic** en "Cargar TODOS los JSON"
            3. El sistema buscará y cargará automáticamente todos los archivos .json
            
            ### 📋 Datos que analizará:
            - ✅ Todos los productos de todos los JSON
            - ✅ Productos nuevos de Junio 2026
            - ✅ Distribución por marca y categoría
            - ✅ Análisis de precios
            - ✅ Filtros interactivos
            
            ### 📂 Estructura de archivos:
