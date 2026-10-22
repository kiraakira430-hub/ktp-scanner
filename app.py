import streamlit as st
import cv2
import easyocr
import re
import pandas as pd
import os
import numpy as np
from PIL import Image

# Page Config Streamlit
st.set_page_config(page_title="KTP OCR SCANNER - ORANGE NEON EDITION", page_icon="🪪", layout="wide")

# CSS Custom Theme - 3 Gradasi Orange Neon, Font Hitam, & Variasi Merah Neon
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #ff4500 0%, #ff7700 50%, #ffaa00 100%);
        color: #000000;
        font-family: 'Segoe UI', Roboto, sans-serif;
    }
    .cyber-title {
        font-size: 2.8rem;
        font-weight: 900;
        text-align: center;
        color: #000000;
        text-shadow: 0 0 15px rgba(255, 0, 85, 0.6), 0 0 30px rgba(255, 0, 85, 0.4);
        letter-spacing: 2px;
        margin-bottom: 5px;
        text-transform: uppercase;
    }
    .cyber-subtitle {
        text-align: center;
        color: #ff0055;
        font-size: 1.1rem;
        font-weight: 800;
        margin-bottom: 25px;
        letter-spacing: 1.5px;
        text-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
    }
    section[data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.85);
        border: 3px dashed #ff0055;
        border-radius: 14px;
        padding: 20px;
        box-shadow: 0 0 20px rgba(255, 0, 85, 0.3);
    }
    .cyber-card {
        background: rgba(255, 255, 255, 0.92);
        border-left: 8px solid #ff0055;
        border-top: 2px solid #ff0055;
        border-right: 2px solid #ff0055;
        border-bottom: 2px solid #ff0055;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25), 0 0 15px rgba(255, 0, 85, 0.4);
        color: #000000;
    }
    .stButton > button {
        background: linear-gradient(45deg, #ff0055, #cc0044) !important;
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 1.1rem !important;
        border: 2px solid #ff3377 !important;
        border-radius: 10px !important;
        padding: 12px 24px !important;
        box-shadow: 0 0 20px rgba(255, 0, 85, 0.6) !important;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        background: linear-gradient(45deg, #000000, #ff0055) !important;
        color: #ffffff !important;
        box-shadow: 0 0 30px rgba(255, 0, 85, 0.9) !important;
        transform: scale(1.02);
    }
    .stTextInput label {
        color: #000000 !important;
        font-weight: 800 !important;
    }
    .stTextInput > div > div > input {
        background-color: #ffffff !important;
        color: #000000 !important;
        font-weight: 700 !important;
        border: 2px solid #ff0055 !important;
        border-radius: 8px !important;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
    }
    .stTextInput > div > div > input:focus {
        border-color: #000000 !important;
        box-shadow: 0 0 12px rgba(255, 0, 85, 0.8) !important;
    }
    [data-testid="stDataFrame"] {
        border: 2px solid #ff0055;
        border-radius: 10px;
        box-shadow: 0 0 15px rgba(255, 0, 85, 0.3);
        background-color: #ffffff;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="cyber-title">⚡ KTP OCR AUTOMATION ⚡</div>', unsafe_allow_html=True)
st.markdown('<div class="cyber-subtitle">[ ORANGE NEON EDITION • EASYOCR DEEP LEARNING ]</div>', unsafe_allow_html=True)

@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en', 'id'], gpu=False)

reader = load_ocr_reader()

def clean_ocr_text(text):
    if not text:
        return ""
    cleaned = re.sub(r'[^A-Z0-9\s\.,/-]', '', text.upper())
    return re.sub(r'\s+', ' ', cleaned).strip()

def parse_ktp_easyocr(ocr_results):
    text_lines = [res[1].strip() for res in ocr_results if len(res[1].strip()) > 0]
    full_text = "\n".join(text_lines)
    full_upper = full_text.upper()

    data = {
        "Provinsi": "",
        "Kota/Kabupaten": "",
        "NIK": "",
        "Nama": "",
        "Tempat/Tgl Lahir": "",
        "Jenis Kelamin": "",
        "Gol. Darah": "-",
        "Alamat": "",
        "RT/RW": "",
        "Kel/Desa": "",
        "Kecamatan": "",
        "Agama": "",
        "Status Perkawinan": "",
        "Pekerjaan": "",
        "Kewarganegaraan": "WNI",
        "Berlaku Hingga": "SEUMUR HIDUP"
    }

    # 1. NIK Extraction (16 Digit)
    all_digits = re.sub(r'\D', '', full_text)
    nik_matches = re.findall(r'\d{16}', all_digits)
    if nik_matches:
        data["NIK"] = nik_matches[0]

    # 2. Parsing cerdas berbasis baris teks
    for idx, line in enumerate(text_lines):
        up = line.upper()
        clean_l = clean_ocr_text(up)

        if 'PROVINSI' in up:
            parts = up.split('PROVINSI')
            data["Provinsi"] = clean_ocr_text(parts[-1].replace(':', ''))
        elif 'KABUPATEN' in up or 'KOTA' in up:
            data["Kota/Kabupaten"] = clean_ocr_text(up.replace(':', ''))

        if 'NAMA' in up and 'AGAMA' not in up:
            val = line.split(':')[-1] if ':' in line else re.sub(r'^NAMA', '', clean_l, flags=re.IGNORECASE)
            c_val = clean_ocr_text(val)
            if len(c_val) > 2 and 'TEMPAT' not in c_val:
                data["Nama"] = c_val
            elif idx + 1 < len(text_lines):
                data["Nama"] = clean_ocr_text(text_lines[idx + 1])

        # Tempat / Tgl Lahir Presisi Sempurna
        if re.search(r'\d{2}[-\s]\d{2}[-\s]\d{4}', line) or 'LAHIR' in up or 'TEMPAT' in up or 'TEMPAU' in up:
            m = re.search(r'([A-Za-z\s]+)[,\s:]+(\d{2}[-\s]\d{2}[-\s]\d{4})', line)
            if m:
                t_part = clean_ocr_text(m.group(1)).replace('TEMPAU', '').replace('TEMPAT', '').replace('LAHIR', '').strip()
                d_part = m.group(2).replace(' ', '-')
                if len(t_part) < 3 and data["Kota/Kabupaten"]:
                    # Ambil dari nama kabupaten/kota jika tempat lahir terpotong
                    t_part = data["Kota/Kabupaten"].replace('KABUPATEN', '').replace('KOTA', '').strip()
                data["Tempat/Tgl Lahir"] = f"{t_part}, {d_part}"
            elif not data["Tempat/Tgl Lahir"] and re.search(r'\d{2}[-\s]\d{2}[-\s]\d{4}', line):
                tgl_match = re.search(r'(\d{2}[-\s]\d{2}[-\s]\d{4})', line)
                if tgl_match and idx > 0:
                    prev_text = clean_ocr_text(text_lines[idx-1])
                    for label in ['TEMPAT', 'TEMPAU', 'LAHIR', 'TGL', 'NAMA', 'NIK', 'P']:
                        prev_text = prev_text.replace(label, '').strip()
                    if not prev_text and data["Kota/Kabupaten"]:
                        prev_text = data["Kota/Kabupaten"].replace('KABUPATEN', '').replace('KOTA', '').strip()
                    data["Tempat/Tgl Lahir"] = f"{prev_text}, {tgl_match.group(1).replace(' ', '-')}"

        # Alamat Cerdas
        if 'ALAMAT' in up:
            val = line.split(':')[-1] if ':' in line else re.sub(r'^ALAMAT', '', clean_l, flags=re.IGNORECASE)
            c_alm = clean_ocr_text(val)
            if len(c_alm) > 1:
                data["Alamat"] = c_alm
            elif idx + 1 < len(text_lines):
                next_l = clean_ocr_text(text_lines[idx + 1])
                if not any(k in next_l for k in ['RT', 'RW', 'KEL', 'KEC', 'AGAMA']):
                    data["Alamat"] = next_l

        rtrw_m = re.search(r'(\d{2,3}\s*/\s*\d{2,3})', line)
        if rtrw_m:
            data["RT/RW"] = rtrw_m.group(1).replace(' ', '')

        # Kel/Desa Cerdas
        if ('KEL' in up or 'DESA' in up) and 'KELAMIN' not in up:
            val = line.split(':')[-1] if ':' in line else re.sub(r'.*(KEL/DESA|DESA|KELURAHAN|KELDEZA)', '', up)
            c_kel = clean_ocr_text(val)
            if len(c_kel) > 1:
                data["Kel/Desa"] = c_kel
            elif idx + 1 < len(text_lines):
                data["Kel/Desa"] = clean_ocr_text(text_lines[idx + 1])

        # Kecamatan Cerdas
        if 'KEC' in up or 'KECAMATAN' in up:
            val = line.split(':')[-1] if ':' in line else re.sub(r'.*(KECAMATAN|KEC|WIAOSNII)', '', up)
            c_kec = clean_ocr_text(val)
            if len(c_kec) > 1:
                data["Kecamatan"] = c_kec
            elif idx + 1 < len(text_lines):
                data["Kecamatan"] = clean_ocr_text(text_lines[idx + 1])

    # Fallback Tempat/Tgl Lahir jika masih kosong / tidak ada nama kota
    if data["Tempat/Tgl Lahir"].startswith(','):
        city_fallback = ""
        if data["Kota/Kabupaten"]:
            city_fallback = data["Kota/Kabupaten"].replace('KABUPATEN', '').replace('KOTA', '').strip()
        data["Tempat/Tgl Lahir"] = f"{city_fallback}{data['Tempat/Tgl Lahir']}"

    # Fallback Alamat jika kosong
    if not data["Alamat"]:
        for l in text_lines:
            up_l = l.upper()
            if any(k in up_l for k in ['TUNJUNGAN', 'NGASEM', 'BLABUR', 'WONOREJO', 'SAMBIREJO']):
                if 'KEC' not in up_l and 'KEL' not in up_l:
                    data["Alamat"] = clean_ocr_text(l)
                    break

    # 3. Jenis Kelamin & Gol Darah Akurat
    if 'PEREMPUAN' in full_upper:
        data["Jenis Kelamin"] = "PEREMPUAN"
    elif 'LAKI' in full_upper:
        data["Jenis Kelamin"] = "LAKI-LAKI"

    # Deteksi Golongan Darah strict (hanya ambil jika bernilai A, B, AB, O, atau plus/minus, abaikan strip)
    gol_match = re.search(r'GOL[.\s]*DARAH\s*[:]?\s*([A|B|AB|O][\+\-]?)', full_upper)
    if gol_match:
        val_g = gol_match.group(1).strip()
        if val_g in ['A', 'B', 'AB', 'O', 'A+', 'B+', 'AB+', 'O+', 'A-', 'B-', 'AB-', 'O-']:
            data["Gol. Darah"] = val_g
        else:
            data["Gol. Darah"] = "-"
    else:
        data["Gol. Darah"] = "-"

    # 4. Agama, Status, Pekerjaan
    if 'ISLAM' in full_upper: data["Agama"] = "ISLAM"
    elif 'KRISTEN' in full_upper: data["Agama"] = "KRISTEN"
    elif 'KATOLIK' in full_upper: data["Agama"] = "KATOLIK"
    elif 'HINDU' in full_upper: data["Agama"] = "HINDU"
    elif 'BUDDHA' in full_upper: data["Agama"] = "BUDDHA"

    if 'BELUM KAWIN' in full_upper:
        data["Status Perkawinan"] = "BELUM KAWIN"
    elif 'KAWIN' in full_upper:
        data["Status Perkawinan"] = "KAWIN"

    if 'MENGURUS' in full_upper or 'RUMAH' in full_upper:
        data["Pekerjaan"] = "MENGURUS RUMAH TANGGA"
    elif 'BELUM' in full_upper and 'BEKERJA' in full_upper:
        data["Pekerjaan"] = "BELUM/TIDAK BEKERJA"
    elif 'KARYAWAN' in full_upper or 'SWASTA' in full_upper:
        data["Pekerjaan"] = "KARYAWAN SWASTA"
    elif 'PNS' in full_upper:
        data["Pekerjaan"] = "PNS"
    elif 'PELAJAR' in full_upper or 'MAHASISWA' in full_upper:
        data["Pekerjaan"] = "PELAJAR/MAHASISWA"
    elif 'WIRASWASTA' in full_upper:
        data["Pekerjaan"] = "WIRASWASTA"

    if 'SEUMUR' in full_upper:
        data["Berlaku Hingga"] = "SEUMUR HIDUP"

    return data

# Layout Aplikasi
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown('<div class="cyber-card"><h3 style="color:#000000; margin-top:0; font-weight: 900;">📤 UPLOAD DOKUMEN KTP</h3>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Format Dukungan: JPG, JPEG, PNG", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Preview Foto KTP Target", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    if uploaded_file is not None:
        st.markdown('<div class="cyber-card"><h3 style="color:#ff0055; margin-top:0; font-weight: 900;">⚙️ HASIL EKSTRAKSI & EDIT DATA</h3>', unsafe_allow_html=True)
        
        img_np = np.array(image)
        
        with st.spinner("🧠 EasyOCR Deep Learning sedang menganalisis teks KTP..."):
            results = reader.readtext(img_np)
            parsed_data = parse_ktp_easyocr(results)

        with st.form("ktp_edit_form"):
            f_prov = st.text_input("Provinsi", parsed_data["Provinsi"])
            f_kota = st.text_input("Kota/Kabupaten", parsed_data["Kota/Kabupaten"])
            f_nik = st.text_input("NIK (16 Digit)", parsed_data["NIK"])
            f_nama = st.text_input("Nama Lengkap", parsed_data["Nama"])
            f_ttl = st.text_input("Tempat/Tgl Lahir", parsed_data["Tempat/Tgl Lahir"])
            
            c_a, c_b = st.columns(2)
            with c_a:
                f_jk = st.text_input("Jenis Kelamin", parsed_data["Jenis Kelamin"])
                f_alamat = st.text_input("Alamat", parsed_data["Alamat"])
                f_kel = st.text_input("Kel/Desa", parsed_data["Kel/Desa"])
                f_agama = st.text_input("Agama", parsed_data["Agama"])
                f_kerja = st.text_input("Pekerjaan", parsed_data["Pekerjaan"])
            with c_b:
                f_gol = st.text_input("Gol. Darah", parsed_data["Gol. Darah"])
                f_rtrw = st.text_input("RT/RW", parsed_data["RT/RW"])
                f_kec = st.text_input("Kecamatan", parsed_data["Kecamatan"])
                f_status = st.text_input("Status Perkawinan", parsed_data["Status Perkawinan"])
                f_berlaku = st.text_input("Berlaku Hingga", parsed_data["Berlaku Hingga"])

            f_kwn = st.text_input("Kewarganegaraan", parsed_data["Kewarganegaraan"])

            submit_btn = st.form_submit_button("🔥 SIMPAN DATA KE DATABASE EXCEL 🔥")

        st.markdown('</div>', unsafe_allow_html=True)

        if submit_btn:
            final_record = {
                "Provinsi": f_prov,
                "Kota/Kabupaten": f_kota,
                "NIK": f_nik,
                "Nama": f_nama,
                "Tempat/Tgl Lahir": f_ttl,
                "Jenis Kelamin": f_jk,
                "Gol. Darah": f_gol,
                "Alamat": f_alamat,
                "RT/RW": f_rtrw,
                "Kel/Desa": f_kel,
                "Kecamatan": f_kec,
                "Agama": f_agama,
                "Status Perkawinan": f_status,
                "Pekerjaan": f_kerja,
                "Kewarganegaraan": f_kwn,
                "Berlaku Hingga": f_berlaku
            }
            
            excel_filename = "database_ktp.xlsx"
            df_new = pd.DataFrame([final_record])

            if os.path.exists(excel_filename):
                try:
                    df_old = pd.read_excel(excel_filename)
                    if 'NIK' in df_old.columns and f_nik:
                        df_old = df_old[df_old['NIK'].astype(str) != str(f_nik)]
                    df_final = pd.concat([df_old, df_new], ignore_index=True)
                except Exception:
                    df_final = df_new
            else:
                df_final = df_new

            df_final.to_excel(excel_filename, index=False)

            st.success("⚡ DATA SUCCESSFUL INJECTED TO EXCEL DATABASE! ⚡")
            st.dataframe(df_final, use_container_width=True)

            with open(excel_filename, "rb") as f:
                st.download_button(
                    label="📥 DOWNLOAD EXCEL DATABASE (.XLSX)",
                    data=f,
                    file_name="database_ktp.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        with col2:
            st.markdown("""
                <div class="cyber-card" style="text-align: center; padding: 40px;">
                    <h2 style="color: #ff0055;">⏳ MENUNGGU UPLOAD KTP</h2>
                    <p style="font-size: 1.1rem; font-weight: 700; color: #000000;">
                        Silakan upload foto KTP Anda melalui panel di sebelah kiri.<br>
                        Sistem AI EasyOCR akan otomatis memindai dan mengisi data di sini.
                    </p>
                </div>
            """, unsafe_allow_html=True)
            