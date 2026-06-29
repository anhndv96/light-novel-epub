import sys
import json
import subprocess
import os

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
    
    for idx, url in enumerate(chapters, start=1):
        print(f"\n" + "*"*50)
        print(f"ĐANG XỬ LÝ CHƯƠNG {idx}/{len(chapters)}")
        print(f"URL: {url}")
        print("*"*50)
        
        try:
            # Tận dụng lại chính script run_pipeline.py đã viết
            subprocess.run([sys.executable, "run_pipeline.py", series_name, str(idx), url], check=True)
        except subprocess.CalledProcessError as e:
            print(f"\n[!] CÓ LỖI XẢY RA KHI XỬ LÝ CHƯƠNG {idx} ({url}).")
            print(f"Chi tiết lỗi: {e}")
            print("[*] Script sẽ bỏ qua chương này và tiếp tục chạy chương tiếp theo...")
            
    print(f"\n==================================================")
    print(f"[✓] ĐÃ HOÀN TẤT XỬ LÝ TOÀN BỘ SERIES: {series_name}")
    print(f"==================================================")

if __name__ == "__main__":
    main()
