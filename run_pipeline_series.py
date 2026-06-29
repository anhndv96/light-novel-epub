import sys
import json
import subprocess
import os
import glob
import requests

UPLOAD_API_URL = "https://download.miyoko.site/upload-light-novel-epub"

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline_series.py <series_data.json>")
        print("JSON format example:")
        print("{\n  \"series_name\": \"Ten Series\",\n  \"chapters\": [\n    \"http://...\",\n    \"http://...\"\n  ]\n}")
        sys.exit(1)
        
    json_file = sys.argv[1]
    
    if not os.path.exists(json_file):
        print(f"[!] Lỗi: Không tìm thấy file '{json_file}'.")
        sys.exit(1)
        
    with open(json_file, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[!] Lỗi khi đọc file JSON: {e}")
            sys.exit(1)
            
    series_name = data.get("series_name")
    chapters = data.get("chapters", [])
    
    if not series_name:
        print("[!] Lỗi: File JSON phải chứa trường 'series_name'.")
        sys.exit(1)
        
    if not chapters or not isinstance(chapters, list):
        print("[!] Lỗi: File JSON phải chứa một mảng 'chapters' chứa các đường link.")
        sys.exit(1)
        
    print(f"==================================================")
    print(f"BẮT ĐẦU CHẠY PIPELINE CHO SERIES: {series_name}")
    print(f"Tổng số chương cần xử lý: {len(chapters)}")
    print(f"==================================================\n")
    
    output_files = []
    out_dir = "downloads"
    os.makedirs(out_dir, exist_ok=True)
    
    for idx, url in enumerate(chapters, start=1):
        if url.strip().lower() == "na":
            print(f"\n" + "*"*50)
            print(f"ĐANG BỎ QUA CHƯƠNG {idx}/{len(chapters)} (URL: na)")
            print("*"*50)
            continue

        print(f"\n" + "*"*50)
        print(f"ĐANG XỬ LÝ CHƯƠNG {idx}/{len(chapters)}")
        print(f"URL: {url}")
        print("*"*50)
        
        existing_epubs = set(glob.glob(os.path.join(out_dir, "*.epub")))

        try:
            # Tận dụng lại chính script run_pipeline.py đã viết
            subprocess.run([sys.executable, "run_pipeline.py", series_name, str(idx), url], check=True)
        except subprocess.CalledProcessError as e:
            print(f"\n[!] CÓ LỖI XẢY RA KHI XỬ LÝ CHƯƠNG {idx} ({url}).")
            print(f"Chi tiết lỗi: {e}")
            print("[*] Script sẽ bỏ qua chương này và tiếp tục chạy chương tiếp theo...")
            continue
            
        current_epubs = set(glob.glob(os.path.join(out_dir, "*.epub")))
        new_epubs = current_epubs - existing_epubs
        
        # We need to find the translated file (it should start with the padded index)
        idx_str = str(idx).zfill(3)
        translated_file = None
        for f in new_epubs:
            if os.path.basename(f).startswith(f"{idx_str} - "):
                translated_file = f
                break
                
        if translated_file:
            output_files.append(translated_file)
            print(f"[+] Đã ghi nhận file output: {translated_file}")
        else:
            print(f"[!] Không tìm thấy file output đã dịch cho chương {idx} có tiền tố '{idx_str} - '.")
            
    print(f"\n==================================================")
    print(f"[✓] ĐÃ HOÀN TẤT XỬ LÝ TOÀN BỘ SERIES: {series_name}")
    print(f"==================================================")
    
    if output_files:
        print(f"\n==================================================")
        print(f"BẮT ĐẦU UPLOAD {len(output_files)} FILE LÊN SERVER...")
        print(f"==================================================")
        for fpath in output_files:
            print(f"[*] Đang upload: {os.path.basename(fpath)}")
            try:
                with open(fpath, 'rb') as f_in:
                    files = {'file': f_in}
                    data_payload = {'folder_name': series_name}
                    response = requests.post(UPLOAD_API_URL, files=files, data=data_payload, timeout=60)
                
                if response.status_code == 200:
                    print(f"  -> Upload thành công!")
                else:
                    print(f"  -> Upload thất bại: Mã HTTP {response.status_code} - {response.text}")
            except Exception as e:
                print(f"  -> Lỗi upload: {e}")
                
        print("\n[✓] QUÁ TRÌNH UPLOAD KẾT THÚC.")

if __name__ == "__main__":
    main()
