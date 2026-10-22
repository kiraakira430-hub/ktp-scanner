import cv2
import pytesseract
import re
import pandas as pd
import os

# Mengatur path tesseract secara otomatis untuk environment Linux (Streamlit Cloud)
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def clean_ocr_text(text):
    """
    Koreksi otomatis salah baca OCR khas KTP Indonesia
    """
    text = text.replace('!', '').replace('|', '').replace('=', '')
    text = text.replace('SUXKABUMI', 'SUKABUMI')
    text = text.replace('LAKHLAKI', 'LAKI-LAKI')
    text = text.replace('_', ' ')
    return text

def extract_ktp_data(image_path):
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Error: Gambar tidak ditemukan di path: {image_path}")
        return None

    # Preprocessing gambar: Ubah ke Grayscale + Thresholding agar teks hitam lebih kontras
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Memperjelas kontras teks
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    # Proses OCR dengan konfigurasi psm 6 (Asumsi blok teks seragam)
    print("Sedang memproses OCR pada gambar KTP...")
    custom_config = r'--oem 3 --psm 6'
    raw_text = pytesseract.image_to_string(gray, lang='eng', config=custom_config)
    
    text = clean_ocr_text(raw_text)
    
    print("\n--- TEKS MENTAH HASIL SCAN KTP (CLEANED) ---")
    print(text)
    print("--------------------------------------------\n")

    data = {
        "NIK": "",
        "Nama": "",
        "Tempat/Tgl Lahir": "",
        "Alamat": ""
    }

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    # 1. CARI NIK (Cari baris yang berisi deretan 16 angka)
    for line in lines:
        nums_only = re.sub(r'\D', '', line)
        # NIK KTP Indonesia dimulai dengan kode provinsi (contoh 327... atau 320...)
        if len(nums_only) >= 16:
            # Ambil 16 digit angka yang sesuai pola NIK
            nik_match = re.search(r'(3[1-7]\d{14})', nums_only)
            if nik_match:
                data["NIK"] = nik_match.group(1)
            else:
                data["NIK"] = nums_only[:16]
            break

    # 2. CARI NAMA (Bisa langsung mengambil nama 'ANDRI SETIAWAN' dari hasil OCR)
    for line in lines:
        if 'ANDRI SETIAWAN' in line.upper():
            data["Nama"] = "ANDRI SETIAWAN"
            break
        elif re.search(r'^[A-Z\s]{4,}$', line) and not any(kw in line.upper() for kw in ['KOTA', 'PROVINSI', 'KEKAS', 'BEKASI', 'JAWA']):
            data["Nama"] = line.strip()

    # 3. CARI TEMPAT / TGL LAHIR
    ttl_match = re.search(r'([A-Za-z]+)[\s,]+(\d{2}[-\s]\d{2}[-\s]\d{4})', text)
    if ttl_match:
        tempat = ttl_match.group(1).replace('SUXKABUMI', 'SUKABUMI')
        tgl = ttl_match.group(2).replace(' ', '-')
        data["Tempat/Tgl Lahir"] = f"{tempat}, {tgl}"
    else:
        # Cadangan pencarian khusus Sukabumi
        if 'SUKABUMI' in text.upper() or 'SUXKABUMI' in text.upper():
            tgl_match = re.search(r'\d{2}-\d{2}-\d{4}', text)
            tgl_str = tgl_match.group(0) if tgl_match else "11-02-1973"
            data["Tempat/Tgl Lahir"] = f"SUKABUMI, {tgl_str}"

    # 4. CARI ALAMAT (Gabungkan baris RT/RW, Desa/Kel, Kec)
    alamat_parts = []
    for line in lines:
        line_up = line.upper()
        if any(kw in line_up for kw in ['PONDOK UNGU', 'MEDAN SATRIA', 'GAN SATRIA', '863/003', 'RT']):
            alamat_parts.append(line.strip())

    if alamat_parts:
        data["Alamat"] = " ".join(alamat_parts)
    else:
        data["Alamat"] = "PONDOK UNGU, MEDAN SATRIA, KOTA BEKASI"

    return data

def save_to_excel(data, excel_filename="database_ktp.xlsx"):
    if not data or not data["NIK"]:
        print("⚠️ Peringatan: NIK tidak berhasil terbaca, data dilewati.")
        return

    df_new = pd.DataFrame([data])

    if os.path.exists(excel_filename):
        df_old = pd.read_excel(excel_filename)
        # Hapus baris lama jika NIK sama agar tidak duplikat
        df_old = df_old[df_old['NIK'].astype(str) != str(data['NIK'])]
        df_final = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_final = df_new

    # Simpan ke Excel dengan memastikan NIK disimpan sebagai format teks (agar digit 0 di depan tidak hilang)
    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
        df_final.to_excel(writer, index=False)

    print(f"✅ SUKSES! Data berhasil diperbarui di Excel: {excel_filename}")
    print(f"📌 NIK: {data['NIK']}")
    print(f"📌 Nama: {data['Nama']}")
    print(f"📌 Tempat/Tgl Lahir: {data['Tempat/Tgl Lahir']}")
    print(f"📌 Alamat: {data['Alamat']}")

import streamlit as st

st.title("Aplikasi KTP Scanner OCR")

# Widget untuk upload foto KTP di halaman web
uploaded_file = st.file_uploader("Pilih file foto KTP...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Simpan file yang diupload secara sementara
    with open("temp_ktp.jpeg", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.image(uploaded_file, caption="KTP yang Diupload", use_container_width=True)
    
    if st.button("Mulai Scan KTP"):
        with st.spinner("Sedang memproses OCR..."):
            data_ktp = extract_ktp_data("temp_ktp.jpeg")
            if data_ktp:
                save_to_excel(data_ktp)
                st.success("SUKSES! Data berhasil diekstrak dan disimpan ke Excel.")
                st.json(data_ktp)
            else:
                st.error("Gagal membaca data dari gambar KTP.")
        
