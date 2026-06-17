import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import base64

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Análisis de Productos",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS
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
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class ProductAnalyzer:
    def __init__(self):
        self.df = None
        self.all_records = []
        
    def load_from_github(self, repo_owner, repo_name, branch="main", folder=""):
        """Carga TODOS los archivos JSON desde GitHub"""
        
        # URL de la API de GitHub para listar archivos
        api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{folder}"
        
        try:
            # Obtener lista de archivos
            response = requests.get(api_url)
            if response.status_code != 200:
                st.error(f"Error al acceder al repositorio: {response.status_code}")
                return None
            
            files = response.json()
            json_files = []
            
            # Filtrar solo archivos JSON
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
                st.warning("No se encontraron archivos JSON en el repositorio")
                return None
            
            st.success(f"📁 Encontrados {len(json_files)} archivos JSON")
            
            # Cargar cada archivo JSON
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_records = 0
            
            for idx, file_info in enumerate(json_files):
                status_text.text(f"Cargando archivo {idx+1} de {len(json_files)}: {file_info['name']} ({file_info['size']} bytes)")
                
                try:
                    # Descargar el archivo
                    file_response = requests.get(file_info['download_url'])
                    if file_response.status_code == 200:
                        data = file_response.json()
                        if 'records' in data:
                            records_count = len(data['records'])
                            self.all_records.extend(data['records'])
                            total_records += records_count
                            st.info(f"📄 {file_info['name']}: {records_count} registros")
                except Exception as e:
                    st.error(f"Error al cargar {file_info['name']}: {str(e)}")
                
                progress_bar.progress((idx + 1) / len(json_files))
            
            status_text.text(f"✅ ¡Carga completada! Total: {total_records} registros")
            progress_bar.empty()
            
            if self.all_records:
                self.df = pd.DataFrame(self.all_records)
                self._process_data()
                return self.df
            
            return None
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return None
    
    def _process_data(self):
        """Procesa los datos"""
        if self.df is None or self.df.empty:
            return
        
        # Convertir fechas
        self.df['fecha_publicacion_dt'] = pd.to_datetime(
            self.df['fecha_publicacion'], 
            format='%d/%m/%Y %I:%M:%S %p',
            errors='coerce'
        )
        
        # Extraer marca y categoría
        self.df['marca'] = self.df['descripcion'].apply(self._extract_brand)
        self.df['categoria'] = self.df['descripcion'].apply(self._extract_category)
        self.df['precio_float'] = pd.to_numeric(self.df['precio'], errors='coerce')
        
        # Filtrar Junio 2026
        self.df['es_junio_2026'] = (self.df['fecha_publicacion_dt'].dt.year == 2026) & \
                                   (self.df['fecha_publicacion_dt'].dt.month == 6)
    
    def _extract_brand(self, descripcion):
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
        if not isinstance(descripcion, str):
            return "Desconocida"
        
        if "PORTATIL" in descripcion.upper() or "NOTEBOOK" in descripcion.upper():
            return "Portátil"
        elif "ESCRITORIO" in descripcion.upper() or "DESKTOP" in descripcion.upper():
            return "Escritorio"
        return "Otro"
    
    def get_monthly_stats(self):
        if self.df is None or self.df.empty:
            return None
        
        df_junio = self.df[self.df['es_junio_2026'] == True]
        
        if df_junio.empty:
            return {'total': 0, 'por_marca': {}, 'por_categoria': {}, 'precio_promedio': 0}
        
        return {
            'total': len(df_junio),
            'por_marca': df_junio['marca'].value_counts().to_dict(),
            'por_categoria': df_junio['categoria'].value_counts().to_dict(),
            'precio_promedio': df_junio['precio_float'].mean(),
            'precio_min': df_junio['precio_float'].min(),
            'precio_max': df_junio['precio_float'].max(),
            'dataframe': df_junio
        }

def main():
    st.markdown('<h1 class="main-header">📊 Dashboard de Análisis de Productos</h1>', unsafe_allow_html=True)
    
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = ProductAnalyzer()
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        st.markdown("""
        ### 📌 Carga desde GitHub
        El sistema cargará automáticamente TODOS los archivos JSON
        """)
        
        # Configuración del repositorio
        repo_owner = st.text_input("Owner del repositorio:", value="StalinHA")
        repo_name = st.text_input("Nombre del repositorio:", value="fichadjudicados")
        branch = st.text_input("Rama:", value="main")
        folder = st.text_input("Carpeta (opcional):", value="")
        
        if st.button("🚀 Cargar TODOS los JSON", use_container_width=True):
            with st.spinner("Cargando archivos desde GitHub..."):
                df = st.session_state.analyzer.load_from_github(repo_owner, repo_name, branch, folder)
                if df is not None and not df.empty:
                    st.success(f"✅ {len(df)} registros cargados exitosamente!")
                    st.rerun()
    
    analyzer = st.session_state.analyzer
    
    if analyzer.df is None or analyzer.df.empty:
        st.info("📁 Haz clic en 'Cargar TODOS los JSON' en el panel izquierdo")
        
        with st.expander("💡 Instrucciones", expanded=True):
            st.markdown("""
            ### Cómo funciona:
            1. **El sistema busca automáticamente** todos los archivos .json en tu repositorio
            2. **Los combina** en un solo DataFrame
            3. **Analiza** todos los registros juntos
            
            ### ¿Dónde subir los archivos?
            - Sube todos tus JSON al repositorio de GitHub
            - El sistema los descargará automáticamente
            - No necesitas subirlos a Streamlit Cloud
            """)
        return
    
    # Mostrar estadísticas
    stats = analyzer.get_monthly_stats()
    
    if stats and stats['total'] > 0:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{stats['total']}</div>
                <div class="metric-label">📦 Nuevos (Junio 2026)</div>
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
                <div class="metric-value">${stats['precio_promedio']:.2f}</div>
                <div class="metric-label">💰 Precio promedio</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        # Gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Distribución por Marca")
            if stats['por_marca']:
                df_marcas = pd.DataFrame(list(stats['por_marca'].items()), 
                                         columns=['Marca', 'Cantidad'])
                fig = px.pie(df_marcas, values='Cantidad', names='Marca')
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("📂 Distribución por Categoría")
            if stats['por_categoria']:
                df_categorias = pd.DataFrame(list(stats['por_categoria'].items()), 
                                            columns=['Categoría', 'Cantidad'])
                fig = px.bar(df_categorias, x='Categoría', y='Cantidad', color='Categoría')
                st.plotly_chart(fig, use_container_width=True)
        
        # Tabla de datos
        st.subheader("📋 Productos Nuevos (Junio 2026)")
        df_show = stats['dataframe'][['ID_ProductoOfertado', 'descripcion', 'marca', 
                                      'categoria', 'precio', 'fecha_publicacion']].copy()
        df_show['descripcion'] = df_show['descripcion'].str[:100] + '...'
        st.dataframe(df_show, use_container_width=True, height=400)
        
        # Exportar
        st.subheader("💾 Exportar Datos")
        csv = stats['dataframe'].to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="productos_junio_2026.csv">📥 Descargar CSV</a>'
        st.markdown(href, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
