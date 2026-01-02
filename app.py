import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="Simulasi Cek Biaya Hidup",
    page_icon="💰",
    layout="wide"
)

# CSS untuk mempercantik tampilan kotak vonis
st.markdown("""
<style>
    .stAlert {
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .big-font {
        font-size: 20px !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MATH ENGINE (LOGIKA SIMULASI)
# ==========================================
def generate_correlated_samples(n, correlation_strength):
    # Gaussian Copula untuk korelasi antar variabel
    r = correlation_strength
    cov_matrix = np.array([[1.0, 0.6*r, 0.4*r], [0.6*r, 1.0, 0.5*r], [0.4*r, 0.5*r, 1.0]])
    mean = [0, 0, 0]
    mv_norm = np.random.multivariate_normal(mean, cov_matrix, n)
    return stats.norm.cdf(mv_norm[:, 0]), stats.norm.cdf(mv_norm[:, 1]), stats.norm.cdf(mv_norm[:, 2])

# ==========================================
# 3. SIDEBAR (UX MUDAH DIMENGERTI)
# ==========================================
with st.sidebar:
    st.header("🎛️ Pengaturan")
    
    # --- BAGIAN 1: YANG WAJIB (SIMPLE) ---
    st.subheader("1. Data Keuangan")
    BUDGET = st.number_input("Punya Uang Berapa? (Rp)", value=2500000, step=100000)
    
    st.subheader("2. Estimasi Biaya Makan")
    st.caption("Masukkan perkiraan biaya makan sebulan.")
    makan_min = st.number_input("Paling Hemat", value=900000)
    makan_mode = st.number_input("Biasanya (Normal)", value=1500000)
    makan_max = st.number_input("Paling Boros", value=2400000)

    st.markdown("---")

    # --- BAGIAN 2: PENGATURAN LANJUT (DISEMBUNYIKAN/EXPANDER) ---
    # Ini supaya user awam tidak pusing lihat istilah teknis
    with st.expander("⚙️ Pengaturan Lanjut (Advanced)"):
        st.info("Atur bagian ini jika ingin simulasi lebih mendetail.")
        
        N_SIMULATIONS = st.slider("Jumlah Simulasi", 1000, 20000, 10000, step=1000)
        
        st.markdown("**🔗 Efek 'Hedon' (Korelasi)**")
        correlation_strength = st.slider(
            "Seberapa menular gaya hidup?", 0.0, 0.95, 0.7,
            help="Semakin tinggi, berarti jika kamu boros di satu hal, kamu cenderung boros di hal lain."
        )
        
        st.markdown("**☕ Gaya Hidup (Lifestyle)**")
        lifestyle_mu = st.slider("Level Gaya Hidup (11-14)", 11.0, 14.0, 12.5, 0.1)
        st.caption(f"Median Lifestyle: Rp {np.exp(lifestyle_mu):,.0f}")
        lifestyle_sigma = st.slider("Variasi Gaya Hidup", 0.1, 1.0, 0.4, 0.05)
        
        st.markdown("**🚨 Risiko Musibah**")
        prob_darurat = st.slider("Peluang Musibah (%)", 0, 20, 5) / 100
        biaya_darurat_val = st.number_input("Biaya Musibah (Rp)", value=1500000)

    st.markdown("---")
    run_sim = st.button("🚀 CEK KONDISI KEUANGAN", type="primary", use_container_width=True)

# ==========================================
# 4. MAIN DASHBOARD
# ==========================================
st.title("Analisis Risiko Keuangan 📊")

if run_sim:
    # --- PROSES HITUNG ---
    with st.spinner('Sedang menghitung risiko...'):
        u_makan, u_trans, u_life = generate_correlated_samples(N_SIMULATIONS, correlation_strength)
        
        biaya_kost = np.random.normal(850000, 50000, N_SIMULATIONS)
        
        # Triangular
        c_makan = (makan_mode - makan_min) / (makan_max - makan_min)
        biaya_makan = stats.triang.ppf(u_makan, c=c_makan, loc=makan_min, scale=makan_max-makan_min)
        
        biaya_transport = stats.uniform.ppf(u_trans, 150000, 300000)
        biaya_lifestyle = stats.lognorm.ppf(u_life, s=lifestyle_sigma, scale=np.exp(lifestyle_mu))
        
        is_darurat = np.random.rand(N_SIMULATIONS) < prob_darurat
        biaya_darurat = np.where(is_darurat, biaya_darurat_val, 0)
        
        total_biaya = biaya_kost + biaya_makan + biaya_transport + biaya_lifestyle + biaya_darurat
        
        df = pd.DataFrame({'Total': total_biaya, 'Status': ['Darurat' if x > 0 else 'Normal' for x in biaya_darurat]})

    # --- KPI UTAMA ---
    prob_gagal = (np.sum(total_biaya > BUDGET) / N_SIMULATIONS) * 100
    safe_budget_95 = np.percentile(total_biaya, 95)
    gap = BUDGET - safe_budget_95
    
    # =========================================================
    # UI BAGIAN 1: STATUS / VONIS (PERMINTAAN USER)
    # =========================================================
    
    if gap < 0:
        # TAMPILAN JIKA KURANG UANG (MERAH)
        with st.container():
            st.error(f"""
            ### ⚠️ BAHAYA: UANG TIDAK CUKUP!
            **Anda kekurangan dana sebesar: Rp {abs(gap):,.0f}**
            
            Budget Anda (Rp {BUDGET:,.0f}) tidak cukup untuk menutupi risiko terburuk bulan ini (Rp {safe_budget_95:,.0f}).
            Ada kemungkinan **{prob_gagal:.1f}%** uang Anda habis sebelum akhir bulan.
            """)
            # Progress bar merah (Budget vs Kebutuhan)
            persen_terpenuhi = min(BUDGET / safe_budget_95, 1.0)
            st.progress(persen_terpenuhi, text=f"Dana hanya menutupi {persen_terpenuhi*100:.1f}% dari kebutuhan aman.")
            
    else:
        # TAMPILAN JIKA AMAN (HIJAU)
        with st.container():
            st.success(f"""
            ### ✅ AMAN: KEUANGAN SEHAT
            **Anda memiliki sisa dana sebesar: Rp {gap:,.0f}**
            
            Budget Anda (Rp {BUDGET:,.0f}) sudah melebihi kebutuhan risiko terburuk (Rp {safe_budget_95:,.0f}).
            Risiko kehabisan uang sangat kecil (**{prob_gagal:.1f}%**).
            """)
            st.progress(1.0, text="Dana menutupi 100% kebutuhan risiko.")

    # =========================================================
    # UI BAGIAN 2: DATA DETAIL (3 KOLOM)
    # =========================================================
    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Uang di Tangan", f"Rp {BUDGET:,.0f}")
    col2.metric("🛡️ Butuh Segini (95% Aman)", f"Rp {safe_budget_95:,.0f}")
    col3.metric("📉 Risiko Bangkrut", f"{prob_gagal:.1f}%", delta_color="inverse")

    # =========================================================
    # UI BAGIAN 3: GRAFIK (UX LEBIH MUDAH DIBACA)
    # =========================================================
    st.markdown("### 📊 Peta Risiko Pengeluaran")
    
    # Membuat Histogram
    fig = px.histogram(
        df, x="Total", color="Status", nbins=80,
        color_discrete_map={'Normal': '#00CC96', 'Darurat': '#FF4B4B'},
        title="Distribusi Kemungkinan Total Pengeluaran",
        labels={"Total": "Total Biaya (Rp)", "count": "Frekuensi"}
    )
    
    # 1. Garis Uang Kamu (Putih Putus-putus)
    fig.add_vline(x=BUDGET, line_width=2, line_dash="dash", line_color="white")
    fig.add_annotation(
        x=BUDGET, y=0, text=f"Uang Kamu<br>Rp {BUDGET/1e6:.1f} Juta", 
        showarrow=True, arrowhead=2, ax=0, ay=-40,
        font=dict(color="white", size=12), bgcolor="#333333"
    )

    # 2. Garis Batas Aman (Oranye Solid)
    fig.add_vline(x=safe_budget_95, line_width=3, line_dash="solid", line_color="#FFA500")
    fig.add_annotation(
        x=safe_budget_95, y=0, text=f"Batas Aman<br>Rp {safe_budget_95/1e6:.1f} Juta", 
        showarrow=True, arrowhead=2, ax=0, ay=-70,
        font=dict(color="#FFA500", size=12, weight="bold"), bgcolor="black"
    )

    # Memindahkan legend agar tidak menutupi grafik
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=50) # Tambah margin atas biar teks tidak kepotong
    )

    st.plotly_chart(fig, use_container_width=True)

    # Penjelasan Grafik Bahasa Manusia
    st.info("""
    **Cara Baca Grafik:**
    * **Area Hijau:** Pengeluaran di bulan-bulan normal.
    * **Area Merah (Kanan):** Bulan saat kamu kena musibah (sakit/hp rusak).
    * **Lihat Jarak Garis:**
        * Jika garis **"Uang Kamu"** ada di sebelah KIRI garis **"Batas Aman"**, berarti kamu **KURANG** uang (Area Merah).
        * Jika garis **"Uang Kamu"** ada di sebelah KANAN garis **"Batas Aman"**, berarti kamu **AMAN** (Area Hijau).
    """)

else:
    st.info("👈 Silakan masukkan data keuangan di sidebar kiri, lalu klik tombol **CEK KONDISI KEUANGAN**.")