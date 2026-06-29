import os
import sys
import argparse
import html
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub

def main():
    parser = argparse.ArgumentParser(description="Trích xuất HTML từ EPUB để xem cấu trúc thẻ (Debug).")
    parser.add_argument("input_file", help="Đường dẫn tới file EPUB gốc")
    parser.add_argument("--limit", type=int, default=3, help="Số lượng chương muốn trích xuất (mặc định: 3 chương đầu)")
    args = parser.parse_args()

    input_path = args.input_file
    if not os.path.exists(input_path):
        print(f"[Lỗi]: File không tồn tại tại: {input_path}")
        sys.exit(1)

    print(f"[*] Đang đọc file EPUB: {input_path}")
    book = epub.read_epub(input_path)

    items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    if not items:
        print("[!] Không tìm thấy chương nào trong file EPUB.")
        sys.exit(1)

    output_filename = "debug_epub_structure.html"
    
    print(f"[*] Đang tạo file debug HTML...")
    with open(output_filename, "w", encoding="utf-8") as f:
        # Ghi header của file HTML hiển thị
        f.write("<!DOCTYPE html><html><head><meta charset='utf-8'>\n")
        f.write("<title>EPUB HTML Debugger</title>\n")
        f.write("<style>\n")
        f.write("  body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1e1e1e; color: #d4d4d4; padding: 20px; }\n")
        f.write("  h1 { color: #569cd6; border-bottom: 1px solid #333; padding-bottom: 10px; }\n")
        f.write("  pre { background-color: #2d2d2d; padding: 15px; border-radius: 5px; overflow-x: auto; font-family: 'Consolas', 'Courier New', monospace; font-size: 14px; line-height: 1.5; border: 1px solid #444; }\n")
        f.write("  .tag { color: #569cd6; }\n")
        f.write("  .attr { color: #9cdcfe; }\n")
        f.write("  .string { color: #ce9178; }\n")
        f.write("</style>\n</head><body>\n")
        
        for idx, item in enumerate(items):
            if idx >= args.limit:
                break
                
            print(f"   -> Đang trích xuất: {item.get_name()}")
            content = item.get_content()
            
            # Sử dụng BeautifulSoup để làm đẹp (prettify) HTML
            soup = BeautifulSoup(content, 'html.parser')
            pretty_html = soup.prettify()
            
            # Escape HTML entities để khi mở bằng trình duyệt nó hiển thị code thay vì render web
            escaped_html = html.escape(pretty_html)
            
            f.write(f"<h1>--- CHƯƠNG {idx + 1}: {item.get_name()} ---</h1>\n")
            f.write(f"<pre><code>{escaped_html}</code></pre>\n")
            f.write("<br><br>\n")
            
        f.write("</body></html>")
        
    print(f"\n[✓] THÀNH CÔNG! Đã lưu cấu trúc HTML vào file '{output_filename}'")
    print(f"[!] Hãy click đúp vào file '{output_filename}' để mở bằng trình duyệt web (Chrome/Edge/Firefox) và xem cấu trúc thẻ.")

if __name__ == "__main__":
    main()
