import cv2
import pytesseract
import re
import pandas as pd
import os
import streamlit as st

# Mengatur path tesseract secara otomatis untuk environment Linux (Streamlit Cloud)
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

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

    # 1. CARI NIK (Mencari angka 16 digit apa saja secara fleksibel)
    for line in lines:
        nums_only = re.sub(r'\D', '', line)
        if len(nums_only) >= 16:
            nik_match = re.search(r'(\d{16})', nums_only)
            if nik_match:
                data["NIK"] = nik_match.group(1)
                break

    if not data["NIK"]:
        all_nums = re.sub(r'\D', '', text)
        nik_match = re.search(r'(\d{16})', all_nums)
        if nik_match:
            data["NIK"] = nik_match.group(1)

    # 2. CARI NAMA (Mencari baris setelah kata NAMA)
    for i, line in enumerate(lines):
        line_up = line.upper()
        if 'NAMA' in line_up and 'Keluarga' not in line:
            parts = line.split(':')
            if len(parts) > 1 and len(parts[1].strip()) > 3:
                data["Nama"] = parts[1].strip()
            elif i + 1 < len(lines):
                data["Nama"] = lines[i + 1].strip()
            break
    
    # Cadangan Nama (Cari teks huruf kapital panjang yang mirip nama orang)
    if not data["Nama"]:
        for line in lines:
            if re.match(r'^[A-Z\s]{5,}$', line) and not any(kw in line.upper() for kw in ['PROVINSI', 'KABUPATEN', 'KOTA', 'JAWA', 'BLORA', 'GROBOGAN', 'NIK', 'GOL']):
                data["Nama"] = line.strip()
                break

    # 3. CARI TEMPAT / TGL LAHIR
    for line in lines:
        if 'LAHIR' in line.upper() or 'TEMPAT' in line.upper():
            tgl_match = re.search(r'(\d{2}[-\/]\d{2}[-\/]\d{4})', line)
            if tgl_match:
                tgl = tgl_match.group(1).replace('/', '-')
                parts = line.split(':')
                tempat_teks = parts[1] if len(parts) > 1 else line
                tempat_clean = re.sub(r'\d{2}[-\/]\d{2}[-\/]\d{4}', '', tempat_teks).replace(',', '').strip()
                if not tempat_clean:
                    tempat_clean = "KABUPATEN"
                data["Tempat/Tgl Lahir"] = f"{tempat_clean.upper()}, {tgl}"
                break
    
    if not data["Tempat/Tgl Lahir"]:
        tgl_match = re.search(r'(\d{2}[-\/]\d{2}[-\/]\d{4})', text)
        if tgl_match:
            tgl = tgl_match.group(1).replace('/', '-')
            data["Tempat/Tgl Lahir"] = f"WILAYAH, {tgl}"

    # 4. CARI ALAMAT (Menangkap baris Alamat, RT/RW, Kel/Desa, Kecamatan)
    alamat_parts = []
    capture = False
    for line in lines:
        line_up = line.upper()
        if 'ALAMAT' in line_up:
            capture = True
            parts = line.split(':')
            if len(parts) > 1 and len(parts[1].strip()) > 2:
                alamat_parts.append(parts[1].strip())
            continue
        
        if capture:
            if any(kw in line_up for kw in ['AGAMA', 'STATUS', 'PEKERJAAN', 'KEWARGANEGARAAN', 'BERLAKU']):
                break
            alamat_parts.append(line.strip())

    if alamat_parts:
        data["Alamat"] = ", ".join([p for p in alamat_parts if p])
    else:
        data["Alamat"] = "ALAMAT TIDAK TERBACA"

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

    # Simpan ke Excel dengan memastikan NIK disimpan sebagai format teks
    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
        df_final.to_excel(writer, index=False)

    print(f"✅ SUKSES! Data berhasil diperbarui di Excel: {excel_filename}")

# --- TAMPILAN STREAMLIT WEB ---
st.title("Aplikasi KTP Scanner OCR")

uploaded_file = st.file_uploader("Pilih file foto KTP...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
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
