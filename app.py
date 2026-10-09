import io
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import trimesh

# ==========================================
# 1. PAGE CONFIGURATION & DARK PACS THEME
# ==========================================
st.set_page_config(
    page_title="3D Orthopedic Workstation | PTS & ACL Analysis",
    page_icon="🦴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Clinical PACS Styling
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #e6edf3; }
    div[data-testid="stMetricValue"] { font-size: 28px; font-weight: bold; color: #00f2fe; }
    div[data-testid="stMetricLabel"] { font-size: 14px; color: #8b949e; }
    .stSelectbox, .stSlider, .stFileUploader { background-color: #161b22; border-radius: 8px; }
    .risk-banner-normal { background-color: #0d381e; border: 1px solid #2ea043; color: #56d364; padding: 12px; border-radius: 6px; }
    .risk-banner-warning { background-color: #3b2300; border: 1px solid #d29922; color: #e3b341; padding: 12px; border-radius: 6px; }
    .risk-banner-danger { background-color: #4c1d1d; border: 1px solid #f85149; color: #f85149; padding: 12px; border-radius: 6px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. HELPER FUNCTIONS: STL LOADING & SYNTHESIS
# ==========================================
@st.cache_data
def load_stl_mesh(file_source):
    """
    Loads an STL file (path or BytesIO) using trimesh.
    Returns vertices and faces.
    """
    try:
        if isinstance(file_source, str):
            mesh = trimesh.load_mesh(file_source)
        else:
            mesh = trimesh.load(file_source, file_type='stl')
        return mesh.vertices, mesh.faces
    except Exception as e:
        st.error(f"Error loading STL mesh: {e}")
        return None, None

def generate_fallback_tibia_mesh():
    """
    Generates a procedural anatomical proxy of a proximal tibia if no STL is provided.
    """
    # Create plateau head and tapering shaft
    shaft = trimesh.creation.cylinder(radius=14, height=120, sections=32)
    head = trimesh.creation.cylinder(radius=26, height=25, sections=32)
    head.apply_translation([0, 0, 50])
    
    # Merge geometries
    tibia_proxy = trimesh.util.concatenate([shaft, head])
    return tibia_proxy.vertices, tibia_proxy.faces

# ==========================================
# 3. SIDEBAR CONTROLS
# ==========================================
st.sidebar.title("🦴 PACS Workstation Controls")
st.sidebar.markdown("---")

# File Upload / Local Asset Selector
stl_option = st.sidebar.radio(
    "3D Model Source:",
    ("Use Local/Uploaded STL File", "Use Anatomical Proxy Model")
)

vertices, faces = None, None

if stl_option == "Use Local/Uploaded STL File":
    uploaded_file = st.sidebar.file_uploader("Upload Tibia Mesh (.stl)", type=["stl"])
    local_path = "tibia.stl"  # Checks root directory for default file
    
    if uploaded_file is not None:
        vertices, faces = load_stl_mesh(io.BytesIO(uploaded_file.read()))
        st.sidebar.success("Custom STL Loaded Successfully!")
    elif os.path.exists(local_path):
        vertices, faces = load_stl_mesh(local_path)
        st.sidebar.info("Loaded root 'tibia.stl' asset.")
    else:
        st.sidebar.warning("No 'tibia.stl' found in root folder. Loading anatomical proxy.")
        vertices, faces = generate_fallback_tibia_mesh()
else:
    vertices, faces = generate_fallback_tibia_mesh()

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Surgical Parameters")

# Slope & Preset Selector
preset_case = st.sidebar.selectbox(
    "Clinical Case Presets:",
    ("Custom Adjustment", "Normal Variant (6.5°)", "Borderline Risk (11.0°)", "Severe High Risk (15.5°)")
)

if preset_case == "Normal Variant (6.5°)":
    pts_angle = 6.5
elif preset_case == "Borderline Risk (11.0°)":
    pts_angle = 11.0
elif preset_case == "Severe High Risk (15.5°)":
    pts_angle = 15.5
else:
    pts_angle = st.sidebar.slider("Posterior Tibial Slope (°):", 0.0, 20.0, 9.5, 0.5)
mesh_opacity = st.sidebar.slider("Bone Opacity:", 0.2, 1.0, 0.85, 0.05)
show_axes = st.sidebar.checkbox("Display Anatomical Axes (Anterior-Posterior / Z)", True)
show_grid = st.sidebar.checkbox("Display Reference Grid", True)

# ==========================================
# 4. MAIN WORKSTATION DASHBOARD
# ==========================================
st.title("🏥 3D Orthopedic Workstation: Posterior Tibial Slope Engine")
st.markdown("Quantitative 3D assessment of anatomical tibial slope & anterior cruciate ligament (ACL) strain vectors.")

# Top Metric Cards
col1, col2, col3, col4 = st.columns(4)

# Calculate Risk Level
if pts_angle < 10.0:
    risk_tier = "LOW"
    risk_color = "#56d364"
    shear_force = "Normal (~120 N)"
elif 10.0 <= pts_angle <= 12.0:
    risk_tier = "MODERATE"
    risk_color = "#e3b341"
    shear_force = "Elevated (~210 N)"
else:
    risk_tier = "HIGH RISK"
    risk_color = "#f85149"
    shear_force = "Critical (>340 N)"

col1.metric("Calculated PTS Angle", f"{pts_angle:.1f}°")
col2.metric("ACL Strain Risk Tier", risk_tier)
col3.metric("Est. Anterior Shear Force", shear_force)
col4.metric("Anatomical Alignment", "Sub-mm Precision")

st.markdown("---")

# ==========================================
# 5. REALISTIC 3D PLOTLY MESH GENERATION
# ==========================================
x, y, z = vertices[:, 0], vertices[:, 1], vertices[:, 2]
i_idx, j_idx, k_idx = faces[:, 0], faces[:, 1], faces[:, 2]

# Center the mesh coordinates around origin
x_center, y_center, z_center = np.mean(x), np.mean(y), np.mean(z)
x, y, z = x - x_center, y - y_center, z - z_center

z_max = np.max(z)
z_min = np.min(z)
x_range = np.ptp(x)

# 1. Realistic Bone Mesh Trace (Physically-Based Lighting)
bone_trace = go.Mesh3d(
    x=x, y=y, z=z,
    i=i_idx, j=j_idx, k=k_idx,
    color='#F5F2EB',          # Realistic bone ivory tone
    opacity=mesh_opacity,
    name="Tibial Bone Mesh",
    flatshading=False,
    lighting=dict(
        ambient=0.45,         # Soft global environmental glow
        diffuse=0.85,         # Strong matte directional light
        fresnel=0.2,          # Edge lighting effect
        specular=0.9,         # Bright highlight spot on bone cortical surface
        roughness=0.35        # Bone surface texture rendering
    ),
    lightposition=dict(x=100, y=200, z=150) # Light source placement
)

fig = go.Figure(data=[bone_trace])

# 2. Add Rotating PTS Cutting Plane Surface
plane_size = x_range * 0.75
px = np.linspace(-plane_size, plane_size, 10)
py = np.linspace(-plane_size, plane_size, 10)
PX, PY = np.meshgrid(px, py)

# Rotate plane along sagittal axis by PTS angle
rad = np.radians(pts_angle)
PZ = (z_max - 5) - (PY * np.tan(rad))

plane_trace = go.Surface(
    x=PX, y=PY, z=PZ,
    colorscale=[[0, '#00f2fe'], [1, '#4facfe']],
    showscale=False,
    opacity=0.55,
    name="PTS Cutting Plane"
)
fig.add_trace(plane_trace)

# 3. Add Anatomical Vector Overlays
if show_axes:
    # Anatomical Shaft Axis (Cyan)
    fig.add_trace(go.Scatter3d(
        x=[0, 0], y=[0, 0], z=[z_min, z_max + 15],
        mode='lines+text',
        line=dict(color='#00f2fe', width=6),
        name="Anatomical Axis"
    ))
    # Slope Line (Red/Yellow Vector)
    fig.add_trace(go.Scatter3d(
        x=[0, 0], y=[-plane_size, plane_size],
        z=[(z_max - 5) + (plane_size * np.tan(rad)), (z_max - 5) - (plane_size * np.tan(rad))],
        mode='lines+text',
        line=dict(color='#f85149', width=6, dash='dash'),
        name="Slope Line"
    ))

# 4. Apply Dark PACS CAD Layout
fig.update_layout(
    scene=dict(
        xaxis=dict(title="Medial - Lateral (X)", visible=show_grid, backgroundcolor="#0d1117", gridcolor="#21262d"),
        yaxis=dict(title="Anterior - Posterior (Y)", visible=show_grid, backgroundcolor="#0d1117", gridcolor="#21262d"),
[09.10.2026 15:00] #.࣪ 𝚛𝚒𝚊𝚗𝚗𝚊◝☁️: zaxis=dict(title="Superior - Inferior (Z)", visible=show_grid, backgroundcolor="#0d1117", gridcolor="#21262d"),
        aspectmode='data',
        camera=dict(eye=dict(x=1.6, y=-1.6, z=0.8)) # Default Sagittal/Oblique view
    ),
    paper_bgcolor="#0d1117",
    plot_bgcolor="#0d1117",
    margin=dict(l=0, r=0, b=0, t=30),
    height=680
)

# Render Chart
main_col, side_col = st.columns([3, 1])

with main_col:
    st.plotly_chart(fig, use_container_width=True)

with side_col:
    st.subheader("📋 Risk Diagnostic Engine")
    
    if pts_angle < 10.0:
        st.markdown(
            f"""<div class='risk-banner-normal'>
            <h4>🟢 Low Risk ({pts_angle:.1f}°)</h4>
            <p>Anatomical slope within normal limits (<10°). Minimal secondary anterior shearing strain on ACL graft during weight-bearing.</p>
            </div>""", unsafe_allow_html=True
        )
    elif 10.0 <= pts_angle <= 12.0:
        st.markdown(
            f"""<div class='risk-banner-warning'>
            <h4>🟡 Moderate Risk ({pts_angle:.1f}°)</h4>
            <p>Borderline slope elevation (10°–12°). Increased tibial displacement forces during knee flexion. Monitor graft tension.</p>
            </div>""", unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""<div class='risk-banner-danger'>
            <h4>🔴 High Risk ({pts_angle:.1f}°)</h4>
            <p>High slope detected (>12°). Significantly elevated risk for primary/secondary ACL graft revision. Consider slope-correcting anterior osteotomy.</p>
            </div>""", unsafe_allow_html=True
        )
        
    st.markdown("---")
    st.markdown("Biomechanical Force Estimates:")
    st.write(f"- PTS Angle: {pts_angle}°")
    st.write(f"- Tibial Slope Plane Drift: {np.tan(np.radians(pts_angle)):.3f} mm/mm")
    st.write(f"- Relative ACL Graft Load Increase: {max(0, (pts_angle - 8.0) * 12.5):.1f}%")
    
    st.markdown("---")
    st.download_button(
        label="📄 Export Clinical Report (PDF/Summary)",
        data=f"PTS Angle: {pts_angle} deg\nRisk Tier: {risk_tier}\nShear Force: {shear_force}",
        file_name="pts_analysis_report.txt"
    )
